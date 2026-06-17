"""Per-contact auto-reply rate budget — an anti-runaway guard.

A simple in-process sliding-window counter that caps how many replies the twin
may auto-send to a single contact per minute. Prevents reply storms and feedback
loops (two twins answering each other) without any external dependency. The
clock is injectable so the limiter stays deterministic under test.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

_WINDOW_SECONDS = 60.0


class RateBudget:
    """Sliding-window per-contact auto-send limiter."""

    def __init__(
        self, max_per_minute: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._max = max_per_minute
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, contact_id: str) -> bool:
        """Return whether an auto-send is within budget, consuming one slot.

        When ``max_per_minute`` is 0 the limiter is disabled and always allows.
        """
        if self._max <= 0:
            return True
        now = self._clock()
        window = self._hits[contact_id]
        cutoff = now - _WINDOW_SECONDS
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self._max:
            return False
        window.append(now)
        return True


__all__ = ["RateBudget"]
