"""HTTP tests for the per-finding evidence ledger endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.red_agent import dependencies as deps
from plugins.red_agent.models import Finding, Severity
from plugins.red_agent.routers import findings_router


class _StubPersistence:
    available = True

    def __init__(self) -> None:
        self.dsn = "stub"
        self.findings: dict[UUID, tuple[Finding, UUID]] = {}
        self.audit_chain: dict[UUID, list[dict[str, Any]]] = {}

    async def get_finding(self, finding_id: UUID) -> tuple[Finding, UUID] | None:
        return self.findings.get(finding_id)

    async def list_scan_audit(
        self, scan_id: UUID, *, limit: int = 500
    ) -> list[dict[str, Any]]:
        del limit
        return list(self.audit_chain.get(scan_id, []))


class _StubAgent:
    def __init__(self, persistence: _StubPersistence) -> None:
        self.persistence = persistence


@pytest.fixture()
def http_state() -> tuple[TestClient, _StubPersistence]:
    persistence = _StubPersistence()
    agent = _StubAgent(persistence)

    app = FastAPI()
    app.include_router(findings_router)

    async def _allow() -> None:
        return None

    app.dependency_overrides[deps._viewer_dep] = _allow
    app.dependency_overrides[deps.get_red_agent] = lambda: agent
    return TestClient(app), persistence


def _make_finding() -> Finding:
    return Finding(
        scanner="nuclei",
        title="t",
        description="d",
        severity=Severity.HIGH,
        target="https://example.com",
        evidence={"command": "nuclei -u https://example.com"},
    )


def test_get_evidence_returns_finding_and_chain(
    http_state: tuple[TestClient, _StubPersistence],
) -> None:
    http, persistence = http_state
    finding = _make_finding()
    scan_id = uuid4()
    persistence.findings[finding.id] = (finding, scan_id)
    persistence.audit_chain[scan_id] = [
        {
            "id": 1,
            "scan_id": str(scan_id),
            "actor": "op",
            "event": "scan.submitted",
            "payload": {"target": "https://example.com"},
            "created_at": datetime(2026, 4, 29, 18, 0, tzinfo=timezone.utc),
        },
        {
            "id": 2,
            "scan_id": str(scan_id),
            "actor": "red_agent",
            "event": "scan.planner_step",
            "payload": {"scanners": ["nuclei"], "target": "https://example.com"},
            "created_at": datetime(2026, 4, 29, 18, 1, tzinfo=timezone.utc),
        },
    ]

    resp = http.get(f"/findings/{finding.id}/evidence")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scan_id"] == str(scan_id)
    assert body["finding"]["id"] == str(finding.id)
    events = [event["event"] for event in body["chain"]]
    assert events == ["scan.submitted", "scan.planner_step"]


def test_evidence_404_for_missing_finding(
    http_state: tuple[TestClient, _StubPersistence],
) -> None:
    http, _ = http_state
    resp = http.get(f"/findings/{uuid4()}/evidence")
    assert resp.status_code == 404


def test_evidence_chain_empty_when_no_audit_rows(
    http_state: tuple[TestClient, _StubPersistence],
) -> None:
    http, persistence = http_state
    finding = _make_finding()
    scan_id = uuid4()
    persistence.findings[finding.id] = (finding, scan_id)
    resp = http.get(f"/findings/{finding.id}/evidence")
    assert resp.status_code == 200
    assert resp.json()["chain"] == []
