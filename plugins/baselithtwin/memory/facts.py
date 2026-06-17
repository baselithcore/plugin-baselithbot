"""Heuristic salient-fact extraction from conversation.

Distills durable, self-referential statements ("I live in Milan", "my flight is
on Friday") from a contact's messages into :class:`SalientFact` candidates. This
is a deliberately conservative, dependency-free pass — it favours precision over
recall so the long-term memory stays trustworthy. An LLM-backed extractor can be
layered on later behind the same return type.
"""

from __future__ import annotations

import re
import uuid

from ..gateway.models import InboundMessage
from ..models import SalientFact

# First-person, commitment, and scheduling cues that signal a durable fact.
_CUE_PATTERNS = (
    re.compile(r"\b(i\s+(?:am|live|work|have|like|hate|need|prefer))\b", re.I),
    re.compile(r"\b(my\s+\w+\s+is)\b", re.I),
    re.compile(r"\b(sono|abito|lavoro|mi\s+chiamo|ho\s+\w+|preferisco)\b", re.I),
    re.compile(r"\b(remember|ricorda|appointment|meeting|deadline|scadenza)\b", re.I),
)
_MIN_CHARS = 10
_MAX_CHARS = 240


def _salience(text: str, cue_hits: int) -> float:
    """Score 0..1 — more cues and richer (but not rambling) text scores higher."""
    base = 0.35 + 0.18 * cue_hits
    if "?" in text:  # questions are rarely durable facts
        base -= 0.15
    if len(text) > _MAX_CHARS:
        base -= 0.1
    return max(0.0, min(1.0, base))


def extract_facts(message: InboundMessage, threshold: float = 0.5) -> list[SalientFact]:
    """Extract salient-fact candidates from a single inbound message.

    Args:
        message: The message to mine.
        threshold: Minimum salience required to keep a candidate.

    Returns:
        Zero or more :class:`SalientFact` records above the threshold.
    """
    text = message.text.strip()
    if not (_MIN_CHARS <= len(text) <= _MAX_CHARS):
        return []
    cue_hits = sum(1 for pat in _CUE_PATTERNS if pat.search(text))
    if cue_hits == 0:
        return []
    salience = _salience(text, cue_hits)
    if salience < threshold:
        return []
    tags = [w.lower() for w in re.findall(r"[#]([\w-]+)", text)]
    return [
        SalientFact(
            id=str(uuid.uuid4()),
            contact_id=message.contact_id,
            text=text,
            salience=round(salience, 3),
            tags=tags,
            source_message_id=message.id,
        )
    ]


__all__ = ["extract_facts"]
