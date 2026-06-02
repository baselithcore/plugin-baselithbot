"""
Empathic interviewer agent.

Drives the slot-filling loop by computing the next unfilled slot via the
``SymptomGraphRepository`` and asking MedGemma for an empathic question
focused on that slot. The agent never invents medical advice; it only
formulates questions.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.observability.logging import get_logger

from ..graph.repository import SymptomGraphRepository
from ..providers.medgemma_ollama import OllamaMedGemmaProvider

logger = get_logger(__name__)

# Default per-turn LLM budget. Small models (medgemma:4b) answer in 2-3s;
# large ones (medgemma:27b) need 12-15s warm. The default is tuned for the
# small model so the loop stays snappy; deployments running a big model
# MUST raise it via ``provider.turn_timeout_seconds`` in plugins.yaml or
# every turn falls back to the deterministic question/DDx bank.
_DEFAULT_LLM_TURN_TIMEOUT_SECONDS: float = 3.0

_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "system_anamnesis.md"
)


class NextQuestion(BaseModel):
    """Schema returned by the interviewer at each turn."""

    model_config = ConfigDict(extra="forbid")

    text: str
    target_slot: str
    tone: str = Field(default="empathic")
    rationale: str = ""


class AnamnesisAgent:
    """Generates the next empathic question for the patient."""

    name = "baselithmed-anamnesis"

    def __init__(
        self,
        *,
        provider: OllamaMedGemmaProvider,
        graph: SymptomGraphRepository,
        system_prompt: str | None = None,
        turn_timeout_seconds: float = _DEFAULT_LLM_TURN_TIMEOUT_SECONDS,
    ) -> None:
        self._provider = provider
        self._graph = graph
        self._system_prompt = system_prompt or _PROMPT_PATH.read_text(encoding="utf-8")
        self._turn_timeout = turn_timeout_seconds

    async def next_question(
        self,
        session_id: str,
        *,
        last_utterance: str | None = None,
    ) -> NextQuestion:
        """Compute the next interview question for ``session_id``."""
        unfilled = self._graph.find_unfilled_slots(session_id)
        snapshot = self._graph.snapshot(session_id)
        known_symptoms = [s.canonical_name for s in snapshot.symptoms]

        if not unfilled:
            return NextQuestion(
                text=(
                    "Grazie per le informazioni condivise. "
                    "Posso preparare il riassunto per il medico?"
                ),
                target_slot="finalize",
                tone="reassuring",
                rationale="Tutti gli slot anamnestici principali sono compilati.",
            )

        target_slot = unfilled[0]
        dialogue = self._graph.recent_dialogue(session_id, last_n=5)
        history_lines = (
            "\n".join(f"[{role}] {text}" for role, text in dialogue)
            or "(prima domanda)"
        )
        asked_questions = [q for r, q in dialogue if r == "agent"]
        history_block = (
            "Cronologia recente del colloquio (non ripetere domande già "
            "poste):\n"
            f"{history_lines}\n"
        )
        prompt = (
            f"{history_block}\n"
            f"Slot anamnestico mancante: {target_slot}.\n"
            f"Slot già compilati: {[s for s in _ANAMNESIS_SLOTS if s not in unfilled]}\n"
            f"Sintomi noti: {known_symptoms or 'nessuno ancora'}\n"
            f"Ultima frase del paziente: {last_utterance or 'N/A'}\n"
            f"Formula UNA domanda breve nuova mirata a riempire lo slot "
            f"'{target_slot}'. Non ripetere alla lettera domande della "
            f"cronologia. Imposta target_slot a '{target_slot}'."
        )
        try:
            question = await asyncio.wait_for(
                self._provider.generate_structured(
                    prompt=prompt,
                    schema=NextQuestion,
                    system=self._system_prompt,
                ),
                timeout=self._turn_timeout,
            )
        except TimeoutError:
            logger.warning(
                "Anamnesis LLM timed out (>%ss), using deterministic question.",
                self._turn_timeout,
            )
            question = NextQuestion(
                text=_FALLBACK_QUESTIONS.get(target_slot, "Può dirmi qualcosa in più?"),
                target_slot=target_slot,
                tone="empathic",
                rationale="timeout",
            )
        except Exception:
            question = NextQuestion(
                text=_FALLBACK_QUESTIONS.get(target_slot, "Può dirmi qualcosa in più?"),
                target_slot=target_slot,
                tone="empathic",
                rationale="fallback",
            )

        # Fuzzy-dedup: if the LLM returned the exact same question already
        # asked, swap in a different paraphrase from the alt-bank. The bare
        # ``_FALLBACK_QUESTIONS`` map is *the same* question that may have
        # already been recorded (when an earlier turn timed out), so a
        # second-tier paraphrase keeps the loop progressing even on cold
        # ollama instances.
        normalized_new = _normalize(question.text)
        normalized_asked = {_normalize(q) for q in asked_questions}
        if normalized_new in normalized_asked:
            alt = _ALT_FALLBACK_QUESTIONS.get(target_slot)
            if alt and _normalize(alt) not in normalized_asked:
                question = NextQuestion(
                    text=alt,
                    target_slot=target_slot,
                    tone="empathic",
                    rationale="dedup alt",
                )
            else:
                # No paraphrase available — push the slot to skip immediately
                # by signaling a 2× bump via a clearly-different filler.
                question = NextQuestion(
                    text="Può aggiungere qualcosa di utile per il medico?",
                    target_slot=target_slot,
                    tone="empathic",
                    rationale="dedup skip",
                )

        # Always overwrite ``target_slot`` with what the repository asked for
        # so the slot-ask-budget bumps the correct counter even if the LLM
        # returned a divergent label or rewrote the slot.
        return question.model_copy(update={"target_slot": target_slot})

    async def execute(
        self, input: Any, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Bridge to ``AgentProtocol`` shape used by orchestration tests."""
        context = context or {}
        session_id = str(context.get("session_id", "default"))
        utterance = input if isinstance(input, str) else str(input)
        question = await self.next_question(session_id, last_utterance=utterance)
        return question.model_dump(mode="json")


