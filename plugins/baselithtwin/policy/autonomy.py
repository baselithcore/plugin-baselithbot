"""The autonomy policy: decides whether a draft is auto-sent or queued.

This is the governance seam of the twin. It maps the configured
:class:`AutonomyMode`, the contact's whitelist status, and an anti-runaway rate
budget onto one of two outcomes — auto-send or human-in-the-loop queue. Keeping
this decision pure and centralised means every send path is governed identically
and the rule is trivially auditable.
"""

from __future__ import annotations

from enum import Enum

from ..config import AutonomyMode


class Decision(str, Enum):
    """The governance outcome for a single drafted reply."""

    AUTO_SEND = "auto_send"
    QUEUE = "queue"


def decide(
    mode: AutonomyMode,
    *,
    is_whitelisted: bool,
    rate_ok: bool,
    confidence: float,
    min_confidence: float = 0.25,
) -> Decision:
    """Resolve the governance decision for a drafted reply.

    Rules (safe-by-default):
        * ``SUGGEST`` → always queue.
        * ``WHITELIST`` → auto-send only to whitelisted contacts.
        * ``FULL`` → auto-send to everyone.
        * Auto-send is always downgraded to queue when the per-contact rate
          budget is exhausted or the draft confidence is below ``min_confidence``.

    Args:
        mode: The configured autonomy level.
        is_whitelisted: Whether the contact is on the auto-reply whitelist.
        rate_ok: Whether the per-contact rate budget still allows an auto-send.
        confidence: The draft's self-reported confidence (0..1).
        min_confidence: Floor below which a draft is never auto-sent.

    Returns:
        ``Decision.AUTO_SEND`` or ``Decision.QUEUE``.
    """
    if mode is AutonomyMode.SUGGEST:
        return Decision.QUEUE
    if confidence < min_confidence or not rate_ok:
        return Decision.QUEUE
    if mode is AutonomyMode.FULL:
        return Decision.AUTO_SEND
    if mode is AutonomyMode.WHITELIST and is_whitelisted:
        return Decision.AUTO_SEND
    return Decision.QUEUE


__all__ = ["decide", "Decision"]
