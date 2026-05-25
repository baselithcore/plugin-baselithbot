"""Approval registry tests — open/resolve/timeout semantics."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from plugins.red_agent.approvals import ApprovalRegistry


@pytest.mark.asyncio
async def test_open_then_resolve_approved() -> None:
    reg = ApprovalRegistry()
    scan_id = uuid4()
    fut = await reg.open(scan_id, reason="active scan", requested_by="op")

    ok = await reg.resolve(scan_id, approved=True, actor="alice")
    assert ok is True
    assert await fut is True


@pytest.mark.asyncio
async def test_resolve_unknown_returns_false() -> None:
    reg = ApprovalRegistry()
    ok = await reg.resolve(uuid4(), approved=True, actor="bob")
    assert ok is False


@pytest.mark.asyncio
async def test_resolve_idempotent() -> None:
    reg = ApprovalRegistry()
    scan_id = uuid4()
    await reg.open(scan_id, reason="x", requested_by="op")
    assert await reg.resolve(scan_id, approved=True, actor="a") is True
    # second resolve has no pending future left
    assert await reg.resolve(scan_id, approved=False, actor="a") is False


@pytest.mark.asyncio
async def test_list_pending() -> None:
    reg = ApprovalRegistry()
    a, b = uuid4(), uuid4()
    await reg.open(a, reason="ra", requested_by="alice")
    await reg.open(b, reason="rb", requested_by="bob")
    pending = await reg.list_pending()
    ids = {p["scan_id"] for p in pending}
    assert {str(a), str(b)} <= ids


@pytest.mark.asyncio
async def test_timeout_via_wait_for() -> None:
    reg = ApprovalRegistry()
    scan_id = uuid4()
    fut = await reg.open(scan_id, reason="x", requested_by="op")
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(fut, timeout=0.05)


class _FakeStore:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.rows = rows
        self.inserts: list[tuple] = []
        self.resolutions: list[tuple] = []
        self.timeouts: list[str] = []

    async def insert_open(self, scan_id, reason, requested_by) -> None:
        self.inserts.append((str(scan_id), reason, requested_by))

    async def mark_resolved(self, scan_id, *, approved, actor) -> None:
        self.resolutions.append((str(scan_id), approved, actor))

    async def mark_timeout(self, scan_id) -> None:
        self.timeouts.append(str(scan_id))

    async def list_open(self):
        return self.rows


@pytest.mark.asyncio
async def test_rehydrate_recreates_futures() -> None:
    a = uuid4()
    b = uuid4()
    store = _FakeStore(
        rows=[
            {"scan_id": str(a), "reason": "ra", "requested_by": "alice"},
            {"scan_id": str(b), "reason": "rb", "requested_by": "bob"},
        ]
    )
    reg = ApprovalRegistry(store=store)
    n = await reg.rehydrate()
    assert n == 2
    pending = await reg.list_pending()
    ids = {p["scan_id"] for p in pending}
    assert {str(a), str(b)} <= ids


@pytest.mark.asyncio
async def test_resolve_writes_through_to_store() -> None:
    scan_id = uuid4()
    store = _FakeStore(rows=[])
    reg = ApprovalRegistry(store=store)
    await reg.open(scan_id, reason="x", requested_by="op")
    await reg.resolve(scan_id, approved=True, actor="alice")
    assert store.inserts == [(str(scan_id), "x", "op")]
    assert store.resolutions == [(str(scan_id), True, "alice")]


@pytest.mark.asyncio
async def test_mark_timeout_writes_through() -> None:
    scan_id = uuid4()
    store = _FakeStore(rows=[])
    reg = ApprovalRegistry(store=store)
    await reg.mark_timeout(scan_id)
    assert store.timeouts == [str(scan_id)]