def _normalize(text: str) -> str:
    """Lowercase + strip punctuation + collapse spaces for fuzzy compare."""
    import re

    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


_FALLBACK_QUESTIONS: dict[str, str] = {
    "chief_complaint": "Cosa la porta qui oggi?",
    "onset": "Da quanto è iniziato?",
    "location": "Dove esattamente sente il sintomo?",
    "character": "Che tipo di dolore? Pulsante, sordo, costante?",
    "radiation": "Si irradia altrove?",
    "severity": "Da 0 a 10, quanto è intenso?",
    "timing": "È continuo o a episodi?",
    "modifiers": "Cosa lo peggiora o migliora?",
    "associated_symptoms": "Ha altri sintomi associati?",
    "past_medical_history": "Ha patologie note?",
    "allergies": "Soffre di allergie?",
    "medications": "Sta assumendo farmaci?",
}

# Second-tier paraphrases used only when the primary fallback was already
# asked. Picking from a different lexical surface keeps the LLM-less path
# from looping on the exact same string.
_ALT_FALLBACK_QUESTIONS: dict[str, str] = {
    "chief_complaint": "Mi descrive meglio il disturbo principale?",
    "onset": "Quando è comparso per la prima volta?",
    "location": "In che zona del corpo lo avverte?",
    "character": "Come descriverebbe la sensazione?",
    "radiation": "Il dolore si estende verso altre zone?",
    "severity": "Quanto la sta limitando nelle attività?",
    "timing": "Compare a episodi o resta sempre presente?",
    "modifiers": "Posizione o movimento lo cambiano?",
    "associated_symptoms": "Ha notato altri disturbi insieme?",
    "past_medical_history": "Ha avuto malattie o interventi importanti?",
    "allergies": "Ha allergie a farmaci, cibi o altro?",
    "medications": "Assume farmaci regolarmente?",
}


_ANAMNESIS_SLOTS: tuple[str, ...] = (
    "chief_complaint",
    "onset",
    "location",
    "character",
    "radiation",
    "severity",
    "timing",
    "modifiers",
    "associated_symptoms",
    "past_medical_history",
    "allergies",
    "medications",
)
