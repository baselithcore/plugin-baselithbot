from __future__ import annotations

import hashlib
import pickle
import time
from collections import OrderedDict
from threading import Lock
from typing import Generic, MutableMapping, Optional, Tuple, TypeVar

try:  # pragma: no cover - dipendenza opzionale
    from redis import Redis
except Exception:  # pragma: no cover - redis non disponibile
    Redis = None  # type: ignore[arg-type]

K = TypeVar("K")
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """
    Semplice cache in memoria con TTL e politica LRU.
    Pensata per ridurre il carico su reranker e LLM senza introdurre dipendenze esterne.
    """

    def __init__(self, maxsize: int = 256, ttl: float = 300.0) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize deve essere positivo")
        if ttl <= 0:
            raise ValueError("ttl deve essere positivo")
        self._maxsize = maxsize
        self._ttl = ttl
        self._store: MutableMapping[K, Tuple[V, float]] = OrderedDict()
        self._lock = Lock()

    def _purge_expired(self) -> None:
        now = time.time()
        while self._store:
            # OrderedDict.items() returns items in insertion order.
            # Since TTL is constant and we always append on set/get,
            # the oldest expiry is always at the beginning.
            key = next(iter(self._store))
            _, expiry = self._store[key]
            if expiry <= now:
                self._store.popitem(last=False)
            else:
                break

    def get(self, key: K) -> Optional[V]:
        with self._lock:
            self._purge_expired()
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if expiry <= time.time():
                self._store.pop(key, None)
                return None
            # Aggiorna l'ordine LRU
            self._store.pop(key)
            self._store[key] = (value, expiry)
            return value

    def set(self, key: K, value: V) -> None:
        with self._lock:
            self._purge_expired()
            if key in self._store:
                self._store.pop(key)
            elif len(self._store) >= self._maxsize:
                self._store.popitem(last=False)
            expiry = time.time() + self._ttl
            self._store[key] = (value, expiry)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class RedisTTLCache(Generic[K, V]):
    """
    Cache TTL basata su Redis. Ogni entry viene serializzata (pickle) e memorizzata con TTL.
    Richiede il pacchetto ``redis`` e un client già configurato.
    """

    def __init__(self, client: "Redis", *, prefix: str, default_ttl: float) -> None:
        if Redis is None:
            raise RuntimeError(
                "Redis non è disponibile: installa il pacchetto 'redis'."
            )
        self._client = client
        self._prefix = prefix.rstrip(":")
        self._ttl = max(1, int(default_ttl))

    def _serialize_key(self, key: K) -> str:
        payload = pickle.dumps(key, protocol=4)
        digest = hashlib.sha1(payload).hexdigest()
        return f"{self._prefix}:{digest}"

    def get(self, key: K) -> Optional[V]:
        redis_key = self._serialize_key(key)
        data = self._client.get(redis_key)
        if data is None:
            return None
        try:
            return pickle.loads(data)
        except Exception:
            self._client.delete(redis_key)
            return None

    def set(self, key: K, value: V) -> None:
        redis_key = self._serialize_key(key)
        payload = pickle.dumps(value, protocol=4)
        self._client.setex(redis_key, self._ttl, payload)

    def clear(self) -> None:
        pattern = f"{self._prefix}:*"
        cursor = 0
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=500)
            if keys:
                self._client.delete(*keys)
            if cursor == 0:
                break


def create_redis_client(url: str) -> "Redis":
    if Redis is None:
        raise RuntimeError(
            "Cache backend 'redis' richiesto ma il pacchetto redis non è installato."
        )
    return Redis.from_url(url)
