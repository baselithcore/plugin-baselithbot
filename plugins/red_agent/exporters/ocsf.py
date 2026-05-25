"""OCSF 1.4 ``Vulnerability Finding`` (class_uid=2002) exporter.

Maps :class:`Finding` and :class:`ScanResult` into the Open Cybersecurity
Schema Framework normalized event shape so downstream SIEM/SOAR/GRC
platforms (Splunk, Sentinel, Chronicle, Panther, Tines, OpenObserve …)
can ingest red-agent findings without per-vendor adapters.

Schema reference: https://schema.ocsf.io/1.4.0/classes/vulnerability_finding

Mapping highlights:

* ``severity_id``: ``1=Informational, 2=Low, 3=Medium, 4=High, 5=Critical``
* ``status_id``: maps :class:`FindingState` → OCSF Status
  (``1=New``, ``2=In Progress``, ``4=Resolved``, ``5=Suppressed``).
* ``activity_id=1`` (``Create``); subsequent state changes flip
  ``activity_id`` to ``2`` (Update) / ``3`` (Close) — handled by the
  triage router when emitting OCSF webhook events.
* ``vulnerabilities[].cvss[]`` carries CVSS v3.x scores; EPSS/KEV
  enrichment lands in ``unmapped`` so consumers that already understand
  the OCSF schema can ignore non-standard fields.

The exporter is pure (no I/O), so it can run inside HTTP request
handlers without dragging persistence dependencies.
"""

from __future__ import annotations

from datetime import timezone
from typing import Any

from plugins.red_agent.models import (
    Finding,
    FindingState,
    ScanResult,
    Severity,
)

OCSF_VERSION = "1.4.0"
OCSF_CLASS_UID = 2002  # Vulnerability Finding
OCSF_CATEGORY_UID = 2  # Findings
OCSF_ACTIVITY_CREATE = 1
OCSF_ACTIVITY_UPDATE = 2
OCSF_ACTIVITY_CLOSE = 3

_OCSF_SEVERITY: dict[Severity, int] = {
    Severity.INFO: 1,
    Severity.LOW: 2,
    Severity.MEDIUM: 3,
    Severity.HIGH: 4,
    Severity.CRITICAL: 5,
}

_OCSF_STATUS: dict[FindingState, int] = {
    FindingState.OPEN: 1,  # New
    FindingState.TRIAGED: 2,  # In Progress
    FindingState.FIXED: 4,  # Resolved
    FindingState.WONTFIX: 5,  # Suppressed
    FindingState.ACCEPTED: 5,  # Suppressed
}


