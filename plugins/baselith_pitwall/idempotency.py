"""Tiny in-memory idempotency cache for safe POST retries.

When a client sends an ``Idempotency-Key`` header, a repeated request with the
same key (per tenant) returns the first result instead of re-executing — so a
network retry of a telemetry/radio/ack POST can't double-count. Bounded LRU;
in-memory and per-process (a multi-replica deployment would back this with a
shared store).
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

_CAPACITY = 4096


class IdempotencyCache:
    """Bounded LRU map from ``(tenant, key)`` to a stored result."""

    def __init__(self, capacity: int = _CAPACITY) -> None:
        self._capacity = capacity
        self._store: OrderedDict[tuple[str, str], Any] = OrderedDict()

    def get(self, tenant: str, key: str) -> Any | None:
        """Return the cached result for a key, or None; refreshes LRU order."""
        composite = (tenant, key)
        if composite not in self._store:
            return None
        self._store.move_to_end(composite)
        return self._store[composite]

    def put(self, tenant: str, key: str, value: Any) -> None:
        """Store a result, evicting the least-recently-used entry when full."""
        composite = (tenant, key)
        self._store[composite] = value
        self._store.move_to_end(composite)
        while len(self._store) > self._capacity:
            self._store.popitem(last=False)


__all__ = ["IdempotencyCache"]
