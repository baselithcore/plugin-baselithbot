"""SARIF 2.1.0 exporter tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from plugins.red_agent.models import (
    Finding,
    ScanResult,
    ScanStatus,
    Severity,
)
from plugins.red_agent.sarif import to_sarif


def _result_with(findings: list[Finding]) -> ScanResult:
    return ScanResult(
        scan_id=uuid4(),
        status=ScanStatus.COMPLETED,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        findings=findings,
    )


def test_empty_scan_returns_minimal_envelope() -> None:
    doc = to_sarif(_result_with([]))
    assert doc["version"] == "2.1.0"
    assert "$schema" in doc
    assert doc["runs"] == []


def test_groups_findings_by_scanner() -> None:
    findings = [
        Finding(
            scanner="nmap",
            title="open 80",
            description="d",
            severity=Severity.INFO,
            target="example.com",
        ),
        Finding(
            scanner="nuclei",
            title="xss",
            description="reflected",
            severity=Severity.HIGH,
            cwe="CWE-79",
            target="example.com",
            endpoint="https://example.com/?q=x",
        ),
        Finding(
            scanner="nuclei",
            title="open redirect",
            description="r",
            severity=Severity.MEDIUM,
            target="example.com",
        ),
    ]
    doc = to_sarif(_result_with(findings))
    runs_by_tool = {r["tool"]["driver"]["name"]: r for r in doc["runs"]}
    assert set(runs_by_tool.keys()) == {"nmap", "nuclei"}
    assert len(runs_by_tool["nuclei"]["results"]) == 2
    assert len(runs_by_tool["nmap"]["results"]) == 1


def test_severity_to_level_mapping() -> None:
    f = Finding(
        scanner="x",
        title="t",
        description="d",
        severity=Severity.CRITICAL,
        target="example.com",
    )
    doc = to_sarif(_result_with([f]))
    assert doc["runs"][0]["results"][0]["level"] == "error"

    f2 = Finding(
        scanner="x",
        title="t",
        description="d",
        severity=Severity.LOW,
        target="example.com",
    )
    doc2 = to_sarif(_result_with([f2]))
    assert doc2["runs"][0]["results"][0]["level"] == "note"


def test_attack_techniques_and_detection_promoted_to_properties() -> None:
    f = Finding(
        scanner="nuclei",
        title="sql injection",
        description="d",
        severity=Severity.HIGH,
        cwe="CWE-89",
        target="example.com",
        evidence={
            "attack_techniques": [
                {"id": "T1190", "name": "Exploit Public-Facing Application"},
            ],
            "detection_guidance": {
                "logsource": {"product": "webserver", "category": "webserver"},
                "detection": "look for UNION SELECT",
                "mitigations": ["Parameterized queries"],
            },
        },
    )
    doc = to_sarif(_result_with([f]))
    props = doc["runs"][0]["results"][0]["properties"]
    assert props["attack_techniques"][0]["id"] == "T1190"
    assert props["tags"] == ["T1190"]
    assert props["detection_guidance"]["logsource"]["product"] == "webserver"


def test_rule_dedup_within_scanner() -> None:
    same_cwe = [
        Finding(
            scanner="nuclei",
            title="xss-1",
            description="d",
            severity=Severity.HIGH,
            cwe="CWE-79",
            target="example.com",
        ),
        Finding(
            scanner="nuclei",
            title="xss-2",
            description="d",
            severity=Severity.HIGH,
            cwe="CWE-79",
            target="example.com",
        ),
    ]
    doc = to_sarif(_result_with(same_cwe))
    rules = doc["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 1
    assert rules[0]["id"] == "CWE-79"
    assert all(r["ruleIndex"] == 0 for r in doc["runs"][0]["results"])
