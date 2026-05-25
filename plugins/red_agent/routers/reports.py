"""Report export endpoints (SARIF, OCSF, compliance, JSON, Sigma)."""

from __future__ import annotations

import io
import zipfile
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from plugins.red_agent.agent import RedAgent
from plugins.red_agent.dependencies import get_red_agent, require_viewer
from plugins.red_agent.enrichers.compliance_mapper import coverage_summary
from plugins.red_agent.exporters import to_ocsf, to_sigma_yaml
from plugins.red_agent.sarif import to_sarif

router = APIRouter(prefix="/reports", tags=["red-agent"])

_FRAMEWORK_PREFIX: dict[str, str] = {
    "cis": "CIS-",
    "pci": "PCI-",
    "pci_dss_4": "PCI-",
    "nist": "NIST-",
    "nist_800_53": "NIST-",
    "iso27001": "ISO27001-",
    "soc2": "SOC2-",
}


@router.get("/{scan_id}/sarif", dependencies=[require_viewer()])
async def export_sarif(
    scan_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
) -> dict[str, Any]:
    scan = await agent.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return to_sarif(scan)


@router.get("/{scan_id}/ocsf", dependencies=[require_viewer()])
async def export_ocsf(
    scan_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
) -> dict[str, Any]:
    """Export the scan as an OCSF 1.4 Vulnerability Finding batch.

    Each finding becomes one normalized OCSF event (class_uid=2002) so
    SIEM/SOAR/GRC consumers (Splunk, Sentinel, Chronicle, Panther …)
    can ingest the feed without per-vendor adapters.
    """
    scan = await agent.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return to_ocsf(scan)


@router.get("/{scan_id}/compliance", dependencies=[require_viewer()])
async def export_compliance(
    scan_id: UUID,
    framework: str | None = Query(
        default=None,
        description=(
            "Filter coverage by framework. One of: cis, pci, pci_dss_4, "
            "nist, nist_800_53, iso27001, soc2. Omit for the full mapping."
        ),
    ),
    agent: RedAgent = Depends(get_red_agent),
) -> dict[str, Any]:
    """Return per-control coverage of compliance frameworks for the scan.

    Output: ``{"framework": "...", "controls": {control_id: {count,
    severities, finding_ids}}}``. Use to feed GRC dashboards or the
    auditor's "show me PCI 6.5.x evidence" query.
    """
    scan = await agent.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    prefix: str | None = None
    if framework is not None:
        prefix = _FRAMEWORK_PREFIX.get(framework.lower())
        if prefix is None:
            raise HTTPException(
                status_code=400,
                detail=f"unknown framework {framework!r}",
            )
    return {
        "scan_id": str(scan.scan_id),
        "framework": framework,
        "controls": coverage_summary(scan.findings, framework_prefix=prefix),
        "findings_total": len(scan.findings),
    }


@router.get("/{scan_id}/sigma.zip", dependencies=[require_viewer()])
async def export_sigma_bundle(
    scan_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
) -> Response:
    """Bundle every finding's Sigma rule for the scan as a ZIP archive.

    Findings without ``detection_guidance`` are skipped silently. The
    archive ships with one ``.sigma.yml`` per emittable finding plus a
    ``MANIFEST.txt`` listing the included finding ids and titles.
    """
    scan = await agent.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")

    buf = io.BytesIO()
    manifest_lines = [f"scan_id: {scan.scan_id}", ""]
    written = 0
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for finding in scan.findings:
            yaml_body = to_sigma_yaml(finding)
            if yaml_body is None:
                continue
            name = f"{finding.id}.sigma.yml"
            zf.writestr(name, yaml_body)
            manifest_lines.append(
                f"- {finding.id}  [{finding.severity.value}]  {finding.title}"
            )
            written += 1
        if written == 0:
            raise HTTPException(
                status_code=409,
                detail="no findings in this scan have detection_guidance",
            )
        zf.writestr("MANIFEST.txt", "\n".join(manifest_lines) + "\n")

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="baselithcore-scan-{scan_id}.sigma.zip"'
            )
        },
    )
