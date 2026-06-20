"""Unit tests for the retained-telemetry layer (request-volume + lifecycle).

These cover the two pieces that survive a page reload: the server-side
request-rate ring (:class:`VolumeSampler`) and the bus-fed lifecycle timeline
(:class:`LifecycleBuffer`). Both are pure in-process primitives, so the tests
exercise them directly without standing up the FastAPI app.
"""

from __future__ import annotations

import pytest

from core.events.bus import get_event_bus, reset_event_bus
from plugins.baselithcontrol.service.lifecycle import LifecycleBuffer
from plugins.baselithcontrol.service.plugin_meter import get_plugin_meter
from plugins.baselithcontrol.service.volume import VolumeSampler


@pytest.fixture
def bus():
    """A clean global event bus per test."""
    reset_event_bus()
    yield get_event_bus()
    reset_event_bus()


async def test_lifecycle_buffer_captures_and_orders_events(bus):
    buf = LifecycleBuffer(capacity=10)
    buf.attach(bus)

    await bus.emit("plugin.failed", {"plugin": "demo", "state": "failed"}, wait=True)
    await bus.emit("plugin.activated", {"plugin": "demo", "state": "active"}, wait=True)

    rows = buf.tail(10)
    # Newest first.
    assert [r["type"] for r in rows] == ["plugin.activated", "plugin.failed"]
    assert rows[0]["plugin"] == "demo"
    assert rows[0]["state"] == "active"


async def test_lifecycle_buffer_respects_capacity(bus):
    buf = LifecycleBuffer(capacity=2)
    buf.attach(bus)

    for i in range(5):
        await bus.emit("plugin.reloaded", {"plugin": f"p{i}"}, wait=True)

    rows = buf.tail(10)
    assert len(rows) == 2
    assert rows[0]["plugin"] == "p4"  # most recent retained


async def test_lifecycle_attach_is_idempotent(bus):
    buf = LifecycleBuffer(capacity=10)
    buf.attach(bus)
    buf.attach(bus)  # a second attach must not double-subscribe

    await bus.emit("plugin.failed", {"plugin": "demo"}, wait=True)
    assert len(buf.tail(10)) == 1


def test_volume_sampler_derives_rate_between_samples():
    meter = get_plugin_meter()
    sampler = VolumeSampler(capacity=10, interval_seconds=1.0)

    sampler._take_sample(now=100.0)  # baseline only — no point yet
    assert sampler.history() == []

    for _ in range(10):
        meter.end("voltest", 1.0, 200)  # +10 requests over the window

    sampler._take_sample(now=102.0)  # dt = 2s → 10 / 2 = 5 req/s
    hist = sampler.history()
    assert len(hist) == 1
    assert hist[0]["timestamp"] == 102.0
    assert hist[0]["requests_per_sec"] == pytest.approx(5.0)


def test_volume_sampler_is_capacity_bounded():
    sampler = VolumeSampler(capacity=3, interval_seconds=1.0)
    for i in range(6):
        sampler._take_sample(now=float(i))
    assert len(sampler.history()) <= 3
