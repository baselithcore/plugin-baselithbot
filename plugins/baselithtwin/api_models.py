"""Request/response payload models for the FastAPI surface.

Kept separate from the domain models so the HTTP contract can evolve
independently of internal representations. The router validates against these
and delegates to :class:`TwinService`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .gateway.models import MediaRef


class InboundWebhook(BaseModel):
    """Normalised inbound-message payload accepted by the OpenWA webhook."""

    id: str
    contact_id: str = Field(..., description="WhatsApp chat id, e.g. '39...@c.us'.")
    contact_name: str | None = None
    text: str = ""
    from_me: bool = False
    media: MediaRef | None = None


class WhitelistRequest(BaseModel):
    """Request body to authorise a contact for auto-reply."""

    contact_id: str
    display_name: str | None = None
    note: str | None = None


class FactRequest(BaseModel):
    """Manually curated salient fact to inject into long-term memory."""

    contact_id: str
    text: str
    salience: float = Field(default=0.6, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class MessageResponse(BaseModel):
    """Generic localized acknowledgement envelope."""

    message: str


__all__ = [
    "InboundWebhook",
    "WhitelistRequest",
    "FactRequest",
    "MessageResponse",
]
