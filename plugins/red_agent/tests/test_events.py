"""Tests for the in-process scan event bus (publish/subscribe semantics)."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest

from plugins.red_agent.events import ScanEventBus


@pytest.mark.asyncio
async def test_publish_fanouts_to_subscribers() -> None:
    bus = ScanEventBus()
    scan_id = uuid4()
    q1 = await bus.subscribe(scan_id)
    q2 = await bus.subscribe(scan_id)

    await bus.publish(scan_id, {"type": "status", "status": "running"})
    await bus.publish(scan_id, {"type": "finding", "finding": {"id": "x"}})

    msg1a = json.loads(q1.get_nowait())
    msg1b = json.loads(q1.get_nowait())
    msg2a = json.loads(q2.get_nowait())
    msg2b = json.loads(q2.get_nowait())

    assert msg1a["status"] == "running"
    assert msg1b["type"] == "finding"
    assert msg2a == msg1a
    assert msg2b == msg1b


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery() -> None:
    bus = ScanEventBus()
    scan_id = uuid4()
    q = await bus.subscribe(scan_id)
    await bus.unsubscribe(scan_id, q)

    await bus.publish(scan_id, {"type": "status", "status": "completed"})

    with pytest.raises(asyncio.QueueEmpty):
        q.get_nowait()


@pytest.mark.asyncio
async def test_isolation_between_scans() -> None:
    bus = ScanEventBus()
    a = uuid4()
    b = uuid4()
    qa = await bus.subscribe(a)
    qb = await bus.subscribe(b)

    await bus.publish(a, {"type": "status", "status": "running"})

    msg = json.loads(qa.get_nowait())
    assert msg["status"] == "running"
    with pytest.raises(asyncio.QueueEmpty):
        qb.get_nowait()
