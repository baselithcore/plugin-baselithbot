"""Retained plugin-lifecycle timeline for the control plane.

The SSE bridge (:mod:`bridge`) fans live events to *connected* clients only —
nothing is kept, so a page reload starts from an empty feed. This buffer
subscribes once to the in-process :class:`EventBus` and retains the recent
lifecycle history (activations, failures, reloads, governed actions) in a
bounded ring, so the dashboard can render a "recent activity" timeline that
survives reloads.

It reuses the core EventBus (already the control plane's event backbone) for the
subscription; only the filtered, wire-shaped retention is plugin-local. Handlers
receive the payload dict (not the ``Event``), so — like the bridge — each topic
is bound through its own closure to recover the event name.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from core.events.bus import get_event_bus
from core.observability.logging import get_logger

from ..config import get_runtime_config
from .bridge import CONTROL_ACTION

logger = get_logger(__name__)

# Lifecycle topics retained for the timeline (governed actions + core deltas).
_TOPICS: tuple[str, ...] = (
    "plugin.activated",
    "plugin.deactivated",
    "plugin.reloaded",
    "plugin.failed",
    CONTROL_ACTION,
)


class LifecycleBuffer:
    """Bounded, newest-first ring of retained lifecycle events."""

    def __init__(self, capacity: int) -> None:
        self._ring: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._unsubscribes: list[Any] = []

    def attach(self, bus: Any) -> None:
        """Subscribe to every lifecycle topic (idempotent)."""
        if self._unsubscribes:
            return
        for topic in _TOPICS:
            try:
                self._unsubscribes.append(
                    bus.subscribe(topic, self._make_handler(topic))
                )
            except Exception as exc:  # noqa: BLE001 — never block boot on telemetry
                logger.debug("lifecycle subscribe to '%s' failed: %s", topic, exc)

    def _make_handler(self, name: str):
        async def _handler(data: dict[str, Any]) -> None:  # bus passes the payload
            self.record(name, data or {})

        return _handler

    def record(self, event_type: str, data: dict[str, Any]) -> None:
        """Append one normalized lifecycle record (timestamped now)."""
        entry = {
            "type": event_type,
            "timestamp": round(time.time(), 3),
            "plugin": data.get("plugin"),
            "state": data.get("state"),
            "ok": data.get("ok"),
        }
        with self._lock:
            self._ring.append(entry)

    def tail(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return up to ``limit`` most-recent events, newest first."""
        with self._lock:
            items = list(self._ring)
        if limit > 0:
            items = items[-limit:]
        return list(reversed(items))


_BUFFER: LifecycleBuffer | None = None
_BUFFER_LOCK = threading.Lock()


def get_lifecycle_buffer() -> LifecycleBuffer:
    """Return the singleton buffer, subscribed to the bus on first construction."""
    global _BUFFER
    if _BUFFER is None:
        with _BUFFER_LOCK:
            if _BUFFER is None:
                buf = LifecycleBuffer(get_runtime_config().lifecycle_capacity)
                buf.attach(get_event_bus())
                _BUFFER = buf
    return _BUFFER


__all__ = ["LifecycleBuffer", "get_lifecycle_buffer"]
