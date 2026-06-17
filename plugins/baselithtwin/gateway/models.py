"""WhatsApp wire models exchanged with the gateway.

A deliberately small, transport-agnostic shape so the OpenWA REST/webhook
backend and the in-memory fake speak the same language. Maps cleanly onto the
``@open-wa/wa-automate`` message envelope without leaking its idiosyncrasies
into the domain.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MediaKind(str, Enum):
    """Supported media payload kinds for inbound/outbound messages."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"


class MediaRef(BaseModel):
    """A reference to a media payload (URL or base64), never the raw bytes."""

    model_config = ConfigDict(frozen=True)

    kind: MediaKind = MediaKind.TEXT
    url: str | None = None
    mime_type: str | None = None
    caption: str | None = None


class InboundMessage(BaseModel):
    """A message received from a WhatsApp contact via the gateway."""

    model_config = ConfigDict(frozen=True)

    id: str
    contact_id: str  # WhatsApp chat id, e.g. "39333...@c.us".
    contact_name: str | None = None
    text: str = ""
    media: MediaRef | None = None
    from_me: bool = False  # True for the owner's own outbound history.
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OutboundMessage(BaseModel):
    """A message the twin asks the gateway to send."""

    model_config = ConfigDict(frozen=True)

    contact_id: str
    text: str
    media: MediaRef | None = None
    quoted_message_id: str | None = None


class SendReceipt(BaseModel):
    """The gateway's acknowledgement of a send attempt."""

    model_config = ConfigDict(frozen=True)

    ok: bool
    message_id: str | None = None
    error: str | None = None


__all__ = [
    "MediaKind",
    "MediaRef",
    "InboundMessage",
    "OutboundMessage",
    "SendReceipt",
]
