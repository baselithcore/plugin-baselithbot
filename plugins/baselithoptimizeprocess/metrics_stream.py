"""In-process pub/sub broker backing the real-time SSE metrics feed.

Each subscriber gets its own bounded :class:`asyncio.Queue`; publishes fan out to
every queue subscribed to the relevant process. Bounded queues mean a slow client
drops the oldest events instead of growing memory without limit. The broker is
transport-agnostic — the router turns the yielded dicts into SSE frames.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

# Per-subscriber backlog. A slow consumer drops the oldest event past this.
_QUEUE_MAXSIZE = 256


class MetricsBroker:
    """Fan-out broker mapping a process id to a set of subscriber queues."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    async def publish(self, process_id: str, event: dict[str, Any]) -> None:
        """Broadcast an event to all subscribers of a process.

        Non-blocking: if a subscriber's queue is full, the oldest event is
        evicted to make room so one stalled client cannot back-pressure others.
        """
        async with self._lock:
            queues = list(self._subscribers.get(process_id, ()))
        for queue in queues:
            if queue.full():
                with suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with suppress(asyncio.QueueFull):
                queue.put_nowait(event)

    async def subscribe(self, process_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield events for a process until the consumer disconnects.

        Usage::

            async for event in broker.subscribe(pid):
                ...  # forward as an SSE frame

        The subscriber queue is registered on entry and always removed on exit,
        even if the consuming task is cancelled.
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        async with self._lock:
            self._subscribers.setdefault(process_id, set()).add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            async with self._lock:
                subs = self._subscribers.get(process_id)
                if subs is not None:
                    subs.discard(queue)
                    if not subs:
                        del self._subscribers[process_id]

    async def subscriber_count(self, process_id: str) -> int:
        """Return how many live subscribers a process currently has."""
        async with self._lock:
            return len(self._subscribers.get(process_id, ()))


__all__ = ["MetricsBroker"]
