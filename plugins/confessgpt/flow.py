"""
ConfessGPT — liturgical flow handler.

Drives one turn of the sacrament. The handler:

1. Pulls the current session state from the sigillum store.
2. Asks the LLM to produce the next confessor utterance (schema-validated).
3. Enforces hard guards that the LLM is not permitted to bypass:
   - No ASSOLUZIONE without contrition + purpose of amendment.
   - Explicit refusal of repentance → INVITO_RIFLESSIONE (no absolution).
4. Updates the session state (without storing the penitent's content).
5. On terminal phases (CONGEDO / INVITO_RIFLESSIONE) closes the session
   so the sigillum is honored.

The LLM is the *generator*; the flow is the *validator*. This keeps
the doctrine guardrails in code rather than in the prompt alone.
"""

from __future__ import annotations

import json
from typing import Protocol

from core.observability.logging import get_logger
from pydantic import ValidationError

from ._heuristics import (
    ABSOLUTION_REQUIRED_FRAGMENTS,
    _detect_amendment_during,
    _detect_contrition,
    _detect_refusal,
    _extract_json,
    _has_full_absolution,
)
from ._liturgy import (
    CANONICAL_ABSOLUTION,
    DEFAULT_REFUSAL_UTTERANCE,
    _LITURGY,
    _liturgy_turn,
)
from .models import ConfessorTurn, RitePhase, SessionState
from .prompt import build_turn_prompt
from .sigillum import SigillumStore, is_terminal

logger = get_logger(__name__)

# Re-export so existing ``from .flow import …`` call sites keep working.
__all__ = [
    "ConfessionFlow",
    "LLMBackend",
    "SessionNotFound",
    "SessionAlreadyClosed",
    # constants that callers may reference via flow
    "ABSOLUTION_REQUIRED_FRAGMENTS",
    "CANONICAL_ABSOLUTION",
    "DEFAULT_REFUSAL_UTTERANCE",
]


class LLMBackend(Protocol):
    """Minimal LLM interface the flow depends on.

    Any object exposing ``async generate(prompt, *, system) -> str``
    satisfies this. We do not import core.services.llm.LLMService
    directly here to keep the flow unit-testable with simple fakes.
    """

    async def generate(self, prompt: str, *, system: str) -> str: ...


