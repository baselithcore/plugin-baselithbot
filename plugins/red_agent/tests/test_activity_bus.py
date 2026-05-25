"""Unit tests for the cross-scan ActivityEventBus + audit broadcast hook."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from core.di.container import ServiceRegistry
from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.events import ActivityEventBus


@pytest.mark.asyncio
async def test_publish_to_subscribers() -> None:
    bus = ActivityEventBus()
    queue = await bus.subscribe()
    await bus.publish({"event": "scan.critic_veto", "actor": "red_agent"})
    raw = await queue.get()
    decoded = json.loads(raw)
    assert decoded["event"] == "scan.critic_veto"


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery() -> None:
    bus = ActivityEventBus()
    queue = await bus.subscribe()
    await bus.unsubscribe(queue)
    await bus.publish({"event": "scan.cancelled"})
    assert queue.empty()


@pytest.mark.asyncio
async def test_audit_logger_publishes_to_bus_when_registered() -> None:
    bus = ActivityEventBus()
    ServiceRegistry.register(ActivityEventBus, bus)
    try:
        queue = await bus.subscribe()
        logger = AuditLogger(dsn="")  # no DSN → exercises the no-DSN broadcast path
        scan_id = uuid4()
        await logger.record(
            scan_id=scan_id,
            actor="op",
            event="scan.roe_violation",
            payload={"code": "EXCLUDED_BY_ENGAGEMENT"},
        )
        raw = await queue.get()
        decoded = json.loads(raw)
        assert decoded["event"] == "scan.roe_violation"
        assert decoded["actor"] == "op"
        assert decoded["scan_id"] == str(scan_id)
        assert decoded["payload"]["code"] == "EXCLUDED_BY_ENGAGEMENT"
        assert "created_at" in decoded
    finally:
        ServiceRegistry.clear()


@pytest.mark.asyncio
async def test_audit_logger_no_bus_is_silent() -> None:
    logger = AuditLogger(dsn="")
    # Should not raise even without ActivityEventBus registered.
    await logger.record(
        scan_id=None,
        actor="x",
        event="scan.submitted",
        payload={},
    )


def test_ws_prefix_matcher_accepts_matching_event() -> None:
    from plugins.red_agent.routers.ws import _matches_prefix

    frame = json.dumps({"event": "scan.critic_veto", "actor": "red_agent"})
    assert _matches_prefix(frame, ("scan.critic_",)) is True


def test_ws_prefix_matcher_rejects_non_matching_event() -> None:
    from plugins.red_agent.routers.ws import _matches_prefix

    frame = json.dumps({"event": "scan.submitted", "actor": "op"})
    assert _matches_prefix(frame, ("scan.critic_", "scan.roe_")) is False


def test_ws_prefix_matcher_handles_malformed_frame() -> None:
    from plugins.red_agent.routers.ws import _matches_prefix

    assert _matches_prefix("not json", ("scan.",)) is False


def test_ws_engagement_matcher_strict() -> None:
    from plugins.red_agent.routers.ws import _matches_engagement

    frame = json.dumps({"event": "scan.critic_veto", "engagement_id": "abc"})
    assert _matches_engagement(frame, "abc") is True
    assert _matches_engagement(frame, "xyz") is False
    assert _matches_engagement(json.dumps({"engagement_id": None}), "abc") is False


def test_scan_engagement_index_evicts_oldest_when_full() -> None:
    from plugins.red_agent.events import ScanEngagementIndex
    from uuid import uuid4

    idx = ScanEngagementIndex(capacity=2)
    a, b, c = uuid4(), uuid4(), uuid4()
    eng = uuid4()
    idx.remember(a, eng)
    idx.remember(b, eng)
    idx.remember(c, eng)
    assert idx.lookup(a) is None  # evicted
    assert idx.lookup(b) == str(eng)
    assert idx.lookup(c) == str(eng)


@pytest.mark.asyncio
async def test_audit_broadcast_enriches_engagement_id_when_indexed() -> None:
    from plugins.red_agent.events import ScanEngagementIndex
    from uuid import uuid4

    bus = ActivityEventBus()
    index = ScanEngagementIndex()
    scan_id = uuid4()
    eng_id = uuid4()
    index.remember(scan_id, eng_id)

    ServiceRegistry.register(ActivityEventBus, bus)
    ServiceRegistry.register(ScanEngagementIndex, index)
    try:
        queue = await bus.subscribe()
        logger = AuditLogger(dsn="")
        await logger.record(
            scan_id=scan_id, actor="op", event="scan.critic_veto", payload={}
        )
        decoded = json.loads(await queue.get())
        assert decoded["engagement_id"] == str(eng_id)
    finally:
        ServiceRegistry.clear()
