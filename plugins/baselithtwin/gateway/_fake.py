"""In-memory loopback gateway — the zero-infra default and test backend.

Records every sent message in an inspectable buffer and is always "connected".
Smoke tests drive the whole ingest→draft→send vertical against this backend
without an OpenWA sidecar or a network.
"""

from __future__ import annotations

from itertools import count

from .models import OutboundMessage, SendReceipt


class FakeGateway:
    """A deterministic, dependency-free :class:`WhatsAppGateway` implementation."""

    def __init__(self) -> None:
        self._connected = True
        self._ids = count(1)
        self.sent: list[OutboundMessage] = []

    async def connect(self) -> None:
        """Mark the loopback session as live."""
        self._connected = True

    async def disconnect(self) -> None:
        """Mark the loopback session as down."""
        self._connected = False

    async def is_connected(self) -> bool:
        """Return the simulated connection state."""
        return self._connected

    async def send(self, message: OutboundMessage) -> SendReceipt:
        """Record the outbound message and return a synthetic receipt."""
        if not self._connected:
            return SendReceipt(ok=False, error="fake gateway disconnected")
        self.sent.append(message)
        return SendReceipt(ok=True, message_id=f"fake-{next(self._ids)}")


__all__ = ["FakeGateway"]
