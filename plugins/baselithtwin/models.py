"""Core domain models for the digital twin.

Pydantic models that flow across the service, store, router, and MCP surfaces.
WhatsApp wire models live in :mod:`gateway.models`; these are the twin's own
domain entities: salient facts, drafted/pending replies, whitelist entries, and
the aggregate status surfaced to the dashboard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    """Timezone-aware UTC now (kept central so models stay deterministic)."""
    return datetime.now(timezone.utc)


class ReplyStatus(str, Enum):
    """Lifecycle of a drafted reply under the autonomy policy."""

    DRAFT = "draft"  # generated, not yet decided.
    QUEUED = "queued"  # awaiting human approval (HITL).
    AUTO_SENT = "auto_sent"  # auto-sent under the whitelist/full policy.
    APPROVED = "approved"  # human-approved and sent.
    REJECTED = "rejected"  # human-rejected; never sent.
    FAILED = "failed"  # gateway send failed.


class SalientFact(BaseModel):
    """A durable fact distilled from conversation, stored in long-term memory."""

    model_config = ConfigDict(frozen=True)

    id: str
    contact_id: str
    text: str
    salience: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    source_message_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class DraftReply(BaseModel):
    """An LLM- (or template-) generated reply candidate for one inbound message."""

    contact_id: str
    in_reply_to: str
    text: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    style_applied: bool = False
    degraded: bool = False  # True when produced by the template fallback.
    rationale: str | None = None


class PendingReply(BaseModel):
    """A drafted reply tracked through the approval lifecycle."""

    id: str
    contact_id: str
    in_reply_to: str
    inbound_text: str
    draft: DraftReply
    status: ReplyStatus = ReplyStatus.QUEUED
    created_at: datetime = Field(default_factory=_utcnow)
    decided_at: datetime | None = None
    decided_by: str | None = None


class WhitelistEntry(BaseModel):
    """A contact authorised for auto-reply under the whitelist autonomy mode."""

    model_config = ConfigDict(frozen=True)

    contact_id: str
    display_name: str | None = None
    note: str | None = None
    added_at: datetime = Field(default_factory=_utcnow)


class TwinStatus(BaseModel):
    """Aggregate health/state of the twin for the dashboard header."""

    owner_name: str
    autonomy: str
    gateway: str
    gateway_connected: bool
    style_trained: bool
    style_messages: int
    whitelist_size: int
    pending_replies: int
    salient_facts: int
    paused: bool = False
    version: str


class StreamEvent(BaseModel):
    """A real-time event framed onto the SSE channel for the dashboard."""

    type: str  # e.g. "inbound", "draft", "auto_sent", "queued", "decided".
    payload: dict[str, Any] = Field(default_factory=dict)
    at: datetime = Field(default_factory=_utcnow)


__all__ = [
    "ReplyStatus",
    "SalientFact",
    "DraftReply",
    "PendingReply",
    "WhitelistEntry",
    "TwinStatus",
    "StreamEvent",
]
