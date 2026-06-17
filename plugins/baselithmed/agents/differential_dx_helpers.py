"""
Pure module-level helper functions for the differential diagnosis agent.

All functions here are stateless and depend only on the lexicon/pattern
constants from the sibling modules, plus the shared clinical models. They
are extracted so both the agent class and ``interview_flow`` can import
them without pulling in the full agent class and its LLM provider.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..models.clinical import (
    DifferentialDiagnosis,
    DifferentialHypothesis,
    SymptomMatrix,
)
from ..safety.icd10 import sanitize_icd10
from .differential_dx_lexicons import (
    DISCRIMINATOR_QUESTIONS,
    _ALLERGEN_LEXICON,
    _BASELINE_DDX,
    _DENIAL_PENALTY,
    _DISCRIMINATOR_DELTA,
    _HYPOTHESIS_TYPICAL_FINDINGS,
    _MEDICATION_LEXICON,
    _NEGATIVE_QUANTIFIERS,
    _PMH_LEXICON,
    _SUBJECT_DENIAL_MAP,
    _SYMPTOM_LEXICON,
)
from .differential_dx_patterns import (
    _AGGRAVATING_REGEX,
    _DENIAL_CUE_PATTERNS,
    _DENIAL_WINDOW_CHARS,
    _FORTE_REGEX,
    _MEDIUM_REGEX,
    _MILD_REGEX,
    _ONSET_DAYS_REGEX,
    _ONSET_HOURS_REGEX,
    _ONSET_KEYWORDS,
    _ONSET_MINUTES_REGEX,
    _ONSET_MONTHS_REGEX,
    _ONSET_WEEKS_REGEX,
    _ONSET_YEARS_REGEX,
    _POLARITY_FLIP_MARKERS,
    _RELIEVING_REGEX,
    _SEVERITY_REGEX,
)


def select_discriminator_question(
    differential: DifferentialDiagnosis,
    *,
    already_asked: set[str],
) -> tuple[str, str, str] | None:
    """Return ``(question, discriminator_key, condition)`` for the highest
    yield discriminator we have not yet asked, or ``None`` when the
    differential is not competitive enough or no probes are left.

    A differential is "competitive" when the top hypothesis is within
    ``_DISCRIMINATOR_DELTA`` of the next-best alternative; in that case we
    can shave probability mass off either side with one well-aimed yes/no
    question.
    """
    hypotheses = [h for h in differential.hypotheses if h.confidence > 0]
    if len(hypotheses) < 2:
        return None
    top, second = hypotheses[0], hypotheses[1]
    if (top.confidence - second.confidence) > _DISCRIMINATOR_DELTA:
        return None
    # Try discriminators for the top hypothesis first, then for the runner-up.
    for h in (top, second):
        probes = DISCRIMINATOR_QUESTIONS.get(h.condition, ())
        for question, key in probes:
            if key in already_asked:
                continue
            return question, key, h.condition
    return None


def is_global_denial(utterance: str) -> bool:
    """``True`` when the patient's reply is a short global "no/niente"."""
    from .differential_dx_patterns import _GLOBAL_DENIAL_PATTERNS

    stripped = utterance.strip()
    return any(p.match(stripped) for p in _GLOBAL_DENIAL_PATTERNS)


def extract_allergies(lower_utterance: str) -> list[str]:
    """Return matched allergen canonical names, dedup."""
    found: list[str] = []
    seen: set[str] = set()
    for trigger, canonical in _ALLERGEN_LEXICON:
        if trigger in lower_utterance and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return found


def extract_medications(lower_utterance: str) -> list[str]:
    """Return medication names mentioned, normalized to title-case."""
    found: list[str] = []
    seen: set[str] = set()
    for med in _MEDICATION_LEXICON:
        if med in lower_utterance and med not in seen:
            seen.add(med)
            found.append(med.title())
    return found


def extract_risk_factors(lower_utterance: str) -> list[str]:
    """Return PMH/risk-factor labels from the utterance."""
    found: list[str] = []
    seen: set[str] = set()
    for trigger, canonical in _PMH_LEXICON:
        if trigger in lower_utterance and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return found


def extract_modifiers(lower_utterance: str) -> list[str]:
    """Return character-list entries describing what makes the symptom
    worse or better.

    Each entry is prefixed with ``peggiora:`` / ``migliora:`` so the
    existing slot-fill predicate (``character starts with`` either prefix)
    picks it up without any predicate change.
    """
    entries: list[str] = []
    trimmed = lower_utterance.strip()
    snippet = trimmed[:120]
    if _AGGRAVATING_REGEX.search(trimmed):
        entries.append(f"peggiora: {snippet}")
    if _RELIEVING_REGEX.search(trimmed):
        entries.append(f"migliora: {snippet}")
    return entries


