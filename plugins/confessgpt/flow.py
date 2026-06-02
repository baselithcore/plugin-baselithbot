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
import re
from typing import Protocol

from core.observability.logging import get_logger
from pydantic import ValidationError

from .models import ConfessorTurn, RitePhase, SessionState
from .prompt import build_turn_prompt
from .sigillum import SigillumStore, is_terminal

logger = get_logger(__name__)


class LLMBackend(Protocol):
    """Minimal LLM interface the flow depends on.

    Any object exposing ``async generate(prompt, *, system) -> str``
    satisfies this. We do not import core.services.llm.LLMService
    directly here to keep the flow unit-testable with simple fakes.
    """

    async def generate(self, prompt: str, *, system: str) -> str: ...


# Hardcoded canonical CEI absolution. Used to validate that the LLM did
# not paraphrase or shorten the formula.
ABSOLUTION_REQUIRED_FRAGMENTS: tuple[str, ...] = (
    "Dio, Padre di misericordia",
    "ti assolvo dai tuoi peccati",
    "nel nome del Padre",
    "del Figlio",
    "Spirito Santo",
)

CANONICAL_ABSOLUTION: str = (
    "Dio, Padre di misericordia, che ha riconciliato a sé il mondo nella "
    "morte e risurrezione del suo Figlio, e ha effuso lo Spirito Santo "
    "per la remissione dei peccati, ti conceda, mediante il ministero "
    "della Chiesa, il perdono e la pace. E io ti assolvo dai tuoi "
    "peccati nel nome del Padre e del Figlio ✝ e dello Spirito Santo."
)

DEFAULT_REFUSAL_UTTERANCE: str = (
    "Figlio mio, il sacramento esige un cuore che si pente e che propone, "
    "con l'aiuto di Dio, di non offenderlo più. Senza questo non posso "
    "assolverti, non per durezza ma per verità. Torna quando il tuo cuore "
    "sarà pronto: il Padre attende. Va' in pace."
)


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


# ---------------------------------------------------------------------------
# Liturgy fallback — canonical phrases when the LLM is unavailable.
#
# Each phase has a deterministic Italian utterance taken straight from the
# Roman Rite (CEI). When the LLM is unreachable, off-budget, or returns
# unusable output, the flow still completes the sacrament using these
# texts. The LLM is a personalization layer, not a doctrinal one.
# ---------------------------------------------------------------------------

_LITURGY: dict[RitePhase, tuple[str, RitePhase, bool]] = {
    # phase: (utterance, next_phase, advance_on_user_reply)
    RitePhase.ACCOGLIENZA: (
        "Sia lodato Gesù Cristo. Il Signore sia nel tuo cuore perché tu possa "
        "confessare sinceramente i tuoi peccati.",
        RitePhase.INVITO,
        True,
    ),
    RitePhase.INVITO: (
        "Nel nome del Padre, del Figlio e dello Spirito Santo. Ti ascolto.",
        RitePhase.ASCOLTO,
        True,
    ),
    RitePhase.ASCOLTO: (
        "Vuoi aggiungere altro?",
        RitePhase.ESORTAZIONE,
        True,
    ),
    RitePhase.ESORTAZIONE: (
        "Il Padre attende sempre il figlio che torna a casa. La sua "
        "misericordia è più grande di ogni peccato: lascia che ti rinnovi "
        "il cuore.",
        RitePhase.PENITENZA,
        True,
    ),
    RitePhase.PENITENZA: (
        "Per penitenza ti propongo di recitare tre Padre Nostro, tre Ave "
        "Maria e di compiere un gesto concreto di carità verso chi hai "
        "ferito o trascurato.",
        RitePhase.ATTO_DOLORE,
        True,
    ),
    RitePhase.ATTO_DOLORE: (
        "Ora esprimi con le tue parole il dolore per i tuoi peccati e il "
        "proposito, con l'aiuto di Dio, di non offenderlo più. Se non "
        "ricordi una formula, ripeti: «Mio Dio, mi pento e mi dolgo con "
        "tutto il cuore dei miei peccati; propongo con il tuo santo aiuto "
        "di non offenderti mai più.»",
        RitePhase.ASSOLUZIONE,
        True,
    ),
    RitePhase.ASSOLUZIONE: (
        CANONICAL_ABSOLUTION,
        RitePhase.CONGEDO,
        True,
    ),
    RitePhase.CONGEDO: (
        "Rendiamo grazie al Signore, perché è buono. Va' in pace.",
        RitePhase.CONGEDO,
        False,
    ),
    RitePhase.INVITO_RIFLESSIONE: (
        DEFAULT_REFUSAL_UTTERANCE,
        RitePhase.CONGEDO,
        False,
    ),
    RitePhase.VERIFICA_CONTRIZIONE: (
        "Senti nel cuore il dolore per i tuoi peccati?",
        RitePhase.ATTO_DOLORE,
        True,
    ),
}


