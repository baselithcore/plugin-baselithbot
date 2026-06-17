"""Immutable audit-trail domain models for the digital twin.

Every governance-relevant action — a reply approved/rejected/auto-sent, a
contact whitelisted/revoked, the style retrained, the twin paused/resumed — is
recorded as a frozen :class:`TwinAuditEvent`. The trail is append-only and
owner-scoped; the store never updates or deletes an event. This is the
compliance backbone separating the enterprise build from the prototype.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditAction(str, Enum):
    """The closed set of audited governance actions."""

    REPLY_APPROVED = "reply.approved"
    REPLY_REJECTED = "reply.rejected"
    REPLY_AUTO_SENT = "reply.auto_sent"
    REPLY_SEND_FAILED = "reply.send_failed"
    WHITELIST_ADDED = "whitelist.added"
    WHITELIST_REMOVED = "whitelist.removed"
    FACT_CURATED = "fact.curated"
    STYLE_TRAINED = "style.trained"
    TWIN_PAUSED = "twin.paused"
    TWIN_RESUMED = "twin.resumed"
    WEBHOOK_REJECTED = "webhook.rejected"


class TwinAuditEvent(BaseModel):
    """A single, immutable entry in the twin's audit trail."""

    model_config = ConfigDict(frozen=True)

    id: str
    action: AuditAction
    actor: str = "system"
    resource: str | None = None  # e.g. reply id or contact id.
    success: bool = True
    ip_address: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    at: datetime = Field(default_factory=_utcnow)


__all__ = ["AuditAction", "TwinAuditEvent"]
