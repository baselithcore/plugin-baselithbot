"""ConfessGPT — heuristic detectors over penitent utterances.

All token tables and detection functions are here so that flow.py
stays under the 500-LOC cap. Nothing in this module carries state;
every function is a pure transformation of the input string.

Public API:
    _detect_contrition(utterance)          -> bool | None
    _detect_amendment(utterance)           -> bool | None
    _detect_amendment_during(utterance, *, phase) -> bool | None
    _detect_refusal(utterance)             -> bool
    _signals_listen_end(utterance)         -> bool
    _extract_json(text)                    -> str
    _has_full_absolution(text)             -> bool
    ABSOLUTION_REQUIRED_FRAGMENTS          — public constant
"""

from __future__ import annotations

import re

from .models import RitePhase

# ---------------------------------------------------------------------------
# Canonical absolution validation.
# ---------------------------------------------------------------------------

ABSOLUTION_REQUIRED_FRAGMENTS: tuple[str, ...] = (
    "Dio, Padre di misericordia",
    "ti assolvo dai tuoi peccati",
    "nel nome del Padre",
    "del Figlio",
    "Spirito Santo",
)


def _has_full_absolution(text: str) -> bool:
    """Check that the absolution utterance contains every required fragment."""
    return all(fragment in text for fragment in ABSOLUTION_REQUIRED_FRAGMENTS)


# ---------------------------------------------------------------------------
# Heuristic token tables.
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


# ---------------------------------------------------------------------------
# Detector functions.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# JSON extraction helper.
# ---------------------------------------------------------------------------

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> str:
    """Pull the first JSON object out of the LLM response.

    Some providers wrap JSON in code fences or chatty prose. Be lenient
    on the wrapper; strict on the content.
    """
    match = _JSON_OBJECT_RE.search(text)
    return match.group(0) if match else text
