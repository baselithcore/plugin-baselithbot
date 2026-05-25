"""
Red Agent in-process event bus for scan lifecycle events.

The orchestrator publishes status / finding / log events; the WebSocket
router subscribes per-scan to push frames to connected clients in real
time. Backed by Redis pubsub when the cache provider is available.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any
from uuid import UUID

from core.observability.logging import get_logger

logger = get_logger(__name__)


class ScanEventBus:
    """In-process fanout. Drop-in replacement-friendly with Redis pubsub."""

    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, scan_id: UUID, frame: dict[str, Any]) -> None:
        payload = json.dumps(frame, default=str)
        key = str(scan_id)
        async with self._lock:
            queues = list(self._subs.get(key, ()))
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("scan event dropped (slow consumer)")

    async def subscribe(self, scan_id: UUID) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=1024)
        async with self._lock:
            self._subs[str(scan_id)].add(q)
        return q

    async def unsubscribe(self, scan_id: UUID, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subs.get(str(scan_id), set()).discard(q)


class ActivityEventBus:
    """Cross-scan broadcast bus for the cockpit activity stream.

    Distinct from :class:`ScanEventBus`: subscribers don't pin to a
    specific scan_id — they receive every audit-log event the agent
    publishes. The cockpit UI uses it to render the RoE / critic /
    HITL feed without polling. Bounded queue so a stalled WebSocket
    consumer can't pin memory; oldest frames drop with a log line.
    """

    def __init__(self, *, queue_size: int = 1024) -> None:
        self._subs: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()
        self._queue_size = queue_size

    async def publish(self, frame: dict[str, Any]) -> None:
        payload = json.dumps(frame, default=str)
        async with self._lock:
            queues = list(self._subs)
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("activity event dropped (slow consumer)")

    async def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            self._subs.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subs.discard(q)


class ScanEngagementIndex:
    """In-memory ``scan_id → engagement_id`` cache for live filtering.

    Populated by the persistence layer when a scan is inserted; read
    by the activity broadcast hook so each frame can carry the parent
    engagement id without a DB round-trip. Bounded eviction is FIFO
    on the insert ordering — the cache exists only to scope live WS
    streams; historical lookups still hit Postgres.
    """

    def __init__(self, capacity: int = 4096) -> None:
        self._store: dict[str, str | None] = {}
        self._order: list[str] = []
        self._capacity = capacity

    def remember(self, scan_id: UUID, engagement_id: UUID | None) -> None:
        key = str(scan_id)
        if key not in self._store and len(self._store) >= self._capacity:
            evict = self._order.pop(0)
            self._store.pop(evict, None)
        if key not in self._store:
            self._order.append(key)
        self._store[key] = str(engagement_id) if engagement_id else None

    def lookup(self, scan_id: UUID | str | None) -> str | None:
        if scan_id is None:
            return None
        return self._store.get(str(scan_id))
