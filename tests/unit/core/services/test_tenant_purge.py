"""Tenant GDPR purge: deletes every tenant-scoped table, FK-safe via a fixpoint
retry (a parent whose delete fails while a child still references it is retried
after the child is purged). Discovery + deletes are mocked — no live DB."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager

import pytest

import core.services.tenant.purge as purge


class _FakeCursor:
    """'parent' delete fails until 'child' (which references it) is purged."""

    def __init__(self, state: dict):
        self._state = state
        self.rowcount = 0

    async def execute(self, sql: str, params=None):
        if "information_schema" in sql:
            self._state["rows"] = [("parent",), ("child",)]
            return
        table = re.search(r'DELETE FROM "([^"]+)"', sql).group(1)
        if table == "parent" and "child" not in self._state["deleted"]:
            raise RuntimeError('FK violation: "child" still references "parent"')
        self._state["deleted"].add(table)
        self.rowcount = 5

    async def fetchall(self):
        return self._state.get("rows", [])


def _patch(monkeypatch, state):
    @asynccontextmanager
    async def fake_cursor(*a, **k):
        yield _FakeCursor(state)

    monkeypatch.setattr(purge, "get_async_cursor", fake_cursor)


@pytest.mark.asyncio
async def test_discovery_lists_tenant_scoped_tables(monkeypatch):
    _patch(monkeypatch, {"deleted": set()})
    assert await purge.tenant_scoped_tables() == ["parent", "child"]


@pytest.mark.asyncio
async def test_purge_deletes_all_tables_fk_safe(monkeypatch):
    state = {"deleted": set()}
    _patch(monkeypatch, state)
    deleted = await purge.purge_tenant_data("tenant-X")
    # both tables purged despite 'parent' failing on the first pass
    assert state["deleted"] == {"parent", "child"}
    assert deleted == {"parent": 5, "child": 5}
