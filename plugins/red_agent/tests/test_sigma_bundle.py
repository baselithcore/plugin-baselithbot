"""HTTP tests for the per-scan Sigma rule ZIP bundle endpoint."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.red_agent import dependencies as deps
from plugins.red_agent.models import (
    Finding,
    ScanResult,
    ScanStatus,
    Severity,
)
from plugins.red_agent.routers import reports_router


def _finding(**kwargs: Any) -> Finding:
    base: dict[str, Any] = {
        "scanner": "nuclei",
        "title": "SQL injection",
        "description": "d",
        "severity": Severity.HIGH,
        "target": "https://example.com",
        "cwe": "CWE-89",
    }
    base.update(kwargs)
    return Finding(**base)


def _with_guidance() -> Finding:
    f = _finding()
    f.evidence = {
        "detection_guidance": {
            "logsource": {"product": "webserver", "category": "webserver"},
            "detection": "Look for `UNION SELECT` payloads",
            "mitigations": ["prepared statements"],
        }
    }
    return f


class _StubAgent:
    def __init__(self, scans: dict[UUID, ScanResult]) -> None:
        self.scans = scans

    async def get_scan(self, scan_id: UUID) -> ScanResult | None:
        return self.scans.get(scan_id)


@pytest.fixture()
def http() -> tuple[TestClient, dict[UUID, ScanResult]]:
    scans: dict[UUID, ScanResult] = {}
    agent = _StubAgent(scans)
    app = FastAPI()
    app.include_router(reports_router)

    async def _allow() -> None:
        return None

    app.dependency_overrides[deps._viewer_dep] = _allow
    app.dependency_overrides[deps.get_red_agent] = lambda: agent
    return TestClient(app), scans


def _make_scan(findings: list[Finding]) -> ScanResult:
    started = datetime(2026, 4, 29, tzinfo=timezone.utc)
    return ScanResult(
        scan_id=uuid4(),
        status=ScanStatus.COMPLETED,
        started_at=started,
        finished_at=started,
        findings=findings,
    )


def test_zip_contains_sigma_rule_per_emittable_finding(
    http: tuple[TestClient, dict[UUID, ScanResult]],
) -> None:
    client, scans = http
    f1 = _with_guidance()
    f2 = _with_guidance()
    f3 = _finding()  # no guidance — must be skipped
    scan = _make_scan([f1, f2, f3])
    scans[scan.scan_id] = scan

    resp = client.get(f"/reports/{scan.scan_id}/sigma.zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    bundle = zipfile.ZipFile(io.BytesIO(resp.content))
    names = bundle.namelist()
    assert "MANIFEST.txt" in names
    yml_names = [n for n in names if n.endswith(".sigma.yml")]
    assert len(yml_names) == 2
    parsed = yaml.safe_load(bundle.read(yml_names[0]).decode())
    assert parsed["status"] == "experimental"


def test_zip_409_when_no_findings_have_guidance(
    http: tuple[TestClient, dict[UUID, ScanResult]],
) -> None:
    client, scans = http
    scan = _make_scan([_finding(), _finding()])
    scans[scan.scan_id] = scan
    resp = client.get(f"/reports/{scan.scan_id}/sigma.zip")
    assert resp.status_code == 409


def test_zip_404_for_unknown_scan(
    http: tuple[TestClient, dict[UUID, ScanResult]],
) -> None:
    client, _ = http
    resp = client.get(f"/reports/{uuid4()}/sigma.zip")
    assert resp.status_code == 404


def test_zip_manifest_lists_finding_ids(
    http: tuple[TestClient, dict[UUID, ScanResult]],
) -> None:
    client, scans = http
    f = _with_guidance()
    scan = _make_scan([f])
    scans[scan.scan_id] = scan
    resp = client.get(f"/reports/{scan.scan_id}/sigma.zip")
    assert resp.status_code == 200
    bundle = zipfile.ZipFile(io.BytesIO(resp.content))
    manifest = bundle.read("MANIFEST.txt").decode()
    assert str(f.id) in manifest
    assert f.title in manifest
