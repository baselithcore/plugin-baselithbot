"""Sliding-window rate limiter.

Backend automatico in base a ``config.CACHE_BACKEND``:

- ``redis`` — sliding window via ZSET (``ZRANGEBYSCORE``/``ZADD``).
  Distribuito, condiviso fra worker. Richiede ``[auth]`` extra (redis dep).
- ``memory`` (default) — sliding window in-process via ``deque``.
  Single-instance only; due worker uvicorn vedono buckets separati.

Adattato da ``agent-jira/app/security.py:RateLimiter``. Estratto in
modulo dedicato: il file security.py originale mescolava JWT/auth +
rate-limit + headers; qui responsabilità separate.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from llm_wiki import config

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Sollevato quando il limite è superato. Il chiamante (middleware
    o dependency) lo traduce in HTTPException 429."""


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._redis = None
        self._redis_checked = False

    def _get_redis(self):  # noqa: ANN202 — redis client lazy
        if not self._redis_checked:
            self._redis_checked = True
            if config.CACHE_BACKEND == "redis" and config.CACHE_REDIS_URL:
                try:
                    import redis  # type: ignore

                    self._redis = redis.Redis.from_url(
                        config.CACHE_REDIS_URL,
                        decode_responses=True,
                        socket_timeout=2.0,
                    )
                    # Probe: connection-fail diventa fallback locale
                    # invece di 500 sulla prima request.
                    self._redis.ping()
                except Exception as exc:
                    logger.warning(
                        "[ratelimit] redis backend unavailable, fallback in-process: %s",
                        exc,
                    )
                    self._redis = None
        return self._redis

    def check(self, identifier: str, limit: int | None, window_seconds: int) -> None:
        """Solleva :class:`RateLimitExceeded` se ``limit`` superato.

        ``limit=None`` o ``<=0`` disabilita il check (no-op).
        """
        if not limit or limit <= 0:
            return

        redis = self._get_redis()
        if redis is not None:
            self._check_redis(redis, identifier, limit, window_seconds)
        else:
            self._check_local(identifier, limit, window_seconds)

    def _check_local(self, identifier: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        window_start = now - window_seconds
        bucket = self._buckets[identifier]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= limit:
            raise RateLimitExceeded(identifier)
        bucket.append(now)

    def _check_redis(self, redis, identifier: str, limit: int, window_seconds: int) -> None:
        key = f"ratelimit:{identifier}"
        now = time.time()
        window_start = now - window_seconds

        pipe = redis.pipeline(transaction=True)
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 1)
        results = pipe.execute()

        current_count = int(results[1])
        if current_count >= limit:
            # Ho già aggiunto il mio score — rimuovo per non far drift
            # del bucket quando la request viene rifiutata.
            try:
                redis.zrem(key, str(now))
            except Exception:
                pass
            raise RateLimitExceeded(identifier)


# Singleton modulo: il pattern `from ... import rate_limiter` evita
# doppio bucket fra import diversi.
rate_limiter = RateLimiter()


__all__ = ["RateLimiter", "RateLimitExceeded", "rate_limiter"]
