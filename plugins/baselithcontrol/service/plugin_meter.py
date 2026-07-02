"""Per-plugin request telemetry — the honest per-plugin signal.

Because every plugin shares the one host process, CPU/RAM cannot be attributed
to a single plugin (see :mod:`resources`). What *can* be measured per plugin is
its HTTP surface: how much traffic each plugin's router serves, how fast, and
how often it errors. This module meters exactly that.

A pure-ASGI middleware times every request, attributes it to a plugin via the
framework registry's own longest-prefix matcher (``match_plugin_route`` — the
same routing core already trusts, so no prefix logic is duplicated), and folds
the result into an in-memory, memory-bounded per-plugin stat. Request *rate* is
intentionally not computed here: the dashboard derives it from the monotonic
``requests`` counter across its polls, which stays correct under any load.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field

from starlette.routing import Mount
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .llm_cost import current_plugin

_RING = 256  # latency samples retained per plugin for percentile estimation


@dataclass
class _Stat:
    requests: int = 0
    errors: int = 0
    in_flight: int = 0
    last_ms: float = 0.0
    ewma_ms: float = 0.0  # smoothed average latency
    _ring: deque[float] = field(default_factory=lambda: deque(maxlen=_RING))


class PluginMeter:
    """Process-wide, thread-safe collector of per-plugin request stats."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stats: dict[str, _Stat] = {}

    def begin(self, plugin: str) -> None:
        with self._lock:
            self._stats.setdefault(plugin, _Stat()).in_flight += 1

    def end(self, plugin: str, duration_ms: float, status: int) -> None:
        with self._lock:
            st = self._stats.setdefault(plugin, _Stat())
            if st.in_flight > 0:
                st.in_flight -= 1
            st.requests += 1
            if status >= 500:
                st.errors += 1
            st.last_ms = duration_ms
            # EWMA with alpha=0.2 keeps a stable, recent-weighted average.
            st.ewma_ms = (
                duration_ms
                if st.requests == 1
                else st.ewma_ms * 0.8 + duration_ms * 0.2
            )
            st._ring.append(duration_ms)

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        """Return a per-plugin view: counts, in-flight, error rate, avg/p95/last."""
        out: dict[str, dict[str, float | int]] = {}
        with self._lock:
            for name, st in self._stats.items():
                samples = sorted(st._ring)
                p95 = (
                    samples[min(len(samples) - 1, int(len(samples) * 0.95))]
                    if samples
                    else 0.0
                )
                out[name] = {
                    "requests": st.requests,
                    "errors": st.errors,
                    "in_flight": st.in_flight,
                    "error_rate": round(st.errors / st.requests, 4)
                    if st.requests
                    else 0.0,
                    "avg_ms": round(st.ewma_ms, 1),
                    "p95_ms": round(p95, 1),
                    "last_ms": round(st.last_ms, 1),
                }
        return out


_METER: PluginMeter | None = None
_METER_LOCK = threading.Lock()


def get_plugin_meter() -> PluginMeter:
    """Return the process-wide singleton meter (built on first use)."""
    global _METER
    if _METER is None:
        with _METER_LOCK:
            if _METER is None:
                _METER = PluginMeter()
    return _METER


def _mounted_plugins(app: object) -> dict[str, str]:
    """Map mounted sub-app path prefixes → plugin name (cached on ``app.state``).

    Plugins integrated via the sub-app-mount pattern (``app.mount("/name",
    sub_app, name="name")`` — e.g. baselithbrain) have no router
    prefix in the registry, so ``match_plugin_route`` can't see them. We recover
    them from the app's own ``Mount`` routes: their mount name is the plugin name.
    Built once (all mounts exist before requests flow) and cached.
    """
    state = getattr(app, "state", None)
    cached = getattr(state, "_blc_mount_map", None)
    if cached is not None:
        return cached  # type: ignore[no-any-return]
    mapping: dict[str, str] = {}
    try:
        for route in getattr(app, "routes", []):
            if isinstance(route, Mount) and route.name and route.path:
                mapping[route.path.rstrip("/")] = route.name
    except Exception:  # noqa: BLE001 — never let metering break a request
        mapping = {}
    try:
        if state is not None:
            state._blc_mount_map = mapping
    except Exception:  # noqa: BLE001 — caching is best-effort
        pass
    return mapping


def _resolve_plugin(scope: Scope) -> str | None:
    """Attribute a request path to a plugin: router prefix first, then sub-app mount."""
    app = scope.get("app")
    path = scope.get("path", "") or ""
    registry = getattr(getattr(app, "state", None), "plugin_registry", None)
    if registry is not None:
        try:
            matched = registry.match_plugin_route(path)
            if matched:
                return matched
        except Exception:  # noqa: BLE001 — never let metering break a request
            pass
    # Fallback: longest matching mounted sub-app prefix (e.g. /baselithbrain/...).
    best: str | None = None
    best_len = -1
    for prefix, name in _mounted_plugins(app).items():
        if (path == prefix or path.startswith(f"{prefix}/")) and len(prefix) > best_len:
            best, best_len = name, len(prefix)
    return best


class PluginMeterMiddleware:
    """Pure-ASGI middleware that records per-plugin request timing and errors."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._meter = get_plugin_meter()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        plugin = _resolve_plugin(scope)
        if plugin is None:
            await self.app(scope, receive, send)
            return

        self._meter.begin(plugin)
        started = time.perf_counter()
        status_code = 500  # default to error if the response never starts
        # Bind the active plugin for this request so any LLM call it makes is
        # attributed to it by the cost ledger (same task → contextvar visible).
        cv_token = current_plugin.set(plugin)

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 200))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            current_plugin.reset(cv_token)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            self._meter.end(plugin, elapsed_ms, status_code)


__all__ = ["PluginMeter", "PluginMeterMiddleware", "get_plugin_meter"]
