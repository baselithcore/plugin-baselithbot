"""WebSocket router for live scan event streaming."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.red_agent.events import ActivityEventBus, ScanEventBus

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["red-agent"])

_HEARTBEAT_SECONDS = 30.0
_PING_FRAME = json.dumps({"type": "ping"})


def _get_bus() -> ScanEventBus:
    bus = ServiceRegistry.get(ScanEventBus)
    if bus is None:
        raise RuntimeError("ScanEventBus not registered")
    return bus


async def _authenticate(token: str) -> bool:
    """Validate token via core.auth.

    When ``RED_AGENT_ALLOW_ANONYMOUS=true`` or no AuthManager is registered
    (typical in dev), the WebSocket connection is accepted unconditionally.
    """
    import os

    if os.getenv("RED_AGENT_ALLOW_ANONYMOUS", "").lower() in {"1", "true", "yes"}:
        return True

    try:
        from core.auth import AuthManager  # type: ignore[attr-defined]
    except ImportError:
        return True  # auth subsystem not bundled; permissive in dev

    try:
        manager = ServiceRegistry.get(AuthManager)
    except Exception:  # noqa: BLE001
        manager = None
    if manager is None:
        return True

    if not token:
        return False
    try:
        user = await manager.authenticate(f"Bearer {token}")
    except Exception:  # noqa: BLE001
        return False
    return bool(getattr(user, "is_authenticated", False))


@router.websocket("/scans/{scan_id}")
async def scan_stream(
    websocket: WebSocket,
    scan_id: UUID,
    bus: ScanEventBus = Depends(_get_bus),
) -> None:
    token = websocket.query_params.get("token", "")
    if not await _authenticate(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    queue = await bus.subscribe(scan_id)
    try:
        while True:
            try:
                frame = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                await websocket.send_text(_PING_FRAME)
                continue
            await websocket.send_text(frame)
    except WebSocketDisconnect:
        pass
    finally:
        await bus.unsubscribe(scan_id, queue)


def _get_activity_bus() -> ActivityEventBus:
    bus = ServiceRegistry.get(ActivityEventBus)
    if bus is None:
        raise RuntimeError("ActivityEventBus not registered")
    return bus


@router.websocket("/activity")
async def activity_stream(
    websocket: WebSocket,
    bus: ActivityEventBus = Depends(_get_activity_bus),
) -> None:
    """Live cockpit feed: every audit event is broadcast as a JSON frame.

    Frames mirror the ``/activity`` REST shape: ``{scan_id, actor,
    event, payload, created_at}``. Clients can pre-filter via
    ``?event_prefix=scan.critic_`` (repeatable) so the server drops
    non-matching frames before sending — saves bandwidth on busy feeds.
    """
    token = websocket.query_params.get("token", "")
    if not await _authenticate(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    raw_prefixes = websocket.query_params.getlist("event_prefix")
    prefixes = tuple(p for p in raw_prefixes if p)
    engagement_id = websocket.query_params.get("engagement_id") or None

    await websocket.accept()
    queue = await bus.subscribe()
    try:
        while True:
            try:
                frame = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                await websocket.send_text(_PING_FRAME)
                continue
            if prefixes and not _matches_prefix(frame, prefixes):
                continue
            if engagement_id is not None and not _matches_engagement(
                frame, engagement_id
            ):
                continue
            await websocket.send_text(frame)
    except WebSocketDisconnect:
        pass
    finally:
        await bus.unsubscribe(queue)


def _matches_engagement(frame: str, engagement_id: str) -> bool:
    """Frame's ``engagement_id`` field equals the requested scope."""
    try:
        parsed = json.loads(frame)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, dict):
        return False
    return parsed.get("engagement_id") == engagement_id


def _matches_prefix(frame: str, prefixes: tuple[str, ...]) -> bool:
    """Cheap prefix check on the JSON-encoded frame.

    Avoids parsing JSON twice (subscriber side is already paying once
    on the client). Looks for ``"event":"<prefix>`` substring — safe
    because the audit emitter always serializes ``event`` as a JSON
    string and never includes those tokens in payload values that could
    false-match.
    """
    try:
        parsed = json.loads(frame)
    except json.JSONDecodeError:
        return False
    event = parsed.get("event", "") if isinstance(parsed, dict) else ""
    return any(event.startswith(p) for p in prefixes)
