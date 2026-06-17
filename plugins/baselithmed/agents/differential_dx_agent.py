"""
Differential diagnosis reasoning agent.

Two responsibilities:
    * **Extraction**: turn a free-form patient utterance into an
      :class:`ExtractedObservation` so the graph can be updated. When the
      LLM fails to produce a schema-valid payload the agent falls back to a
      deterministic keyword/regex extractor so the Symptom Matrix is never
      empty after a meaningful utterance.
    * **Ranking**: starting from the :class:`SymptomMatrix`, produce a
      :class:`DifferentialDiagnosis` with calibrated confidences. A
      heuristic baseline ranks common Italian symptom→condition mappings
      when the LLM is unavailable, so the UI can show a live preview.

Implementation is split across sibling modules:
    * ``differential_dx_lexicons`` — clinical data tables (symptom lexicon,
      allergen/medication/PMH lexicons, DDx baseline, discriminator
      questions).
    * ``differential_dx_patterns`` — compiled regex patterns and onset
      timing constants.
    * ``differential_dx_helpers`` — pure module-level functions (extraction,
      denial parsing, onset/severity inference).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

from core.observability.logging import get_logger

from ..models.clinical import (
    DifferentialDiagnosis,
    ExtractedObservation,
    Symptom,
    SymptomMatrix,
)
from ..providers.medgemma_ollama import OllamaMedGemmaProvider
from ..safety.icd10 import sanitize_icd10
from .differential_dx_helpers import (
    _extract_denials,
    _infer_body_site,
    _infer_onset,
    _infer_severity,
    detect_subject_denials,
    extract_allergies,
    extract_medications,
    extract_modifiers,
    extract_risk_factors,
    heuristic_rank_ddx,
    is_global_denial,
    select_discriminator_question,
)
from .differential_dx_lexicons import (
    DISCRIMINATOR_QUESTIONS,
    _BARE_DESCRIPTOR_NAMES,
    _CHARACTER_KEYWORDS,
    _METADATA_SLOTS,
    _SYMPTOM_LEXICON,
)
from .differential_dx_patterns import _RADIATION_REGEX

logger = get_logger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "system_differential.md"
)

# Default wall-clock budget for the per-turn extraction LLM call. Tuned for
# a small model (medgemma:4b, ~2-3s). Big models (medgemma:27b, ~12-15s warm)
# REQUIRE raising this via ``provider.turn_timeout_seconds`` in plugins.yaml,
# otherwise extraction always times out and the heuristic extractor runs on
# every turn (same generic questions, same baseline DDx).
_DEFAULT_LLM_TURN_TIMEOUT_SECONDS: Final[float] = 3.0


class DifferentialDxAgent:
    """Wraps MedGemma for extraction and DDx ranking with safe fallbacks."""

    name = "baselithmed-differential"

    def __init__(
        self,
        *,
        provider: OllamaMedGemmaProvider,
        fast_provider: OllamaMedGemmaProvider | None = None,
        system_prompt: str | None = None,
        canonicalization_lexicon: tuple[tuple[str, str, str | None], ...] | None = None,
        turn_timeout_seconds: float = _DEFAULT_LLM_TURN_TIMEOUT_SECONDS,
    ) -> None:
        self._provider = provider
        # ``fast_provider`` handles the latency-sensitive per-turn extraction
        # (NER). When unset it falls back to the main provider — a single-
        # model deployment behaves exactly as before. The main provider is
        # reserved for the quality-sensitive finalize DDx ranking.
        self._fast_provider = fast_provider or provider
        self._system_prompt = system_prompt or _PROMPT_PATH.read_text(encoding="utf-8")
        self._turn_timeout = turn_timeout_seconds
        # The LLM-output canonicalizer can be swapped per language so a non-IT
        # patient utterance ("chest pain") still maps to the Italian
        # canonical keys downstream graph/red-flag layers expect. The
        # heuristic extractor stays Italian for now — its regex/keyword
        # surface is language-specific and refactoring it is a larger
        # change tracked separately.
        self._canonicalization_lexicon = (
            canonicalization_lexicon
            if canonicalization_lexicon is not None
            else _SYMPTOM_LEXICON
        )

    # Upper bound on an LLM symptom name. A "symptom" longer than this is
    # almost always the model echoing the whole utterance — drop those, but
    # keep genuine multi-word symptoms ("apnea notturna", "dolore lombare").
    _MAX_SYMPTOM_NAME_LEN: Final[int] = 60

    # Placeholder / negation tokens that small models emit as a "symptom"
    # when the patient reply carries none (e.g. answering an onset question
    # with "da più di 10 anni" → model returns canonical_name="nessun
    # sintomo"). These must never enter the Symptom Matrix.
    _NON_SYMPTOM_NAMES: Final[frozenset[str]] = frozenset(
        {
            "nessun sintomo",
            "nessun sintomo riferito",
            "nessuno",
            "nessuna",
            "nessun",
            "niente",
            "nulla",
            "n/a",
            "na",
            "none",
            "no symptom",
            "no symptoms",
            "asintomatico",
            "asintomatica",
            "non specificato",
            "sconosciuto",
            "non disponibile",
        }
    )

    def _canonicalize_symptoms(self, obs: ExtractedObservation) -> ExtractedObservation:
        """Normalize LLM symptoms against the lexicon, keeping unmapped ones.

        Two cases:
            * **Lexicon hit** — rewrite to the canonical Italian name and
              attach the lexicon ICD-10 hint (so synonyms like ``mal di
              testa`` collapse to ``cefalea``).
            * **No lexicon hit** — KEEP the symptom using the LLM's own
              (lowercased) name. The lexicon is only ~50 entries; treating
              it as a whitelist silently drops every real symptom outside
              it (e.g. ``apnea notturna``), leaving the Symptom Matrix
              empty and the interview stuck re-asking the chief complaint.
              We trust the model's NER here and rely on the ICD-10
              validator to null out fabricated codes.

        Obvious junk (empty names, or a "symptom" longer than
        ``_MAX_SYMPTOM_NAME_LEN`` — i.e. the whole utterance echoed back) is
        still discarded.
        """
        if not obs.symptoms:
            return obs
        kept: list[Symptom] = []
        for sym in obs.symptoms:
            name_lower = sym.canonical_name.lower().strip()
            quote_lower = (sym.raw_quote or "").lower()
            if not name_lower or len(name_lower) > self._MAX_SYMPTOM_NAME_LEN:
                continue
            if name_lower in self._NON_SYMPTOM_NAMES:
                continue
            # Bare quality adjectives ("costante", "forte") are descriptors of
            # an existing symptom, never a standalone complaint — the LLM
            # echoes them back when the patient answers a character/severity
            # question. The enrichment path routes the word to the current
            # symptom's character/severity instead.
            if name_lower in _BARE_DESCRIPTOR_NAMES:
                continue
            canonical: str | None = None
            icd = sym.icd10_hint
            for trigger, target_canonical, target_icd in self._canonicalization_lexicon:
                if (
                    trigger == name_lower
                    or trigger in name_lower
                    or trigger in quote_lower
                ):
                    canonical = target_canonical
                    icd = icd or target_icd
                    break
            # No lexicon match → keep the LLM symptom verbatim (normalized).
            final_name = canonical if canonical is not None else name_lower
            kept.append(
                sym.model_copy(
                    update={
                        "canonical_name": final_name,
                        "icd10_hint": sanitize_icd10(icd),
                    }
                )
            )
        return obs.model_copy(update={"symptoms": kept})

    async def extract_entities(
        self,
        utterance: str,
        *,
        turn_id: str,
        last_question_slot: str | None = None,
    ) -> ExtractedObservation:
        """Run NER on a patient utterance with heuristic fallback.

        ``last_question_slot`` is the slot the agent probed on the previous
        turn. A single-token reply to a metadata slot (severity/character/…)
        is a descriptor of the current symptom, never a new complaint, so any
        symptom the LLM hallucinates from it is dropped.
        """
        prompt = (
            "Estrai sintomi, body sites, farmaci, fattori di rischio e link "
            "temporali dalla frase del paziente. Per ogni sintomo imposta "
            "`source_turn_id` al valore fornito. Lingua italiana.\n\n"
            f"turn_id: {turn_id}\n"
            f"frase paziente: {utterance!r}\n\n"
            "Esempio output valido per ExtractedObservation:\n"
            "{\n"
            '  "symptoms": [\n'
            '    {"canonical_name": "cefalea", "raw_quote": "mi fa male la testa", '
            '"body_site": "testa", "severity_nrs": 6, "character": ["pulsante"], '
            f'"icd10_hint": "R51", "source_turn_id": "{turn_id}"}}\n'
            "  ],\n"
            '  "body_sites": ["testa"], "medications": [], '
            '"risk_factors": [], "temporal_links": []\n'
            "}"
        )
        try:
            llm_obs = await asyncio.wait_for(
                self._fast_provider.generate_structured(
                    prompt=prompt,
                    schema=ExtractedObservation,
                    system=self._system_prompt,
                ),
                timeout=self._turn_timeout,
            )
        except TimeoutError:
            logger.warning(
                "DDx extraction LLM timed out (>%ss), using heuristic.",
                self._turn_timeout,
            )
            llm_obs = ExtractedObservation()
        except Exception as exc:  # noqa: BLE001
            logger.warning("DDx extraction LLM failed, using heuristic: %s", exc)
            llm_obs = ExtractedObservation()

        llm_obs = self._canonicalize_symptoms(llm_obs)
        # Single-token reply to a metadata slot ("costante", "8", "forte") is a
        # descriptor of the current symptom, never a new complaint. Drop any
        # symptom the LLM invented from it; the enrichment path in the flow
        # routes the token to the existing symptom's character/severity.
        if (
            last_question_slot in _METADATA_SLOTS
            and len(utterance.split()) <= 1
            and llm_obs.symptoms
        ):
            llm_obs = llm_obs.model_copy(update={"symptoms": []})
        heuristic = self._heuristic_extract(utterance, turn_id=turn_id)
        # Heuristic denials win against LLM hallucination: small medical
        # models routinely emit ``"febbre"`` as a confirmed symptom even when
        # the utterance is ``"non ho febbre"``. The negation parser is more
        # reliable than the LLM here, so drop affirmed LLM symptoms whose
        # canonical name appears in the heuristic denial list.
        if heuristic.denied_symptoms:
            denied_set = set(heuristic.denied_symptoms)
            kept = [s for s in llm_obs.symptoms if s.canonical_name not in denied_set]
            if len(kept) != len(llm_obs.symptoms):
                llm_obs = llm_obs.model_copy(update={"symptoms": kept})
        return self._merge_observations(llm_obs, heuristic)

    # Budget for the explicit ``/triage/finalize`` LLM call. medgemma:27b
    # cold-start can take 30-60s on commodity hardware; the patient is no
    # longer waiting on the chat at this point, so the budget is generous.
    FINALIZE_LLM_TIMEOUT_SECONDS: float = 90.0

    async def rank(
        self, matrix: SymptomMatrix, *, timeout: float | None = None
    ) -> DifferentialDiagnosis:
        """Rank candidate diagnoses given the current Symptom Matrix.

        Always returns a non-empty :class:`DifferentialDiagnosis` if there is
        any symptom: when the LLM fails the heuristic baseline is returned.
        ``timeout`` lets the caller widen the budget for an explicit
        clinician-facing finalize.
        """
        if not matrix.symptoms:
            return DifferentialDiagnosis(
                hypotheses=[],
                model_id=self._provider.model_id,
                notes="Nessun sintomo estratto.",
            )
        prompt = (
            "Genera la differential diagnosis ordinata per confidence "
            "decrescente partendo dai sintomi raccolti.\n\n"
            f"{json.dumps(matrix.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"model_id deve essere '{self._provider.model_id}'."
        )
        budget = timeout if timeout is not None else self.FINALIZE_LLM_TIMEOUT_SECONDS
        fallback_reason: str
        try:
            ddx = await asyncio.wait_for(
                self._provider.generate_structured(
                    prompt=prompt,
                    schema=DifferentialDiagnosis,
                    system=self._system_prompt,
                ),
                timeout=budget,
            )
            ddx.hypotheses.sort(key=lambda h: h.confidence, reverse=True)
            if ddx.hypotheses:
                # Strip fabricated ICD-10 codes from the LLM output before
                # surfacing them to the clinician/UI.
                ddx.hypotheses = [
                    h.model_copy(update={"icd10": sanitize_icd10(h.icd10)})
                    for h in ddx.hypotheses
                ]
                return ddx
            fallback_reason = "empty_hypotheses"
            logger.warning("DDx ranking LLM returned 0 hypotheses, using heuristic.")
        except (TimeoutError, asyncio.TimeoutError):
            fallback_reason = "timeout"
            logger.warning(
                "DDx ranking LLM timed out (>%ss), using heuristic.",
                budget,
            )
        except Exception as exc:  # noqa: BLE001
            fallback_reason = "exception"
            logger.warning("DDx ranking LLM failed, using heuristic: %s", exc)

        return self._heuristic_rank(matrix, fallback_reason=fallback_reason)

    async def execute(
        self, input: Any, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Bridge for the orchestrator AgentProtocol."""
        context = context or {}
        turn_id = str(context.get("turn_id", "turn-0"))
        observation = await self.extract_entities(str(input), turn_id=turn_id)
        return observation.model_dump(mode="json")

    # ------------------------------------------------------------------ helpers

    def _heuristic_extract(
        self, utterance: str, *, turn_id: str
    ) -> ExtractedObservation:
        lower = utterance.lower()
        symptoms: list[Symptom] = []
        seen_canonical: set[str] = set()
        onset = _infer_onset(utterance)
        severity = _infer_severity(utterance)
        character = [c for c in _CHARACTER_KEYWORDS if c in lower]
        if _RADIATION_REGEX.search(lower) and "irradia" not in character:
            character.append("irradia")

        denied = _extract_denials(lower)

        for trigger, canonical, icd in _SYMPTOM_LEXICON:
            if trigger not in lower:
                continue
            if canonical in seen_canonical:
                continue
            # Skip lexicon hits that are actually negated — they belong to
            # ``denied_symptoms`` and must not be added as confirmed symptoms.
            if canonical in denied:
                continue
            body_site = _infer_body_site(trigger, canonical)
            symptoms.append(
                Symptom(
                    canonical_name=canonical,
                    raw_quote=utterance,
                    body_site=body_site,
                    onset=onset,
                    severity_nrs=severity,
                    character=character,
                    icd10_hint=icd,
                    source_turn_id=turn_id,
                )
            )
            seen_canonical.add(canonical)

        body_sites: list[str] = sorted({s.body_site for s in symptoms if s.body_site})
        return ExtractedObservation(
            symptoms=symptoms,
            body_sites=body_sites,
            denied_symptoms=denied,
        )

    @staticmethod
    def _merge_observations(
        primary: ExtractedObservation, secondary: ExtractedObservation
    ) -> ExtractedObservation:
        """Merge LLM + heuristic observations deduping on canonical_name.

        When both extractors yield the same symptom, the union of their
        slot fields is kept (onset/severity/body_site/character) so a
        single LLM omission cannot mask metadata supplied by the heuristic.
        """
        by_canonical: dict[str, Symptom] = {}
        for sym in [*primary.symptoms, *secondary.symptoms]:
            existing = by_canonical.get(sym.canonical_name)
            if existing is None:
                by_canonical[sym.canonical_name] = sym
                continue
            merged_character = list(
                dict.fromkeys([*existing.character, *sym.character])
            )
            by_canonical[sym.canonical_name] = existing.model_copy(
                update={
                    "body_site": existing.body_site or sym.body_site,
                    "onset": existing.onset or sym.onset,
                    "severity_nrs": existing.severity_nrs
                    if existing.severity_nrs is not None
                    else sym.severity_nrs,
                    "character": merged_character,
                    "icd10_hint": existing.icd10_hint or sym.icd10_hint,
                }
            )
        merged_denied = list(
            dict.fromkeys([*primary.denied_symptoms, *secondary.denied_symptoms])
        )
        affirmed = {s.canonical_name for s in by_canonical.values()}
        merged_denied = [d for d in merged_denied if d not in affirmed]
        return ExtractedObservation(
            symptoms=list(by_canonical.values()),
            body_sites=sorted({*primary.body_sites, *secondary.body_sites}),
            medications=sorted({*primary.medications, *secondary.medications}),
            risk_factors=sorted({*primary.risk_factors, *secondary.risk_factors}),
            temporal_links=[*primary.temporal_links, *secondary.temporal_links],
            denied_symptoms=merged_denied,
        )

    def _heuristic_rank(
        self,
        matrix: SymptomMatrix,
        *,
        fallback_reason: str = "unspecified",
    ) -> DifferentialDiagnosis:
        """Delegate to the module-level heuristic ranker (kept under 500 LOC)."""
        return heuristic_rank_ddx(
            matrix,
            model_id=self._provider.model_id,
            fallback_reason=fallback_reason,
        )


# Suppress unused-import warning for uuid4 — kept for future schema reshapes.
_ = uuid4

# ---------------------------------------------------------------------------
# Public re-exports kept for backward compatibility with callers (e.g.
# ``interview_flow.py``) that import private names directly from this module.
# ---------------------------------------------------------------------------
__all__ = [
    "DifferentialDxAgent",
    "_DEFAULT_LLM_TURN_TIMEOUT_SECONDS",
    # From lexicons
    "_CHARACTER_KEYWORDS",
    # From patterns
    "_RADIATION_REGEX",
    # From helpers
    "_infer_onset",
    "_infer_severity",
    "detect_subject_denials",
    "extract_allergies",
    "extract_medications",
    "extract_modifiers",
    "extract_risk_factors",
    "is_global_denial",
    "select_discriminator_question",
    # Discriminator table (used by interview_flow for completeness)
    "DISCRIMINATOR_QUESTIONS",
]
