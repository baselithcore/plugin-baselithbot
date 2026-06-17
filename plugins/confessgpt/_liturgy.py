"""ConfessGPT — canonical liturgy table and fallback turn builder.

Extracted from flow.py to keep that module under the 500-LOC cap.
Contains the deterministic Italian utterances taken straight from the
Roman Rite (CEI) and the helper that builds a ``ConfessorTurn`` without
LLM intervention.

Public API:
    _LITURGY                            — phase → (utterance, next_phase, advance)
    _liturgy_turn(phase, *, ...)        -> ConfessorTurn
    CANONICAL_ABSOLUTION                — canonical CEI absolution string
    DEFAULT_REFUSAL_UTTERANCE           — refusal response string
"""

from __future__ import annotations

from .models import ConfessorTurn, RitePhase
from ._heuristics import _signals_listen_end

# ---------------------------------------------------------------------------
# Canonical strings.
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Liturgy fallback table.
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
