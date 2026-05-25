"""HTTP tests for engagement / campaign endpoints."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.di.container import ServiceRegistry
from plugins.red_agent import dependencies as deps
from plugins.red_agent.models import (
    EngagementCreate,
    EngagementRecord,
    EngagementStatus,
    EngagementUpdate,
    Finding,
    ScanResult,
    ScanStatus,
    Severity,
)
from plugins.red_agent.persistence import EngagementPersistence
from plugins.red_agent.routers import engagements_router


class _StubEngagements:
    available = True

    def __init__(self) -> None:
        self.rows: dict[UUID, EngagementRecord] = {}

    async def from_create(
        self,
        body: EngagementCreate,
        *,
        tenant_id: str | None,
        created_by: str | None,
    ) -> EngagementRecord:
        record = EngagementRecord(
            name=body.name,
            objective=body.objective,
            rules=body.rules,
            tags=body.tags,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        self.rows[record.id] = record
        return record

    async def list(
        self,
        *,
        tenant_id: str | None = None,
        status: EngagementStatus | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EngagementRecord]:
        del tenant_id, limit
        rows = list(self.rows.values())
        if status is not None:
            rows = [row for row in rows if row.status == status]
        if not include_archived:
            rows = [row for row in rows if row.status != EngagementStatus.ARCHIVED]
        return rows[offset:]

    async def get(self, engagement_id: UUID) -> EngagementRecord | None:
        return self.rows.get(engagement_id)

    async def update(
        self, engagement_id: UUID, update: EngagementUpdate
    ) -> EngagementRecord | None:
        current = self.rows.get(engagement_id)
        if current is None:
            return None
        patch: dict[str, Any] = {}
        for key, value in update.model_dump(exclude_unset=True).items():
            patch[key] = value
        next_record = current.model_copy(update=patch)
        self.rows[engagement_id] = next_record
        return next_record

    async def archive(self, engagement_id: UUID) -> bool:
        updated = await self.update(
            engagement_id, EngagementUpdate(status=EngagementStatus.ARCHIVED)
        )
        return updated is not None


class _StubScanPersistence:
    available = True

    def __init__(self) -> None:
        self.dsn = "stub"
        self.scans_by_engagement: dict[UUID, list[ScanResult]] = {}

    async def list_scans(
        self,
        *,
        engagement_id: UUID | None = None,
        limit: int = 50,
        **_: Any,
    ) -> list[dict[str, Any]]:
        del limit
        results = (
            self.scans_by_engagement.get(engagement_id, []) if engagement_id else []
        )
        return [{"id": r.scan_id} for r in results]

    async def get_scan(self, scan_id: UUID) -> ScanResult | None:
        for runs in self.scans_by_engagement.values():
            for r in runs:
                if r.scan_id == scan_id:
                    return r
        return None


class _StubAgent:
    def __init__(self, persistence: _StubScanPersistence) -> None:
        self.persistence = persistence


@pytest.fixture()
def client() -> tuple[TestClient, _StubEngagements, _StubScanPersistence]:
    store = _StubEngagements()
    scan_persistence = _StubScanPersistence()
    agent = _StubAgent(scan_persistence)
    ServiceRegistry.register(EngagementPersistence, store)  # type: ignore[arg-type]

    app = FastAPI()
    app.include_router(engagements_router)

    async def _allow() -> None:
        return None

    app.dependency_overrides[deps._security_operator_dep] = _allow
    app.dependency_overrides[deps._viewer_dep] = _allow
    app.dependency_overrides[deps.get_red_agent] = lambda: agent
    return TestClient(app), store, scan_persistence


def test_create_and_list_engagement(client) -> None:
    http, store, _ = client
    resp = http.post(
        "/engagements",
        json={
            "name": "External exposure validation",
            "objective": "Validate public entrypoint exploitability.",
            "rules": {
                "scope_allowlist": ["example.com"],
                "excluded_targets": ["status.example.com"],
                "max_intensity": "active",
                "require_human_approval": True,
            },
            "tags": ["external", "q2"],
        },
    )

    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "External exposure validation"
    assert created["rules"]["max_intensity"] == "active"
    assert len(store.rows) == 1

    listed = http.get("/engagements").json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]


def test_get_missing_engagement_returns_404(client) -> None:
    http, _, _ = client
    resp = http.get("/engagements/00000000-0000-0000-0000-000000000001")
    assert resp.status_code == 404


def _finding_with_guidance() -> Finding:
    return Finding(
        scanner="nuclei",
        title="SQL injection",
        description="d",
        severity=Severity.HIGH,
        target="https://example.com",
        cwe="CWE-89",
        evidence={
            "detection_guidance": {
                "logsource": {"product": "webserver", "category": "webserver"},
                "detection": "Look for `UNION SELECT`",
                "mitigations": ["prepared statements"],
            }
        },
    )


def _scan_with(findings: list[Finding]) -> ScanResult:
    started = datetime(2026, 4, 29, tzinfo=timezone.utc)
    return ScanResult(
        scan_id=uuid4(),
        status=ScanStatus.COMPLETED,
        started_at=started,
        finished_at=started,
        findings=findings,
    )


def test_engagement_sigma_bundle_packs_yaml_per_finding(client) -> None:
    http, _, scans = client
    body = {
        "name": "Sigma bundle test",
        "objective": "test",
        "rules": {"max_intensity": "passive", "require_human_approval": True},
    }
    created = http.post("/engagements", json=body).json()
    eng_uuid = UUID(created["id"])

    scan = _scan_with([_finding_with_guidance(), _finding_with_guidance()])
    scans.scans_by_engagement[eng_uuid] = [scan]

    resp = http.get(f"/engagements/{eng_uuid}/sigma.zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    bundle = zipfile.ZipFile(io.BytesIO(resp.content))
    yml_names = [n for n in bundle.namelist() if n.endswith(".sigma.yml")]
    assert len(yml_names) == 2
    assert "MANIFEST.txt" in bundle.namelist()
    manifest = bundle.read("MANIFEST.txt").decode()
    assert "Sigma bundle test" in manifest


def test_engagement_sigma_bundle_409_when_no_guidance(client) -> None:
    http, _, scans = client
    body = {
        "name": "Bare engagement",
        "objective": "test",
        "rules": {"max_intensity": "passive", "require_human_approval": True},
    }
    created = http.post("/engagements", json=body).json()
    eng_uuid = UUID(created["id"])
    plain_finding = Finding(
        scanner="nuclei",
        title="t",
        description="d",
        severity=Severity.HIGH,
        target="https://example.com",
    )
    scans.scans_by_engagement[eng_uuid] = [_scan_with([plain_finding])]
    resp = http.get(f"/engagements/{eng_uuid}/sigma.zip")
    assert resp.status_code == 409


def test_engagement_sigma_bundle_404_when_engagement_unknown(client) -> None:
    http, _, _ = client
    resp = http.get(f"/engagements/{uuid4()}/sigma.zip")
    assert resp.status_code == 404
