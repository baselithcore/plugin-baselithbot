"""The :class:`WhatsAppGateway` contract shared by every backend.

The twin talks only to this Protocol — never to a concrete client — so the
OpenWA REST backend, a future fork, and the in-memory fake are fully
interchangeable (dependency inversion). Every method is ``async`` so a real
network backend never forces a blocking call onto the event loop.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import OutboundMessage, SendReceipt


@runtime_checkable
class WhatsAppGateway(Protocol):
    """Abstract async contract for sending WhatsApp messages and health checks."""

    async def connect(self) -> None:
        """Establish/verify the session. No-op for the fake backend."""
        ...

    async def disconnect(self) -> None:
        """Tear down the session and release resources."""
        ...

    async def is_connected(self) -> bool:
        """Return whether the gateway currently holds a live session."""
        ...

    async def send(self, message: OutboundMessage) -> SendReceipt:
        """Send a message to a contact and return the gateway's receipt."""
        ...


__all__ = ["WhatsAppGateway"]
