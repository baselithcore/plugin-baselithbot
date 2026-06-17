"""Bridge the in-process :class:`EventBus` to per-client SSE queues.

``EventBus`` handlers are invoked with the event **payload dict** (not the
``Event`` object), so the event name cannot be recovered inside a wildcard
handler. We therefore subscribe one closure per *explicit* control-plane topic
so each frame is reliably typed. The control service emits ``CONTROL_ACTION``
after every governed action, guaranteeing the dashboard's own mutations stream
live; well-known core lifecycle topics are forwarded too when the core emits
them.

Each SSE client gets its own bounded queue; the handler enqueues, the async
generator drains. Framing matches the repo's canonical SSE pattern
(``: connected`` opener, idle ``: ping`` heartbeat, unnamed ``data:`` frames).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from core.events.bus import get_event_bus
from core.observability.logging import get_logger

logger = get_logger(__name__)

# Topic emitted by ControlService after each governed lifecycle action.
CONTROL_ACTION = "baselithcontrol.action"

# Explicit topics the stream forwards (names bound via per-topic closures).
_TOPICS: tuple[str, ...] = (
    CONTROL_ACTION,
    "plugin.activated",
    "plugin.deactivated",
    "plugin.reloaded",
    "plugin.failed",
    "system.health",
)

_QUEUE_MAXSIZE = 256


def _make_handler(name: str, queue: "asyncio.Queue[dict]"):
    """Build an async handler that tags the payload with its topic name."""

    async def _handler(data: dict) -> None:  # EventBus passes the payload dict
        try:
            queue.put_nowait({"type": name, "data": data or {}})
        except asyncio.QueueFull:
            logger.warning("control SSE queue full; dropping '%s'", name)

    return _handler


async def control_sse(heartbeat_seconds: float = 20.0) -> AsyncIterator[str]:
    """Yield SSE frames for control-plane lifecycle/health events."""
    bus = get_event_bus()
    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
    unsubscribes = [
        bus.subscribe(topic, _make_handler(topic, queue)) for topic in _TOPICS
    ]

    yield ": connected\n\n"  # flush headers + fire EventSource.onopen immediately
    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), heartbeat_seconds)
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # idle keepalive so proxies keep the socket open
                continue
            yield f"data: {json.dumps(payload)}\n\n"
    except (asyncio.CancelledError, GeneratorExit):
        return
    finally:
        for off in unsubscribes:
            try:
                off()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass


async def emit_action(*, plugin: str, op: str, ok: bool, state: str) -> None:
    """Publish a governed-action event onto the bus (best-effort, non-blocking)."""
    try:
        await get_event_bus().emit(
            CONTROL_ACTION,
            {"plugin": plugin, "op": op, "ok": ok, "state": state},
            source="baselithcontrol",
            wait=False,
        )
    except Exception as exc:  # noqa: BLE001 — telemetry must never break an action
        logger.debug("control action emit failed: %s", exc)


__all__ = ["control_sse", "emit_action", "CONTROL_ACTION"]
