"""VEX (OpenVEX 0.2.0 + CycloneDX VEX 1.6) ingestion + suppression tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plugins.red_agent.enrichers.vex import VEXStore, VexEnricher
from plugins.red_agent.models import Finding, Severity


def _finding(
    *, cve: str | None = "CVE-2025-0001", target: str = "pkg:npm/foo@1.0.0"
) -> Finding:
    return Finding(
        scanner="grype",
        title=f"{cve or 'no-cve'} on foo",
        description="package vulnerability",
        severity=Severity.HIGH,
        target=target,
        cve=cve,
    )


def _write_openvex(dir_: Path, *, cve: str, status: str, products: list[str]) -> Path:
    doc = {
        "@context": "https://openvex.dev/ns/v0.2.0",
        "@id": f"https://example.com/vex/{cve}",
        "author": "vendor",
        "timestamp": "2026-04-29T00:00:00Z",
        "version": 1,
        "statements": [
            {
                "vulnerability": {"name": cve},
                "products": [{"@id": p} for p in products],
                "status": status,
                "justification": "vulnerable_code_not_in_execute_path",
                "impact_statement": "see code review",
            }
        ],
    }
    path = dir_ / f"{cve.lower()}.openvex.json"
    path.write_text(json.dumps(doc))
    return path


def _write_cdx_vex(dir_: Path, *, cve: str, state: str, ref: str) -> Path:
    doc = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "vulnerabilities": [
            {
                "id": cve,
                "analysis": {
                    "state": state,
                    "justification": "code_not_present",
                    "detail": "transitive only",
                },
                "affects": [{"ref": ref}],
            }
        ],
    }
    path = dir_ / f"{cve.lower()}.cdx.json"
    path.write_text(json.dumps(doc))
    return path


def test_disabled_when_no_store() -> None:
    enricher = VexEnricher(store=None, enabled=True)
    assert enricher.enabled is False


def test_pass_through_without_cve(tmp_path: Path) -> None:
    _write_openvex(
        tmp_path,
        cve="CVE-2025-0001",
        status="not_affected",
        products=["pkg:npm/foo@1.0.0"],
    )
    store = VEXStore(directory=tmp_path)
    enricher = VexEnricher(store=store, enabled=True)
    findings = [_finding(cve=None)]
    kept, suppressed = enricher.enrich(findings)
    assert len(kept) == 1
    assert suppressed == []


def test_openvex_not_affected_suppresses(tmp_path: Path) -> None:
    _write_openvex(
        tmp_path,
        cve="CVE-2025-0001",
        status="not_affected",
        products=["pkg:npm/foo@1.0.0"],
    )
    store = VEXStore(directory=tmp_path)
    enricher = VexEnricher(store=store, enabled=True)
    kept, suppressed = enricher.enrich([_finding()])
    assert kept == []
    assert len(suppressed) == 1
    ev = suppressed[0].evidence
    assert ev["vex_status"] == "not_affected"
    assert ev["vex_justification"] == "vulnerable_code_not_in_execute_path"


def test_openvex_fixed_suppresses_when_flag_on(tmp_path: Path) -> None:
    _write_openvex(
        tmp_path, cve="CVE-2025-0002", status="fixed", products=["pkg:npm/foo@1.0.0"]
    )
    store = VEXStore(directory=tmp_path)
    enricher = VexEnricher(store=store, enabled=True, suppress_fixed=True)
    kept, suppressed = enricher.enrich([_finding(cve="CVE-2025-0002")])
    assert kept == []
    assert len(suppressed) == 1


def test_openvex_fixed_kept_when_flag_off(tmp_path: Path) -> None:
    _write_openvex(
        tmp_path, cve="CVE-2025-0003", status="fixed", products=["pkg:npm/foo@1.0.0"]
    )
    store = VEXStore(directory=tmp_path)
    enricher = VexEnricher(store=store, enabled=True, suppress_fixed=False)
    kept, suppressed = enricher.enrich([_finding(cve="CVE-2025-0003")])
    assert len(kept) == 1
    assert suppressed == []
    assert kept[0].evidence["vex_status"] == "fixed"


def test_cyclonedx_false_positive_suppresses(tmp_path: Path) -> None:
    _write_cdx_vex(
        tmp_path, cve="CVE-2025-0004", state="false_positive", ref="pkg:npm/foo@1.0.0"
    )
    store = VEXStore(directory=tmp_path)
    enricher = VexEnricher(store=store, enabled=True)
    kept, suppressed = enricher.enrich([_finding(cve="CVE-2025-0004")])
    assert kept == []
    assert len(suppressed) == 1
    assert suppressed[0].evidence["vex_status"] == "false_positive"


def test_cyclonedx_exploitable_only_annotates(tmp_path: Path) -> None:
    _write_cdx_vex(
        tmp_path, cve="CVE-2025-0005", state="exploitable", ref="pkg:npm/foo@1.0.0"
    )
    store = VEXStore(directory=tmp_path)
    enricher = VexEnricher(store=store, enabled=True)
    kept, suppressed = enricher.enrich([_finding(cve="CVE-2025-0005")])
    assert len(kept) == 1
    assert suppressed == []
    assert kept[0].evidence["vex_status"] == "exploitable"


def test_unmatched_cve_passes_through(tmp_path: Path) -> None:
    _write_openvex(
        tmp_path,
        cve="CVE-2025-0001",
        status="not_affected",
        products=["pkg:npm/foo@1.0.0"],
    )
    store = VEXStore(directory=tmp_path)
    enricher = VexEnricher(store=store, enabled=True)
    kept, suppressed = enricher.enrich([_finding(cve="CVE-9999-9999")])
    assert len(kept) == 1
    assert suppressed == []


def test_store_caches_until_mtime_changes(tmp_path: Path) -> None:
    path = _write_openvex(
        tmp_path, cve="CVE-2025-0007", status="not_affected", products=[]
    )
    store = VEXStore(directory=tmp_path)
    first = store.load()
    second = store.load()
    assert len(first) == 1
    assert len(second) == 1
    # Bump mtime + change status
    new_doc = {
        "@context": "https://openvex.dev/ns/v0.2.0",
        "@id": "x",
        "author": "vendor",
        "timestamp": "2026-04-29T01:00:00Z",
        "version": 2,
        "statements": [
            {
                "vulnerability": {"name": "CVE-2025-0007"},
                "products": [],
                "status": "fixed",
            }
        ],
    }
    path.write_text(json.dumps(new_doc))
    import os

    os.utime(path, (path.stat().st_atime + 10, path.stat().st_mtime + 10))
    third = store.load()
    assert third[0].status == "fixed"


@pytest.mark.asyncio
async def test_run_vex_suppression_audits(tmp_path: Path) -> None:
    """run_vex_suppression should emit a single audit event with cve list."""
    from plugins.red_agent._agent_helpers import run_vex_suppression

    _write_openvex(tmp_path, cve="CVE-2025-0001", status="not_affected", products=[])
    store = VEXStore(directory=tmp_path)
    enricher = VexEnricher(store=store, enabled=True)

    audited: list[dict[str, object]] = []

    class _AuditStub:
        async def record(self, **kwargs: object) -> None:
            audited.append(kwargs)

    from uuid import uuid4

    findings = [_finding(cve="CVE-2025-0001")]
    kept = await run_vex_suppression(
        vex=enricher,
        audit=_AuditStub(),
        scan_id=uuid4(),
        findings=findings,  # type: ignore[arg-type]
    )
    assert kept == []
    assert len(audited) == 1
    payload = audited[0]["payload"]
    assert payload["suppressed"] == 1  # type: ignore[index]
    assert "CVE-2025-0001" in payload["cves"]  # type: ignore[index]