class ConfessionFlow:
    """One turn of the Rite of Reconciliation."""

    def __init__(
        self,
        *,
        store: SigillumStore,
        llm: LLMBackend,
        system_prompt: str,
    ) -> None:
        self._store = store
        self._llm = llm
        self._system = system_prompt

    async def step(
        self,
        *,
        session_id: str,
        penitent_utterance: str,
    ) -> tuple[ConfessorTurn, SessionState, bool]:
        """Advance the rite by one turn.

        Returns:
            (turn, updated_state, closed) — ``closed`` is True if the
            session was wiped after this turn.
        """
        state = await self._store.get(session_id)
        if state is None:
            raise SessionNotFound(session_id)

        if state.closed:
            raise SessionAlreadyClosed(session_id)

        prompt = build_turn_prompt(
            current_phase=state.current_phase.value,
            contrition_detected=state.contrition_detected,
            amendment_purpose_detected=state.amendment_purpose_detected,
            explicit_refusal_of_repentance=state.explicit_refusal_of_repentance,
            turn_count=state.turn_count,
            penitent_utterance=penitent_utterance,
        )

        # Heuristic detection from the penitent utterance — runs first so
        # even an LLM-less rite honors contrition / refusal signals.
        h_contrition = _detect_contrition(penitent_utterance)
        h_amendment = _detect_amendment_during(
            penitent_utterance, phase=state.current_phase
        )
        h_refusal = _detect_refusal(penitent_utterance)

        try:
            raw = await self._llm.generate(prompt, system=self._system)
            turn = self._parse_turn(raw, fallback_phase=state.current_phase)
        except Exception as exc:  # noqa: BLE001 — LLM is enhancement, not requirement
            logger.warning("confessgpt_llm_unavailable", error=str(exc)[:200])
            turn = _liturgy_turn(
                state.current_phase,
                penitent_utterance=penitent_utterance,
                contrition=h_contrition,
                amendment=h_amendment,
                refusal=h_refusal,
            )
        else:
            # Merge heuristic signals onto the LLM turn so contrition /
            # amendment / refusal cues from the penitent are not lost
            # when the model forgets to set the flags.
            turn = turn.model_copy(
                update={
                    "contrition_detected": _merge_tri(
                        turn.contrition_detected, h_contrition
                    ),
                    "amendment_purpose_detected": _merge_tri(
                        turn.amendment_purpose_detected, h_amendment
                    ),
                    "explicit_refusal_of_repentance": (
                        turn.explicit_refusal_of_repentance or bool(h_refusal)
                    ),
                }
            )

        # Apply doctrinal guards: code wins over LLM. Order matters —
        # explicit refusal must short-circuit before absolution check.
        turn = self._apply_doctrine_guards(turn, state)

        # Anti-loop pass: if the LLM keeps the rite on the same phase
        # while the penitent is providing contrition + amendment, force
        # the next canonical phase so the user is not stuck.
        turn = self._break_liturgical_loop(turn, state, h_contrition, h_amendment)

        # Merge flags into state. Once a flag is set true we keep it
        # (the penitent does not un-repent across turns within a rite).
        new_contrition = _merge_tri(state.contrition_detected, turn.contrition_detected)
        new_amendment = _merge_tri(
            state.amendment_purpose_detected, turn.amendment_purpose_detected
        )
        new_refusal = (
            state.explicit_refusal_of_repentance or turn.explicit_refusal_of_repentance
        )

        # Phase visit counters — track repeated stalls.
        new_atto_attempts = state.atto_dolore_attempts + (
            1 if turn.phase == RitePhase.ATTO_DOLORE else 0
        )
        new_ascolto_attempts = state.ascolto_attempts + (
            1 if turn.phase == RitePhase.ASCOLTO else 0
        )

        next_state = state.model_copy(
            update={
                "current_phase": turn.next_phase,
                "contrition_detected": new_contrition,
                "amendment_purpose_detected": new_amendment,
                "explicit_refusal_of_repentance": new_refusal,
                "turn_count": state.turn_count + 1,
                "atto_dolore_attempts": new_atto_attempts,
                "ascolto_attempts": new_ascolto_attempts,
                "closed": is_terminal(turn.phase),
            }
        )
        await self._store.update(next_state)

        closed = False
        if is_terminal(turn.phase):
            await self._store.close(session_id)
            closed = True

        logger.info(
            "confessgpt_turn",
            session_id=session_id,
            phase=turn.phase.value,
            next_phase=turn.next_phase.value,
            turn_count=next_state.turn_count,
            closed=closed,
        )
        return turn, next_state, closed

    def _parse_turn(self, raw: str, *, fallback_phase: RitePhase) -> ConfessorTurn:
        """Parse the LLM JSON output, recovering gracefully on drift."""
        text = _extract_json(raw)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("confessgpt_llm_parse_fallback")
            return self._safe_fallback(fallback_phase)
        try:
            return ConfessorTurn.model_validate(payload)
        except ValidationError as exc:
            logger.warning("confessgpt_llm_validate_fallback", error=str(exc)[:200])
            return self._safe_fallback(fallback_phase)

    def _safe_fallback(self, phase: RitePhase) -> ConfessorTurn:
        """Last-resort utterance when the LLM produced unusable JSON.

        We never invent doctrine — pick a neutral pastoral nudge that
        keeps the rite going without making the agent silent.
        """
        return ConfessorTurn(
            phase=phase,
            utterance="Prendi il tempo che ti serve. Quando sei pronto, parla.",
            next_phase=phase,
            advance_on_user_reply=True,
            rationale="fallback",
        )

    def _break_liturgical_loop(
        self,
        turn: ConfessorTurn,
        state: SessionState,
        heuristic_contrition: bool | None,
        heuristic_amendment: bool | None,
    ) -> ConfessorTurn:
        """Force phase progression when the LLM keeps stalling.

        Catches two common pathologies:

        - ATTO_DOLORE repeated more than twice while the penitent
          clearly expressed contrition + amendment in the current or
          previous turn. Forces ASSOLUZIONE.
        - ASCOLTO repeated more than ``MAX_ASCOLTO`` times even when
          the penitent has stopped enumerating. Forces ESORTAZIONE.
        """
        effective_contrition = (
            state.contrition_detected
            or turn.contrition_detected
            or heuristic_contrition
        )
        effective_amendment = (
            state.amendment_purpose_detected
            or turn.amendment_purpose_detected
            or heuristic_amendment
        )

        # Loop on ATTO_DOLORE after >=2 attempts with contrition signalled.
        if (
            turn.phase == RitePhase.ATTO_DOLORE
            and state.atto_dolore_attempts >= 2
            and bool(effective_contrition)
            and bool(effective_amendment)
            and not (
                state.explicit_refusal_of_repentance
                or turn.explicit_refusal_of_repentance
            )
        ):
            logger.info("confessgpt_loop_break_to_absolution")
            return ConfessorTurn(
                phase=RitePhase.ASSOLUZIONE,
                utterance=CANONICAL_ABSOLUTION,
                next_phase=RitePhase.CONGEDO,
                advance_on_user_reply=True,
                contrition_detected=True,
                amendment_purpose_detected=True,
                rationale="loop_break:atto_dolore",
            )

        # Loop on ASCOLTO after >=4 attempts → push to ESORTAZIONE.
        if turn.phase == RitePhase.ASCOLTO and state.ascolto_attempts >= 4:
            logger.info("confessgpt_loop_break_to_esortazione")
            utt, nxt, adv = _LITURGY[RitePhase.ESORTAZIONE]
            return ConfessorTurn(
                phase=RitePhase.ESORTAZIONE,
                utterance=utt,
                next_phase=nxt,
                advance_on_user_reply=adv,
                contrition_detected=turn.contrition_detected,
                amendment_purpose_detected=turn.amendment_purpose_detected,
                rationale="loop_break:ascolto",
            )

        return turn

    def _apply_doctrine_guards(
        self, turn: ConfessorTurn, state: SessionState
    ) -> ConfessorTurn:
        """Override LLM decisions that violate sacramental doctrine."""

        # Guard 1: explicit refusal of repentance → no absolution, ever.
        will_refuse = (
            state.explicit_refusal_of_repentance or turn.explicit_refusal_of_repentance
        )
        if will_refuse and turn.phase == RitePhase.ASSOLUZIONE:
            logger.warning("confessgpt_absolution_blocked_refusal")
            return ConfessorTurn(
                phase=RitePhase.INVITO_RIFLESSIONE,
                utterance=DEFAULT_REFUSAL_UTTERANCE,
                next_phase=RitePhase.CONGEDO,
                advance_on_user_reply=False,
                contrition_detected=False,
                amendment_purpose_detected=False,
                explicit_refusal_of_repentance=True,
                rationale="guard:refusal",
            )

        # Guard 2: absolution requires contrition + amendment purpose.
        if turn.phase == RitePhase.ASSOLUZIONE:
            effective_contrition = _merge_tri(
                state.contrition_detected, turn.contrition_detected
            )
            effective_amendment = _merge_tri(
                state.amendment_purpose_detected,
                turn.amendment_purpose_detected,
            )
            if not (effective_contrition and effective_amendment):
                logger.warning("confessgpt_absolution_blocked_no_contrition")
                return ConfessorTurn(
                    phase=RitePhase.ATTO_DOLORE,
                    utterance=(
                        "Prima della formula, esprimi a parole il tuo "
                        "dolore per i peccati e il proposito di non "
                        "offendere più il Signore."
                    ),
                    next_phase=RitePhase.ATTO_DOLORE,
                    advance_on_user_reply=True,
                    rationale="guard:contrition_required",
                )

        # Guard 3: formula integrity — if absolution phase, ensure the
        # canonical CEI formula was emitted. Otherwise replace it.
        if turn.phase == RitePhase.ASSOLUZIONE and not _has_full_absolution(
            turn.utterance
        ):
            logger.warning("confessgpt_absolution_formula_replaced")
            return turn.model_copy(
                update={"utterance": CANONICAL_ABSOLUTION, "rationale": "guard:formula"}
            )

        return turn


class SessionNotFound(LookupError):
    """Raised when a turn references an unknown session id."""


class SessionAlreadyClosed(RuntimeError):
    """Raised when a turn is submitted on an already-closed session."""


def _merge_tri(prior: bool | None, current: bool | None) -> bool | None:
    """Merge two tri-state flags; True is sticky once observed."""
    if prior is True or current is True:
        return True
    if prior is False or current is False:
        return False
    return None
