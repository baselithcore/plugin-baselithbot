"""Status adapter: project a plugin's lifecycle + health into a normalized envelope.

This is the server-side half of the "status adapter" pattern every modern
dashboard converges on: a uniform :class:`PluginStatus` shape the frontend can
render without knowing anything plugin-specific. Liveness/readiness come from
the registry's own ``health_check``; ``last_seen`` is tracked here so the UI can
show "last healthy 12s ago" the way Dashy/Homepage do.
"""

from __future__ import annotations

import time
from typing import Any

from ..api_models import PluginState, PluginStatus, StatusKind
from .telemetry import plugin_metric_views

# name → epoch seconds of the last healthy observation (process-local).
_LAST_SEEN: dict[str, float] = {}


def _kind(state: PluginState, healthy: bool | None) -> StatusKind:
    """Collapse (lifecycle state, health flag) into the status vocabulary."""
    if state == PluginState.failed:
        return StatusKind.down
    if state == PluginState.disabled:
        return StatusKind.disabled
    if state == PluginState.active:
        if healthy is True:
            return StatusKind.healthy
        if healthy is False:
            return StatusKind.degraded
        return StatusKind.healthy  # active, health not reported → assume ready
    return StatusKind.unknown


class StatusProber:
    """Produce normalized :class:`PluginStatus` envelopes from the registry."""

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    def probe(self, plugin: str) -> PluginStatus:
        """Probe a single plugin; measures registry round-trip as latency."""
        start = time.perf_counter()
        hc = self._safe_health(plugin)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        entry = hc.get("plugins", {}).get(plugin, {})
        status = entry.get("status")
        healthy = (status == "healthy") if status else None
        state = self._state(plugin, entry)
        kind = _kind(state, healthy)

        now = time.time()
        if kind == StatusKind.healthy:
            _LAST_SEEN[plugin] = now

        return PluginStatus(
            plugin=plugin,
            kind=kind,
            state=state,
            latency_ms=latency_ms,
            code=200 if kind == StatusKind.healthy else None,
            last_seen=_LAST_SEEN.get(plugin),
            metrics=plugin_metric_views(plugin),
        )

    # -- helpers -------------------------------------------------------------
    def _state(self, plugin: str, entry: dict) -> PluginState:
        if entry.get("status") == "unhealthy":
            return PluginState.failed
        if plugin not in self._registry:
            return PluginState.unknown
        return (
            PluginState.active
            if entry.get("initialized", True)
            else PluginState.discovered
        )

    def _safe_health(self, plugin: str) -> dict:
        try:
            return self._registry.health_check(plugin)
        except Exception:  # noqa: BLE001 — never let a probe raise into the route
            return {"plugins": {}}


__all__ = ["StatusProber"]