def detect_subject_denials(lower_utterance: str) -> list[str]:
    """Return the slot names that the patient just denied by topic.

    Looks for a negative quantifier followed (within a short window) by a
    subject keyword. Example: ``"nessun farmaco"`` returns
    ``["medications"]``. The same utterance can deny multiple slots, e.g.
    ``"nessun farmaco e nessuna allergia"`` returns both.
    """
    hits: list[str] = []
    seen: set[str] = set()
    for subject, slot in _SUBJECT_DENIAL_MAP:
        idx = lower_utterance.find(subject)
        if idx == -1:
            continue
        window_start = max(0, idx - 24)
        window = lower_utterance[window_start:idx]
        if any(q in window for q in _NEGATIVE_QUANTIFIERS):
            if slot not in seen:
                seen.add(slot)
                hits.append(slot)
    return hits


def _extract_denials(lower_utterance: str) -> list[str]:
    """Return canonical symptom names the patient explicitly denied.

    For each symptom-lexicon hit, look back ``_DENIAL_WINDOW_CHARS`` characters
    and find the *latest* denial cue (matched with regex word boundaries so
    short cues like ``"no"`` do not collide with ``"sono"``). The text
    between the cue end and the trigger must not contain any polarity-
    flipping marker (comma, ``" ma "``, ``" ho "``, etc.) — that handles
    compound clauses like ``"non ho febbre, ho tosse"`` correctly.
    """
    denied: list[str] = []
    seen: set[str] = set()
    for trigger, canonical, _icd in _SYMPTOM_LEXICON:
        idx = lower_utterance.find(trigger)
        if idx == -1:
            continue
        if canonical in seen:
            continue
        window_start = max(0, idx - _DENIAL_WINDOW_CHARS)
        window = lower_utterance[window_start:idx]
        denial_end = -1
        for pattern in _DENIAL_CUE_PATTERNS:
            # Find the latest match inside the window.
            last_end = -1
            for m in pattern.finditer(window):
                if m.end() > last_end:
                    last_end = m.end()
            if last_end > denial_end:
                denial_end = last_end
        if denial_end == -1:
            continue
        between = window[denial_end:]
        if any(fm in between for fm in _POLARITY_FLIP_MARKERS):
            continue
        seen.add(canonical)
        denied.append(canonical)
    return denied


def _infer_body_site(trigger: str, canonical: str) -> str | None:
    if "testa" in trigger or canonical == "cefalea":
        return "testa"
    if "collo" in trigger or "cervic" in trigger or canonical == "cervicalgia":
        return "collo"
    if "petto" in trigger or "toracico" in trigger:
        return "torace"
    if (
        "addom" in trigger
        or "stomaco" in trigger
        or "pancia" in trigger
        or "ventre" in trigger
    ):
        return "addome"
    if "schiena" in trigger or "lombal" in canonical:
        return "lombare"
    if "occhi" in trigger or "ocular" in canonical:
        return "occhi"
    return None


def _infer_onset(utterance: str, *, now: datetime | None = None) -> datetime | None:
    """Return a best-effort onset datetime parsed from Italian temporal hints.

    The resolution is conservative: when nothing matches return ``None`` so
    the slot remains marked unfilled. We prefer numerical hints
    (``da 3 ore``) over keywords because they carry more information.
    """
    now = now or datetime.now(timezone.utc)
    lower = utterance.lower()

    m = _ONSET_MINUTES_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(minutes=int(m.group(1)))
        except ValueError:
            pass

    m = _ONSET_HOURS_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(hours=int(m.group(1)))
        except ValueError:
            pass

    m = _ONSET_DAYS_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(days=int(m.group(1)))
        except ValueError:
            pass

    m = _ONSET_WEEKS_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(weeks=int(m.group(1)))
        except ValueError:
            pass

    m = _ONSET_MONTHS_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(days=int(m.group(1)) * 30)
        except ValueError:
            pass

    m = _ONSET_YEARS_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(days=int(m.group(1)) * 365)
        except ValueError:
            pass

    for keyword, delta in _ONSET_KEYWORDS:
        if keyword in lower:
            return now - delta

    return None