def _liturgy_turn(
    phase: RitePhase,
    *,
    penitent_utterance: str,
    contrition: bool | None,
    amendment: bool | None,
    refusal: bool,
) -> ConfessorTurn:
    """Build a canonical turn for ``phase`` without LLM intervention.

    Heuristics:
    - If the penitent explicitly refused repentance, jump to
      ``INVITO_RIFLESSIONE``.
    - If we are in ``ASCOLTO`` and the penitent has given some
      utterance (i.e. at least one sin enumerated), close the listening
      with the standard "anything else?" probe. On a *second* listening
      turn following silence or a closing phrase, advance to
      ``ESORTAZIONE``.
    """
    if refusal:
        utt, nxt, adv = _LITURGY[RitePhase.INVITO_RIFLESSIONE]
        return ConfessorTurn(
            phase=RitePhase.INVITO_RIFLESSIONE,
            utterance=utt,
            next_phase=nxt,
            advance_on_user_reply=adv,
            contrition_detected=False,
            amendment_purpose_detected=False,
            explicit_refusal_of_repentance=True,
            rationale="liturgy:refusal",
        )

    # ASCOLTO progression: close the listening when the penitent signals
    # they are done ("è tutto", "basta", "non ricordo altro", "ho finito",
    # "mi accuso di questi peccati").
    if phase is RitePhase.ASCOLTO and _signals_listen_end(penitent_utterance):
        utt, nxt, adv = _LITURGY[RitePhase.ESORTAZIONE]
        return ConfessorTurn(
            phase=RitePhase.ESORTAZIONE,
            utterance=utt,
            next_phase=nxt,
            advance_on_user_reply=adv,
            contrition_detected=contrition,
            rationale="liturgy:listen_end",
        )

    utt, nxt, adv = _LITURGY[phase]
    # When the penitent recites the Act of Contrition the heuristic will
    # have lit both flags — propagate them so the doctrine guard does
    # not loop back asking for contrition again.
    return ConfessorTurn(
        phase=phase,
        utterance=utt,
        next_phase=nxt,
        advance_on_user_reply=adv,
        contrition_detected=contrition,
        amendment_purpose_detected=amendment,
        rationale="liturgy",
    )


# ---------------------------------------------------------------------------
# Heuristic detectors over the penitent utterance.
# ---------------------------------------------------------------------------

_CONTRITION_TOKENS: tuple[str, ...] = (
    "mi pento",
    "sono pentit",
    "mi dolgo",
    "mi rincresce",
    "mi vergogn",
    "perdona",
    "perdono",
    "chiedo perdono",
    "ho peccato",
    "propongo di non",
    "non lo farò più",
    "non lo faro piu",
    "non voglio più peccare",
)

_AMENDMENT_TOKENS: tuple[str, ...] = (
    "propongo di non",
    "propongo con",
    "non lo farò più",
    "non lo faro piu",
    "non lo rifarò",
    "non lo rifaro",
    "non offenderti",
    "non offenderlo",
    "non peccare più",
    "non peccare piu",
    "voglio cambiare",
    "voglio convertirmi",
    "non commettere più",
    "non commettere piu",
    "prometto",
    "promesso",
    "lo giuro",
    "giuro di",
    "mai più",
    "mai piu",
    "convertirmi",
    "cambiare vita",
    "santo aiuto",
    "fuggire le occasioni",
    "atto di dolore",
)

_REFUSAL_TOKENS: tuple[str, ...] = (
    "non mi pento",
    "non sono pentit",
    "continuerò a",
    "continuero a",
    "voglio continuare",
    "non voglio cambiare",
    "non smetterò",
    "non smettero",
    "non ho intenzione di smettere",
    "lo rifarei",
)

_LISTEN_END_TOKENS: tuple[str, ...] = (
    "è tutto",
    "e' tutto",
    "basta",
    "ho finito",
    "non ricordo altro",
    "non ricordo nulla",
    "nient'altro",
    "niente altro",
    "mi accuso di questi peccati",
    "ho detto tutto",
)


def _detect_contrition(utterance: str) -> bool | None:
    """Return True if contrition is signalled, else None (unknown)."""
    text = utterance.lower()
    if any(tok in text for tok in _REFUSAL_TOKENS):
        return False
    if any(tok in text for tok in _CONTRITION_TOKENS):
        return True
    return None


def _detect_amendment(utterance: str) -> bool | None:
    """Return True if proposito-di-emendamento is signalled, else None.

    The caller can pass ``phase_hint`` via ``_detect_amendment_during``
    to take the Catholic doctrine shortcut: reciting the Act of
    Contrition during ATTO_DOLORE implicitly carries the firm purpose
    of amendment (CCC §1451). Without the hint we stay strict.
    """
    text = utterance.lower()
    if any(tok in text for tok in _REFUSAL_TOKENS):
        return False
    if any(tok in text for tok in _AMENDMENT_TOKENS):
        return True
    return None


def _detect_amendment_during(utterance: str, *, phase: RitePhase) -> bool | None:
    """Phase-aware amendment detector.

    During ATTO_DOLORE, any contrition expression also satisfies
    amendment (recital of the Act of Contrition contains the purpose
    of amendment by liturgical definition).
    """
    base = _detect_amendment(utterance)
    if base is not None:
        return base
    if phase == RitePhase.ATTO_DOLORE:
        text = utterance.lower()
        if any(tok in text for tok in _REFUSAL_TOKENS):
            return False
        if any(tok in text for tok in _CONTRITION_TOKENS):
            return True
    return None


def _detect_refusal(utterance: str) -> bool:
    """True only when the penitent explicitly refuses to repent."""
    text = utterance.lower()
    return any(tok in text for tok in _REFUSAL_TOKENS)


def _signals_listen_end(utterance: str) -> bool:
    """True when the penitent indicates the sin enumeration is over."""
    text = utterance.lower().strip()
    if not text:
        return False
    return any(tok in text for tok in _LISTEN_END_TOKENS)


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> str:
    """Pull the first JSON object out of the LLM response.

    Some providers wrap JSON in code fences or chatty prose. Be lenient
    on the wrapper; strict on the content.
    """
    match = _JSON_OBJECT_RE.search(text)
    return match.group(0) if match else text


def _has_full_absolution(text: str) -> bool:
    """Check that the absolution utterance contains every required fragment."""
    return all(fragment in text for fragment in ABSOLUTION_REQUIRED_FRAGMENTS)