def _epoch_ms(dt: Any) -> int:
    """Return ``dt`` as epoch milliseconds. OCSF prefers epoch_ms for ``time``."""
    if dt is None:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def to_ocsf_event(
    finding: Finding,
    *,
    scan_id: str | None = None,
    tenant_id: str | None = None,
    activity_id: int = OCSF_ACTIVITY_CREATE,
    product_version: str = "0.1.0",
) -> dict[str, Any]:
    """Convert a single :class:`Finding` into an OCSF Vulnerability Finding event."""
    cvss_block: list[dict[str, Any]] = []
    if finding.cvss_score is not None:
        cvss_block.append(
            {
                "version": "3.1",
                "base_score": finding.cvss_score,
                "severity": finding.severity.value.upper(),
            }
        )

    cve_block: dict[str, Any] | None = None
    if finding.cve:
        cve_block = {
            "uid": finding.cve,
            "references": [f"https://nvd.nist.gov/vuln/detail/{finding.cve}"],
        }
        if cvss_block:
            cve_block["cvss"] = cvss_block

    cwe_block: dict[str, Any] | None = None
    if finding.cwe:
        cwe_block = {"uid": finding.cwe}

    vulnerability: dict[str, Any] = {
        "title": finding.title,
        "desc": finding.description,
        "severity": finding.severity.value.upper(),
        "remediation": ({"desc": finding.remediation} if finding.remediation else None),
        "vendor_name": finding.scanner,
    }
    if cve_block is not None:
        vulnerability["cve"] = cve_block
    if cwe_block is not None:
        vulnerability["cwe"] = cwe_block

    # Promote ATT&CK + detection guidance out of ``unmapped`` so OCSF
    # consumers that already understand the MITRE ATT&CK profile pick
    # them up natively.
    evidence = finding.evidence if isinstance(finding.evidence, dict) else {}
    techniques = evidence.get("attack_techniques") or []
    detection_guidance = evidence.get("detection_guidance") or None
    enrichments: list[dict[str, Any]] = []
    if techniques:
        attack_block = [
            {"technique": {"uid": t.get("id"), "name": t.get("name")}}
            for t in techniques
            if isinstance(t, dict) and t.get("id")
        ]
        if attack_block:
            vulnerability["attacks"] = attack_block
    if detection_guidance:
        enrichments.append(
            {
                "type": "detection_guidance",
                "name": "BaselithCore Sigma hint",
                "data": detection_guidance,
            }
        )

    resource: dict[str, Any] = {
        "type": "Asset",
        "uid": f"target::{finding.target}",
        "name": finding.target,
    }
    if finding.endpoint:
        resource["url"] = {"url_string": finding.endpoint}
    if finding.port is not None:
        resource["port"] = finding.port
    if finding.service:
        resource["svc_name"] = finding.service

    finding_info: dict[str, Any] = {
        "uid": str(finding.id),
        "title": finding.title,
        "desc": finding.description,
        "first_seen_time": _epoch_ms(finding.discovered_at),
        "last_seen_time": _epoch_ms(finding.discovered_at),
        "types": [finding.scanner],
    }
    if finding.due_at is not None:
        finding_info["due_time"] = _epoch_ms(finding.due_at)

    severity_id = _OCSF_SEVERITY[finding.severity]
    status_id = _OCSF_STATUS.get(finding.state, 1)

    event: dict[str, Any] = {
        "metadata": {
            "version": OCSF_VERSION,
            "product": {
                "name": "red_agent",
                "vendor_name": "BaselithCore",
                "version": product_version,
            },
            "profiles": ["security_control"],
        },
        "time": _epoch_ms(finding.discovered_at),
        "category_uid": OCSF_CATEGORY_UID,
        "category_name": "Findings",
        "class_uid": OCSF_CLASS_UID,
        "class_name": "Vulnerability Finding",
        "activity_id": activity_id,
        "type_uid": OCSF_CLASS_UID * 100 + activity_id,
        "severity_id": severity_id,
        "severity": finding.severity.value.upper(),
        "status_id": status_id,
        "finding_info": finding_info,
        "vulnerabilities": [vulnerability],
        "resources": [resource],
        "enrichments": enrichments,
        "unmapped": {
            "scanner": finding.scanner,
            "scan_id": scan_id,
            "tenant_id": tenant_id,
            "evidence": finding.evidence,
            "state": finding.state.value,
            "assignee": finding.assignee,
        },
    }
    return event


def to_ocsf(
    scan: ScanResult,
    *,
    tenant_id: str | None = None,
    product_version: str = "0.1.0",
) -> dict[str, Any]:
    """Convert a :class:`ScanResult` into an OCSF batch document.

    The output wraps each finding as an OCSF event in ``events[]`` plus a
    minimal ``scan`` envelope so a SIEM ingestion pipeline can route by
    scan and still process events individually.
    """
    events = [
        to_ocsf_event(
            f,
            scan_id=str(scan.scan_id),
            tenant_id=tenant_id,
            product_version=product_version,
        )
        for f in scan.findings
    ]
    return {
        "schema_version": OCSF_VERSION,
        "scan": {
            "uid": str(scan.scan_id),
            "status": scan.status.value,
            "started_at": _epoch_ms(scan.started_at),
            "finished_at": _epoch_ms(scan.finished_at) if scan.finished_at else None,
            "duration_seconds": scan.duration_seconds,
            "findings_count": len(scan.findings),
        },
        "events": events,
    }
