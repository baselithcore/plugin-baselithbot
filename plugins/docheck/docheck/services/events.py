"""In-process event bus for streaming analysis progress to WS subscribers.

Per-doc_id asyncio.Queue. Pub-sub semplice (no persistence). Stato MVP single-process.
"""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

_queues: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
_lock = asyncio.Lock()


async def publish(doc_id: str, event: dict[str, Any]) -> None:
    async with _lock:
        subs = list(_queues.get(doc_id, []))
    for q in subs:
        with suppress(asyncio.QueueFull):
            q.put_nowait(event)


@asynccontextmanager
async def subscribe(doc_id: str) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1024)
    async with _lock:
        _queues[doc_id].append(q)
    try:
        yield q
    finally:
        async with _lock:
            if q in _queues[doc_id]:
                _queues[doc_id].remove(q)
            if not _queues[doc_id]:
                _queues.pop(doc_id, None)
