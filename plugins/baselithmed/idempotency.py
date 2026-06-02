"""HTTP idempotency-key cache for mutating clinical endpoints.

Clinicians (and EHR integrations) routinely retry failed POST/PUT calls.
Without idempotency that means duplicate validation entries, duplicate
EHR pushes, duplicate audit ledger rows. The pattern is the same one used
by Stripe / GitHub: the caller supplies an ``Idempotency-Key`` HTTP
header on the first request and replays it on every retry; the server
returns the cached response for that key.

The cache is intentionally in-process and TTL-bounded — clinical
sessions are short-lived (minutes), so 1-hour TTL by default covers any
real-world retry storm without growing unbounded. Persistence to Postgres
is a future enhancement; until then, a process restart loses the cache
and idempotency degrades to "best effort".

Thread-safe via :class:`threading.RLock`. Never raises.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock
from typing import Any, Final

_DEFAULT_TTL_SECONDS: Final[float] = 3600.0
# Reject keys outside this range to avoid log spam / abuse — Stripe's
# limit is 255; we use a tighter window because we never need long
# correlation IDs in the clinical surface.
_MIN_KEY_LEN: Final[int] = 8
_MAX_KEY_LEN: Final[int] = 128


@dataclass
class _CacheEntry:
    response: dict[str, Any]
    expires_at: float


class IdempotencyCache:
    """In-process TTL cache keyed by (route, idempotency_key) tuples."""

    def __init__(self, *, ttl_seconds: float = _DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple[str, str], _CacheEntry] = {}
        self._lock = RLock()

    @staticmethod
    def is_valid_key(key: str | None) -> bool:
        """``True`` when ``key`` is well-formed enough to be cacheable."""
        if not isinstance(key, str):
            return False
        return _MIN_KEY_LEN <= len(key) <= _MAX_KEY_LEN

    def get(self, route: str, key: str) -> dict[str, Any] | None:
        if not self.is_valid_key(key):
            return None
        with self._lock:
            entry = self._store.get((route, key))
            if entry is None:
                return None
            if entry.expires_at < time.monotonic():
                self._store.pop((route, key), None)
                return None
            return entry.response

    def put(self, route: str, key: str, response: dict[str, Any]) -> None:
        if not self.is_valid_key(key):
            return
        with self._lock:
            self._store[(route, key)] = _CacheEntry(
                response=response,
                expires_at=time.monotonic() + self._ttl,
            )

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