def _infer_severity(utterance: str) -> int | None:
    m = _SEVERITY_REGEX.search(utterance)
    if m:
        try:
            v = int(m.group(1))
            if 0 <= v <= 10:
                return v
        except ValueError:
            pass
    if _FORTE_REGEX.search(utterance):
        return 9
    if _MEDIUM_REGEX.search(utterance):
        return 7
    if _MILD_REGEX.search(utterance):
        return 3
    return None


def heuristic_rank_ddx(
    matrix: SymptomMatrix,
    *,
    model_id: str,
    fallback_reason: str = "unspecified",
) -> DifferentialDiagnosis:
    """Deterministic heuristic DDx ranker — extracted from DifferentialDxAgent.

    Kept here so the agent class stays under the 500 LOC cap while remaining
    fully importable.  The ``model_id`` parameter substitutes for
    ``self._provider.model_id`` in the original method.
    """
    hypotheses: list[DifferentialHypothesis] = []
    seen: dict[str, int] = {}
    affirmed = {s.canonical_name for s in matrix.symptoms}
    denied = [d for d in matrix.denied_symptoms if d not in affirmed]
    for sym in matrix.symptoms:
        candidates = _BASELINE_DDX.get(sym.canonical_name, [])
        base_conf = 0.6 if sym.severity_nrs and sym.severity_nrs >= 7 else 0.45
        for condition, icd, workup in candidates:
            if condition in seen:
                idx = seen[condition]
                h = hypotheses[idx]
                if sym.canonical_name not in h.supporting_findings:
                    new_support = [*h.supporting_findings, sym.canonical_name]
                    hypotheses[idx] = h.model_copy(
                        update={
                            "supporting_findings": new_support,
                            "confidence": min(1.0, h.confidence + 0.1),
                        }
                    )
                continue
            seen[condition] = len(hypotheses)
            hypotheses.append(
                DifferentialHypothesis(
                    condition=condition,
                    icd10=sanitize_icd10(icd),
                    confidence=base_conf,
                    supporting_findings=[sym.canonical_name],
                    contradicting_findings=[],
                    recommended_workup=workup,
                )
            )

    if denied and hypotheses:
        penalized: list[DifferentialHypothesis] = []
        for h in hypotheses:
            typical = _HYPOTHESIS_TYPICAL_FINDINGS.get(h.condition, ())
            contradictions = [d for d in denied if d in typical]
            if not contradictions:
                penalized.append(h)
                continue
            new_conf = max(0.05, h.confidence - _DENIAL_PENALTY * len(contradictions))
            penalized.append(
                h.model_copy(
                    update={
                        "confidence": round(new_conf, 3),
                        "contradicting_findings": list(
                            dict.fromkeys([*h.contradicting_findings, *contradictions])
                        ),
                    }
                )
            )
        hypotheses = penalized

    if not hypotheses:
        hypotheses.append(
            DifferentialHypothesis(
                condition="Quadro aspecifico — approfondimento clinico",
                confidence=0.3,
                supporting_findings=[s.canonical_name for s in matrix.symptoms[:3]],
                recommended_workup=["Anamnesi mirata", "Esame obiettivo completo"],
            )
        )
    hypotheses.sort(key=lambda h: h.confidence, reverse=True)
    reason_notes: dict[str, str] = {
        "timeout": (
            "Modello LLM non ha risposto entro il budget configurato; "
            "rilanciare la finalizzazione per provare di nuovo l'LLM."
        ),
        "exception": (
            "Modello LLM ha sollevato un errore (transport / parse / "
            "validazione schema); vedi log backend per dettagli e "
            "rilanciare la finalizzazione."
        ),
        "empty_hypotheses": (
            "Modello LLM ha risposto correttamente ma con zero ipotesi: "
            "sintomi insufficienti per un differenziale calibrato. "
            "Aggiungere più anamnesi o validare il ranking euristico."
        ),
        "unspecified": (
            "Fallback euristico attivo (motivo non specificato dal chiamante)."
        ),
    }
    cause = reason_notes.get(fallback_reason, reason_notes["unspecified"])
    notes = f"Ranking deterministico (regole cliniche italiane). {cause}"
    if denied:
        notes += f" Pertinent negatives applicati: {', '.join(denied)}."
    return DifferentialDiagnosis(
        hypotheses=hypotheses,
        model_id=f"{model_id} · ranking deterministico",
        notes=notes,
    )


__all__ = [
    "select_discriminator_question",
    "is_global_denial",
    "extract_allergies",
    "extract_medications",
    "extract_risk_factors",
    "extract_modifiers",
    "detect_subject_denials",
    "heuristic_rank_ddx",
    "_extract_denials",
    "_infer_body_site",
    "_infer_onset",
    "_infer_severity",
]
