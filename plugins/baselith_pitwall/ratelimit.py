"""Opt-in per-tenant rate limiting for the pit-wall API (fixed-window counter).

Disabled by default (``per_minute <= 0``) so existing behaviour and tests are
unchanged; enable via the plugin config ``rate_limit_per_min`` to throttle the
abusable mutating endpoints (telemetry, radio). In-memory and per-process —
adequate for a single replica; a multi-replica deployment should front the API
with a shared gateway limiter.
"""

from __future__ import annotations

from datetime import datetime, timezone

_MAX_BUCKETS = 10_000


class RateLimiter:
    """Fixed-window (per-minute) request counter keyed by tenant."""

    def __init__(self, per_minute: int) -> None:
        self._per_minute = per_minute
        self._hits: dict[tuple[str, int], int] = {}

    @property
    def enabled(self) -> bool:
        """Whether limiting is active."""
        return self._per_minute > 0

    def allow(self, tenant: str) -> bool:
        """Record a hit for ``tenant``; return False once the window is exceeded."""
        if self._per_minute <= 0:
            return True
        minute = int(datetime.now(timezone.utc).timestamp() // 60)
        if len(self._hits) > _MAX_BUCKETS:
            self._hits = {k: v for k, v in self._hits.items() if k[1] >= minute}
        key = (tenant, minute)
        count = self._hits.get(key, 0) + 1
        self._hits[key] = count
        return count <= self._per_minute


__all__ = ["RateLimiter"]
