"""Retained request-volume time-series for the control plane.

The per-plugin meter (:mod:`plugin_meter`) keeps only monotonic counters; the
dashboard derives an instantaneous rate from deltas between its own polls, which
is lost on every page reload. This sampler closes that gap: a single background
task periodically reads the meter's total request count and folds it into a
bounded ring of ``(timestamp, requests_per_sec)`` points, giving the UI a
retained throughput trend that spans the whole window and survives reloads.

The task is lazily started from a request handler (where a running loop exists),
then self-sustains independent of any connected client. Everything is
best-effort: a sampling failure is swallowed so telemetry never affects serving.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque

from core.observability.logging import get_logger

from ..config import ControlConfig
from .plugin_meter import get_plugin_meter

logger = get_logger(__name__)


class VolumeSampler:
    """Bounded ring of aggregate request-rate samples, fed by a loop task."""

    def __init__(self, *, capacity: int, interval_seconds: float) -> None:
        self._interval = interval_seconds
        self._ring: deque[tuple[float, float]] = deque(maxlen=capacity)
        self._prev: tuple[float, int] | None = None  # (timestamp, total_requests)
        self._lock = threading.Lock()
        self._task: asyncio.Task[None] | None = None

    def ensure_started(self) -> None:
        """Start the background sampler once, if an event loop is running."""
        if self._task is not None and not self._task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # no loop (e.g. sync construction) — caller retries
            return
        self._task = loop.create_task(self._run())

    async def _run(self) -> None:
        self._take_sample()  # prime the baseline so the next tick yields a rate
        while True:
            try:
                await asyncio.sleep(self._interval)
                self._take_sample()
            except asyncio.CancelledError:
                return
            except Exception as exc:  # noqa: BLE001 — telemetry must never crash
                logger.debug("volume sample failed: %s", exc)

    def _take_sample(self, now: float | None = None) -> None:
        """Record one rate point from the meter's current total (rate vs. prev)."""
        ts = time.time() if now is None else now
        snap = get_plugin_meter().snapshot()
        total = sum(int(stat["requests"]) for stat in snap.values())
        with self._lock:
            if self._prev is not None:
                prev_ts, prev_total = self._prev
                dt = ts - prev_ts
                if dt > 0:
                    rps = max(0.0, (total - prev_total) / dt)
                    self._ring.append((round(ts, 3), round(rps, 3)))
            self._prev = (ts, total)

    def history(self) -> list[dict[str, float]]:
        """Return the retained series oldest→newest as wire-ready dicts."""
        with self._lock:
            return [{"timestamp": t, "requests_per_sec": v} for t, v in self._ring]


_SAMPLER: VolumeSampler | None = None
_SAMPLER_LOCK = threading.Lock()


def get_volume_sampler() -> VolumeSampler:
    """Return the process-wide singleton sampler (built on first use)."""
    global _SAMPLER
    if _SAMPLER is None:
        with _SAMPLER_LOCK:
            if _SAMPLER is None:
                cfg = ControlConfig()
                _SAMPLER = VolumeSampler(
                    capacity=cfg.volume_capacity,
                    interval_seconds=cfg.volume_interval_seconds,
                )
    return _SAMPLER


__all__ = ["VolumeSampler", "get_volume_sampler"]
