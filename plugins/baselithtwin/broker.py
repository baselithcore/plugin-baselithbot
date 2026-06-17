"""In-process async event broker for the real-time dashboard feed.

A minimal fan-out pub/sub over :class:`asyncio.Queue` subscribers. The service
publishes :class:`StreamEvent`s (inbound message, draft, auto-send, queue, human
decision) and each connected SSE client drains its own bounded queue. Slow
clients drop the oldest event rather than back-pressuring the ingest path, so a
stalled browser tab never blocks WhatsApp processing.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from .models import StreamEvent

_QUEUE_MAXSIZE = 256


class EventBroker:
    """Fan-out broker delivering :class:`StreamEvent`s to many SSE subscribers."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[StreamEvent]] = set()

    async def publish(self, event: StreamEvent) -> None:
        """Deliver an event to every subscriber, dropping the oldest if full."""
        for queue in tuple(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()  # evict oldest to make room
                except asyncio.QueueEmpty:  # pragma: no cover - race-safe guard
                    pass
            queue.put_nowait(event)

    async def subscribe(self) -> AsyncIterator[StreamEvent]:
        """Yield events for one client until it disconnects (cancelled)."""
        queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        """Number of currently connected subscribers (for diagnostics)."""
        return len(self._subscribers)


__all__ = ["EventBroker"]
