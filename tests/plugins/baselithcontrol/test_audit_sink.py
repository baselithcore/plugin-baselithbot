"""Audit sink: capacity honoured regardless of construction order."""

from __future__ import annotations

from plugins.baselithcontrol.service.audit import InMemoryAuditSink


async def _fill(sink: InMemoryAuditSink, n: int) -> None:
    for i in range(n):
        await sink.record(actor="a", plugin="p", op=f"op{i}", ok=True, reason=None)


async def test_ring_bounds_and_tail_order() -> None:
    sink = InMemoryAuditSink(max_events=3)
    await _fill(sink, 5)
    ops = [e.operation for e in sink.tail(limit=10)]
    assert ops == ["op2", "op3", "op4"]


async def test_resize_preserves_newest() -> None:
    sink = InMemoryAuditSink(max_events=10)
    await _fill(sink, 6)
    sink.resize(2)
    assert sink.capacity == 2
    assert [e.operation for e in sink.tail(limit=10)] == ["op4", "op5"]
    sink.resize(5)  # growing keeps existing entries
    await _fill(sink, 1)
    assert len(sink.tail(limit=10)) == 3
