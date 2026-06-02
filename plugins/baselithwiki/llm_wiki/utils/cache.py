"""Cache TTL in-process leggera (thread-safe). Sufficiente per deploy locale."""

from __future__ import annotations

import threading
import time
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """Cache FIFO con scadenza TTL e dimensione massima."""

    def __init__(self, maxsize: int = 1024, ttl: float = 3600.0) -> None:
        self._maxsize = max(1, maxsize)
        self._ttl = max(0.1, ttl)
        self._data: dict[K, tuple[V, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: K) -> V | None:
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            value, expiry = entry
            if expiry < time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: K, value: V, ttl: float | None = None) -> None:
        with self._lock:
            if len(self._data) >= self._maxsize and key not in self._data:
                # FIFO eviction: rimuovi l'entry più vecchia
                oldest = min(self._data.items(), key=lambda kv: kv[1][1])
                self._data.pop(oldest[0], None)
            expiry = time.time() + (ttl if ttl is not None else self._ttl)
            self._data[key] = (value, expiry)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
