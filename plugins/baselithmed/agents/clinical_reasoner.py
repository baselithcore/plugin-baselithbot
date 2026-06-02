"""
Hypothesis-driven clinical reasoning agent.

Unlike :class:`AnamnesisAgent` (which fills a fixed OPQRST slot chosen by the
graph) this agent lets the LLM act as a clinician: it maintains a live
differential across all of medicine and picks the single next question that
best discriminates the competing hypotheses. One LLM call per turn returns a
:class:`ClinicianTurn` (differential + next question + stop/escalate flags).

When the LLM is unavailable (timeout, transport error, schema failure) the
agent raises :class:`ReasonerUnavailable`; the caller falls back to the
deterministic OPQRST/heuristic path so the loop degrades gracefully to the
legacy behaviour instead of breaking.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from core.observability.logging import get_logger

from ..models.clinical import SymptomMatrix
from ..models.reasoning import ClinicianTurn
from ..providers.medgemma_ollama import OllamaMedGemmaProvider
from ..safety.icd10 import sanitize_icd10

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_reasoner.md"

# Default per-turn budget. The reasoner runs in the interactive loop, so the
# budget mirrors the anamnesis turn timeout; deployments running a big model
# must raise ``provider.turn_timeout_seconds`` in plugins.yaml or every turn
# falls back to the deterministic path.
_DEFAULT_LLM_TURN_TIMEOUT_SECONDS: float = 12.0


class ReasonerUnavailable(RuntimeError):
    """Raised when the LLM cannot produce a valid clinician turn in budget."""


class ClinicalReasoner:
    """Generates one hypothesis-driven clinical turn per patient utterance."""

    name = "baselithmed-reasoner"

    def __init__(
        self,
        *,
        provider: OllamaMedGemmaProvider,
        system_prompt: str | None = None,
        turn_timeout_seconds: float = _DEFAULT_LLM_TURN_TIMEOUT_SECONDS,
    ) -> None:
        self._provider = provider
        self._system_prompt = system_prompt or _PROMPT_PATH.read_text(encoding="utf-8")
        self._turn_timeout = turn_timeout_seconds

    async def deliberate(
        self,
        *,
        matrix: SymptomMatrix,
        dialogue: list[tuple[str, str]],
        asked_questions: list[str],
    ) -> ClinicianTurn:
        """Return the next clinical turn for the current evidence.

        Raises :class:`ReasonerUnavailable` on timeout / transport / schema
        failure so the caller can fall back to the deterministic path.
        """
        prompt = self._build_prompt(
            matrix=matrix,
            dialogue=dialogue,
            asked_questions=asked_questions,
        )
        try:
            turn = await asyncio.wait_for(
                self._provider.generate_structured(
                    prompt=prompt,
                    schema=ClinicianTurn,
                    system=self._system_prompt,
                ),
                timeout=self._turn_timeout,
            )
        except (TimeoutError, asyncio.TimeoutError) as exc:
            logger.warning(
                "Clinical reasoner timed out (>%ss); falling back.",
                self._turn_timeout,
            )
            raise ReasonerUnavailable("reasoner timeout") from exc
        except Exception as exc:  # noqa: BLE001 — any failure → deterministic path
            logger.warning("Clinical reasoner failed (%s); falling back.", exc)
            raise ReasonerUnavailable(str(exc)) from exc

        return self._sanitize(turn)

    def _build_prompt(
        self,
        *,
        matrix: SymptomMatrix,
        dialogue: list[tuple[str, str]],
        asked_questions: list[str],
    ) -> str:
        history = (
            "\n".join(f"[{role}] {text}" for role, text in dialogue)
            or "(inizio colloquio)"
        )
        matrix_json = json.dumps(
            matrix.model_dump(mode="json"), ensure_ascii=False, indent=2
        )
        asked = (
            "\n".join(f"- {q}" for q in asked_questions)
            if asked_questions
            else "(nessuna)"
        )
        return (
            "Cronologia recente del colloquio:\n"
            f"{history}\n\n"
            "Dati clinici raccolti finora (Symptom Matrix):\n"
            f"{matrix_json}\n\n"
            "Domande già poste (non ripeterle alla lettera):\n"
            f"{asked}\n\n"
            f"model_id deve essere '{self._provider.model_id}'.\n"
            "Aggiorna la differential e scegli la prossima domanda che la "
            "discrimina meglio, oppure concludi se i dati bastano."
        )

    def _sanitize(self, turn: ClinicianTurn) -> ClinicianTurn:
        """Strip fabricated ICD-10 codes and sort the differential."""
        hyps = sorted(turn.differential, key=lambda h: h.confidence, reverse=True)
        hyps = [h.model_copy(update={"icd10": sanitize_icd10(h.icd10)}) for h in hyps]
        return turn.model_copy(update={"differential": hyps})

    @property
    def model_id(self) -> str:
        return self._provider.model_id
