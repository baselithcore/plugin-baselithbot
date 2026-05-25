"""HTTP tests for the soft- and hard-delete endpoints.

Covers:

* ``DELETE /scans/{id}`` rejects scans in non-terminal states (409).
* ``DELETE /scans/{id}`` cascades to findings on terminal scans (204).
* ``DELETE /targets/{id}`` archives by default (idempotent).
* ``DELETE /targets/{id}?hard=true`` refuses to drop a target with runs
  unless ``purge_runs=true`` is also supplied.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.di.container import ServiceRegistry
from plugins.red_agent import dependencies as deps
from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.models import (
    ScanResult,
    ScanStatus,
    TargetKind,
    TargetRecord,
)
from plugins.red_agent.persistence import RedAgentPersistence, TargetPersistence
from plugins.red_agent.routers import scan_router, targets_router


# ──────────────────────────────────────────────────────────────────────
# Stubs


class _StubScans:
    """In-memory stand-in for RedAgentPersistence."""

    available = True

    def __init__(self) -> None:
        self.dsn = "stub"
        self.scans: dict[UUID, ScanResult] = {}
        self.deleted: list[UUID] = []

    async def get_scan(self, scan_id: UUID) -> ScanResult | None:
        return self.scans.get(scan_id)

    async def delete_scan(self, scan_id: UUID) -> bool:
        if scan_id not in self.scans:
            return False
        self.scans.pop(scan_id)
        self.deleted.append(scan_id)
        return True


class _StubTargets:
    available = True

    def __init__(self) -> None:
        self.dsn = "stub"
        self.targets: dict[UUID, TargetRecord] = {}
        self.runs_by_target: dict[UUID, int] = {}
        self.archived: list[UUID] = []
        self.hard_deleted: list[tuple[UUID, bool]] = []

    async def get(self, tid: UUID) -> TargetRecord | None:
        return self.targets.get(tid)

    async def archive(self, tid: UUID) -> bool:
        rec = self.targets.get(tid)
        if rec is None:
            return False
        if rec.archived_at is None:
            self.targets[tid] = rec.model_copy(
                update={"archived_at": datetime.now(timezone.utc)}
            )
            self.archived.append(tid)
            return True
        return False

    async def has_runs(self, tid: UUID) -> bool:
        return self.runs_by_target.get(tid, 0) > 0

    async def hard_delete(self, tid: UUID, *, purge_runs: bool) -> bool:
        if tid not in self.targets:
            return False
        self.targets.pop(tid)
        if purge_runs:
            self.runs_by_target[tid] = 0
        self.hard_deleted.append((tid, purge_runs))
        return True


class _StubAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def record(
        self,
        *,
        scan_id: UUID | None = None,
        actor: str = "",
        event: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "scan_id": scan_id,
                "actor": actor,
                "event": event,
                "payload": payload or {},
            }
        )


class _StubAgent:
    def __init__(self, persistence: _StubScans, audit: _StubAudit) -> None:
        self.persistence = persistence
        self.audit = audit


# ──────────────────────────────────────────────────────────────────────
# Fixtures


@pytest.fixture()
def app_state() -> tuple[FastAPI, _StubScans, _StubTargets, _StubAudit, _StubAgent]:
    scans = _StubScans()
    targets = _StubTargets()
    audit = _StubAudit()
    agent = _StubAgent(scans, audit)

    ServiceRegistry.register(TargetPersistence, targets)  # type: ignore[arg-type]
    ServiceRegistry.register(RedAgentPersistence, scans)  # type: ignore[arg-type]
    ServiceRegistry.register(AuditLogger, audit)  # type: ignore[arg-type]

    app = FastAPI()
    app.include_router(scan_router)
    app.include_router(targets_router)

    async def _allow() -> None:
        return None

    app.dependency_overrides[deps._security_operator_dep] = _allow
    app.dependency_overrides[deps._viewer_dep] = _allow
    app.dependency_overrides[deps.get_red_agent] = lambda: agent

    return app, scans, targets, audit, agent


def _make_scan(status: ScanStatus) -> ScanResult:
    return ScanResult(
        scan_id=uuid4(),
        status=status,
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        findings=[],
        target_id=None,
    )


def _make_target(name: str = "prod-api") -> TargetRecord:
    return TargetRecord(
        kind=TargetKind.WEB,
        name=name,
        value="https://api.example.com",
    )


# ──────────────────────────────────────────────────────────────────────
# DELETE /scans/{id}


def test_delete_scan_rejects_running(app_state) -> None:
    app, scans, _, _, _ = app_state
    scan = _make_scan(ScanStatus.RUNNING)
    scans.scans[scan.scan_id] = scan
    client = TestClient(app)

    resp = client.delete(f"/scans/{scan.scan_id}")
    assert resp.status_code == 409
    assert scan.scan_id in scans.scans


def test_delete_scan_404_when_missing(app_state) -> None:
    app, *_ = app_state
    client = TestClient(app)
    resp = client.delete(f"/scans/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "status", [ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED]
)
def test_delete_scan_terminal_succeeds(app_state, status: ScanStatus) -> None:
    app, scans, _, audit, _ = app_state
    scan = _make_scan(status)
    scans.scans[scan.scan_id] = scan
    client = TestClient(app)

    resp = client.delete(f"/scans/{scan.scan_id}")
    assert resp.status_code == 204
    assert scan.scan_id not in scans.scans
    assert any(e["event"] == "scan.deleted" for e in audit.events)


# ──────────────────────────────────────────────────────────────────────
# DELETE /targets/{id}


def test_delete_target_soft_archives(app_state) -> None:
    app, _, targets, audit, _ = app_state
    rec = _make_target()
    targets.targets[rec.id] = rec
    client = TestClient(app)

    resp = client.delete(f"/targets/{rec.id}")
    assert resp.status_code == 204
    assert rec.id in targets.archived
    assert any(e["event"] == "target.archived" for e in audit.events)


def test_delete_target_soft_idempotent(app_state) -> None:
    app, _, targets, _, _ = app_state
    rec = _make_target().model_copy(update={"archived_at": datetime.now(timezone.utc)})
    targets.targets[rec.id] = rec
    client = TestClient(app)

    resp = client.delete(f"/targets/{rec.id}")
    assert resp.status_code == 204
    # archived list stays empty: archive() refused to re-archive.
    assert rec.id not in targets.archived


def test_delete_target_hard_refused_with_runs(app_state) -> None:
    app, _, targets, _, _ = app_state
    rec = _make_target()
    targets.targets[rec.id] = rec
    targets.runs_by_target[rec.id] = 3
    client = TestClient(app)

    resp = client.delete(f"/targets/{rec.id}?hard=true")
    assert resp.status_code == 409
    assert rec.id in targets.targets


def test_delete_target_hard_with_purge(app_state) -> None:
    app, _, targets, audit, _ = app_state
    rec = _make_target()
    targets.targets[rec.id] = rec
    targets.runs_by_target[rec.id] = 3
    client = TestClient(app)

    resp = client.delete(f"/targets/{rec.id}?hard=true&purge_runs=true")
    assert resp.status_code == 204
    assert rec.id not in targets.targets
    assert (rec.id, True) in targets.hard_deleted
    payload = next(e["payload"] for e in audit.events if e["event"] == "target.deleted")
    assert payload["purged_runs"] is True


def test_delete_target_404(app_state) -> None:
    app, *_ = app_state
    client = TestClient(app)
    resp = client.delete(f"/targets/{uuid4()}")
    assert resp.status_code == 404
