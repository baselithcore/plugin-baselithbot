"""OCSF 1.4 Vulnerability Finding exporter tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from plugins.red_agent.exporters import to_ocsf, to_ocsf_event
from plugins.red_agent.models import (
    Finding,
    FindingState,
    ScanResult,
    ScanStatus,
    Severity,
)


def _scan(findings: list[Finding]) -> ScanResult:
    started = datetime.now(timezone.utc)
    return ScanResult(
        scan_id=uuid4(),
        status=ScanStatus.COMPLETED,
        started_at=started,
        finished_at=started,
        findings=findings,
    )


def _finding(**kwargs: object) -> Finding:
    base: dict[str, object] = {
        "scanner": "nuclei",
        "title": "Reflected XSS",
        "description": "input not encoded",
        "severity": Severity.HIGH,
        "target": "example.com",
    }
    base.update(kwargs)
    return Finding(**base)  # type: ignore[arg-type]


def test_attack_techniques_promoted_to_vulnerability_attacks() -> None:
    f = _finding(
        cwe="CWE-89",
        evidence={
            "attack_techniques": [
                {"id": "T1190", "name": "Exploit Public-Facing Application"},
            ]
        },
    )
    event = to_ocsf_event(f, scan_id="abc")
    attacks = event["vulnerabilities"][0]["attacks"]
    assert attacks[0]["technique"]["uid"] == "T1190"


def test_detection_guidance_lands_in_enrichments() -> None:
    f = _finding(
        cwe="CWE-89",
        evidence={
            "detection_guidance": {
                "logsource": {"product": "webserver", "category": "webserver"},
                "detection": "UNION SELECT",
                "mitigations": ["prepared statements"],
            }
        },
    )
    event = to_ocsf_event(f, scan_id="abc")
    enrichments = event["enrichments"]
    assert len(enrichments) == 1
    assert enrichments[0]["type"] == "detection_guidance"
    assert enrichments[0]["data"]["logsource"]["product"] == "webserver"


def test_no_evidence_keeps_attacks_empty_and_no_enrichment() -> None:
    f = _finding(cwe="CWE-79")
    event = to_ocsf_event(f, scan_id="abc")
    assert "attacks" not in event["vulnerabilities"][0]
    assert event["enrichments"] == []


def test_empty_scan_envelope() -> None:
    doc = to_ocsf(_scan([]))
    assert doc["schema_version"] == "1.4.0"
    assert doc["events"] == []
    assert doc["scan"]["findings_count"] == 0
    assert doc["scan"]["status"] == "completed"


def test_event_carries_class_and_severity_ids() -> None:
    f = _finding(severity=Severity.CRITICAL, cve="CVE-2025-0001")
    event = to_ocsf_event(f)
    assert event["class_uid"] == 2002
    assert event["category_uid"] == 2
    assert event["severity_id"] == 5
    assert event["severity"] == "CRITICAL"
    assert event["activity_id"] == 1
    assert event["type_uid"] == 200201


def test_event_includes_cve_with_nvd_reference() -> None:
    f = _finding(cve="CVE-2024-9999", cvss_score=9.8)
    event = to_ocsf_event(f)
    vuln = event["vulnerabilities"][0]
    assert vuln["cve"]["uid"] == "CVE-2024-9999"
    assert "https://nvd.nist.gov/vuln/detail/CVE-2024-9999" in vuln["cve"]["references"]
    assert vuln["cve"]["cvss"][0]["base_score"] == 9.8


def test_event_status_id_maps_finding_state() -> None:
    fixed = _finding(state=FindingState.FIXED)
    triaged = _finding(state=FindingState.TRIAGED)
    wontfix = _finding(state=FindingState.WONTFIX)
    assert to_ocsf_event(fixed)["status_id"] == 4
    assert to_ocsf_event(triaged)["status_id"] == 2
    assert to_ocsf_event(wontfix)["status_id"] == 5


def test_resource_block_carries_endpoint_port_service() -> None:
    f = _finding(endpoint="https://example.com/login", port=443, service="https")
    event = to_ocsf_event(f)
    res = event["resources"][0]
    assert res["uid"] == "target::example.com"
    assert res["url"]["url_string"] == "https://example.com/login"
    assert res["port"] == 443
    assert res["svc_name"] == "https"


def test_unmapped_block_preserves_evidence() -> None:
    f = _finding(evidence={"epss_score": 0.7, "kev_listed": True})
    event = to_ocsf_event(f, scan_id="scan-123", tenant_id="acme")
    assert event["unmapped"]["scan_id"] == "scan-123"
    assert event["unmapped"]["tenant_id"] == "acme"
    assert event["unmapped"]["evidence"]["kev_listed"] is True
    assert event["unmapped"]["evidence"]["epss_score"] == 0.7


def test_to_ocsf_emits_one_event_per_finding() -> None:
    findings = [
        _finding(scanner="nmap", severity=Severity.INFO, title="port 22 open"),
        _finding(scanner="zap", severity=Severity.MEDIUM, title="missing CSP"),
    ]
    doc = to_ocsf(_scan(findings))
    assert len(doc["events"]) == 2
    assert doc["scan"]["findings_count"] == 2
    titles = {e["finding_info"]["title"] for e in doc["events"]}
    assert titles == {"port 22 open", "missing CSP"}
