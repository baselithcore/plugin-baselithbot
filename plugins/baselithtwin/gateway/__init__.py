"""WhatsApp gateway abstraction and its interchangeable backends."""

from __future__ import annotations

from ._factory import build_gateway
from ._fake import FakeGateway
from ._openwa import OpenWAGateway
from ._protocol import WhatsAppGateway
from .models import (
    InboundMessage,
    MediaKind,
    MediaRef,
    OutboundMessage,
    SendReceipt,
)

__all__ = [
    "WhatsAppGateway",
    "build_gateway",
    "FakeGateway",
    "OpenWAGateway",
    "InboundMessage",
    "OutboundMessage",
    "SendReceipt",
    "MediaRef",
    "MediaKind",
]
