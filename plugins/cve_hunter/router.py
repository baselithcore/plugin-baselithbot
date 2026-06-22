"""CVE Hunter API Router.

REST API endpoints for the CVE Hunter dashboard.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import AuthRole
from plugins.auth.dependencies import require_roles

from .dependencies import get_swarm_dependency
from .models import (
    AlertListResponse,
    CVEListResponse,
    CVEStats,
    DASTFinding,
    DASTScanResult,
    SASTFinding,
    SASTScanResult,
    SwarmStatus,
)
from .swarm import CVEHunterSwarm


def create_router() -> APIRouter:
    """Create CVE Hunter API router."""
    # CVE data is deployment-level security-ops intel (the public CVE catalog +
    # platform vulnerability alerts), not per-tenant customer data — restricted
    # to admins so non-admin tenant users never read it.
    router = APIRouter(
        prefix="",
        tags=["cve_hunter"],
        dependencies=[Depends(require_roles(AuthRole.ADMIN))],
    )

    @router.get("/status", response_model=SwarmStatus)
    async def get_status(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get CVE Hunter swarm status."""
        return swarm.get_status()

    @router.get("/cves", response_model=CVEListResponse)
    async def list_cves(
        severity: Optional[str] = Query(None, description="Filter by severity"),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get list of discovered CVEs."""

        all_cves = swarm.get_cves(severity=severity, limit=1000)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        items = all_cves[start:end]

        return CVEListResponse(
            items=items,
            total=len(all_cves),
            page=page,
            page_size=page_size,
            has_more=end < len(all_cves),
        )

    @router.get("/cves/{cve_id}")
    async def get_cve(
        cve_id: str,
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get details of a specific CVE."""
        cve = swarm._cve_cache.get(cve_id)
        if cve is None:
            raise HTTPException(status_code=404, detail=f"CVE {cve_id} not found")
        return cve

    @router.post("/cves/{cve_id}/analyze")
    async def analyze_cve_endpoint(
        cve_id: str,
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Trigger an AI analysis for a specific CVE."""
        cve = await swarm.analyze_cve(cve_id)
        if not cve:
            raise HTTPException(status_code=404, detail=f"CVE {cve_id} not found")
        return cve

    @router.post("/attack-chains/{chain_id}/analyze")
    async def analyze_chain_endpoint(
        chain_id: str,
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Trigger an AI analysis for a specific attack chain."""
        chain = await swarm.analyze_attack_chain(chain_id)
        if not chain:
            raise HTTPException(status_code=404, detail=f"Chain {chain_id} not found")
        return chain

    @router.get("/alerts", response_model=AlertListResponse)
    async def list_alerts(
        include_acknowledged: bool = Query(False),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get active vulnerability alerts."""
        alerts = swarm.get_alerts(include_acknowledged=include_acknowledged)
        unack = len([a for a in alerts if not a.acknowledged])

        return AlertListResponse(
            items=alerts,
            total=len(alerts),
            unacknowledged=unack,
        )

    @router.post("/alerts/{alert_id}/acknowledge")
    async def acknowledge_alert(
        alert_id: str,
        acknowledged_by: str = Query("user"),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Acknowledge an alert."""
        success = swarm.acknowledge_alert(alert_id, by=acknowledged_by)

        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {"status": "acknowledged", "alert_id": alert_id}

    @router.post("/scan")
    async def trigger_scan(
        days_back: int = Query(7, ge=1, le=30),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Trigger a manual CVE scan."""
        result = await swarm.run_full_scan(days_back=days_back)

        return {
            "scan_id": result.scan_id,
            "cves_found": result.cves_found,
            "new_cves": result.new_cves,
            "success": result.success,
            "duration_seconds": result.duration_seconds,
        }

    @router.get("/stats", response_model=CVEStats)
    async def get_stats(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get aggregated CVE statistics."""
        return swarm.get_stats()

    @router.get("/discovery/logs", response_model=List[Dict[str, Any]])
    async def get_discovery_logs(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get live discovery logs."""
        return swarm.get_discovery_logs()

    @router.get("/discovery/findings", response_model=List[Dict[str, Any]])
    async def get_discovery_findings(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get live discovery findings."""
        return swarm.get_findings()

    @router.get("/sast/findings", response_model=List[SASTFinding])
    async def get_sast_findings(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get recent SAST findings."""
        return swarm.get_sast_findings()

    @router.post("/sast/scan", response_model=SASTScanResult)
    async def run_sast_scan(
        paths: Optional[List[str]] = Query(None, description="Local paths to scan"),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Trigger a SAST scan on local repositories."""
        return await swarm.run_sast_scan(paths=paths)

    @router.post("/sast/findings/{finding_id}/feedback")
    async def record_sast_feedback(
        finding_id: str,
        outcome: str = Query(..., description="confirmed or false_positive"),
        source: str = Query("user"),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Record feedback for a SAST finding."""
        if outcome not in {"confirmed", "false_positive"}:
            raise HTTPException(status_code=400, detail="Invalid outcome")
        success = await swarm.record_sast_feedback(
            finding_id=finding_id, outcome=outcome, source=source
        )
        if not success:
            raise HTTPException(status_code=404, detail="Finding not found")
        return {"status": "recorded", "finding_id": finding_id, "outcome": outcome}

    @router.get("/dast/findings", response_model=List[DASTFinding])
    async def get_dast_findings(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get recent DAST findings."""
        return swarm.get_dast_findings()

    @router.post("/dast/findings/{finding_id}/feedback")
    async def record_dast_feedback(
        finding_id: str,
        outcome: str = Query(..., description="confirmed or false_positive"),
        source: str = Query("user"),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Record feedback for a DAST finding."""
        if outcome not in {"confirmed", "false_positive"}:
            raise HTTPException(status_code=400, detail="Invalid outcome")
        success = await swarm.record_dast_feedback(
            finding_id=finding_id, outcome=outcome, source=source
        )
        if not success:
            raise HTTPException(status_code=404, detail="Finding not found")
        return {"status": "recorded", "finding_id": finding_id, "outcome": outcome}

    @router.get("/findings/unified", response_model=List[Dict[str, Any]])
    async def get_unified_findings(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get unified findings across SAST/DAST/Discovery."""
        return swarm.get_unified_findings()

    @router.post("/findings/unified/{finding_id}/feedback")
    async def record_unified_feedback(
        finding_id: str,
        outcome: str = Query(..., description="confirmed or false_positive"),
        source: str = Query("user"),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Record feedback for a unified finding."""
        if outcome not in {"confirmed", "false_positive"}:
            raise HTTPException(status_code=400, detail="Invalid outcome")
        success = await swarm.record_unified_feedback(
            finding_id=finding_id, outcome=outcome, source=source
        )
        if not success:
            raise HTTPException(status_code=404, detail="Finding not found")
        return {"status": "recorded", "finding_id": finding_id, "outcome": outcome}

    @router.get("/findings/correlations", response_model=Dict[str, Any])
    async def get_finding_correlations(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get correlations between findings and CVEs/attack patterns."""
        return swarm.get_finding_correlations()

    @router.get("/feedback/audit", response_model=List[Dict[str, Any]])
    async def get_feedback_audit(
        limit: int = Query(50, ge=1, le=200),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get recent feedback audit events."""
        return swarm.get_feedback_audit(limit=limit)

    @router.post("/findings/correlations/cve/{correlation_id}/feedback")
    async def record_finding_correlation_feedback(
        correlation_id: str,
        outcome: str = Query(..., description="confirmed or false_positive"),
        source: str = Query("user"),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Record feedback for a finding-to-CVE correlation."""
        if outcome not in {"confirmed", "false_positive"}:
            raise HTTPException(status_code=400, detail="Invalid outcome")
        success = await swarm.record_finding_correlation_feedback(
            correlation_id=correlation_id, outcome=outcome, source=source
        )
        if not success:
            raise HTTPException(status_code=404, detail="Correlation not found")
        return {
            "status": "recorded",
            "correlation_id": correlation_id,
            "outcome": outcome,
        }

    @router.post("/findings/correlations/chain/{chain_id}/feedback")
    async def record_attack_chain_feedback(
        chain_id: str,
        outcome: str = Query(..., description="confirmed or false_positive"),
        source: str = Query("user"),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Record feedback for a finding-based attack chain."""
        if outcome not in {"confirmed", "false_positive"}:
            raise HTTPException(status_code=400, detail="Invalid outcome")
        success = await swarm.record_attack_chain_feedback(
            chain_id=chain_id, outcome=outcome, source=source
        )
        if not success:
            raise HTTPException(status_code=404, detail="Chain not found")
        return {"status": "recorded", "chain_id": chain_id, "outcome": outcome}

    @router.post("/dast/scan", response_model=DASTScanResult)
    async def run_dast_scan(
        targets: Optional[List[str]] = Query(None, description="Target base URLs"),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Trigger a DAST scan on configured targets."""
        return await swarm.run_dast_scan(targets=targets)

    @router.post("/analyze")
    async def analyze_situation(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Trigger an AI strategic analysis of the current situation."""
        report = await swarm.analyze_situation()
        return {"report": report}

    @router.get("/attack-chains", response_model=List[Dict[str, Any]])
    async def get_attack_chains(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get detected attack chains from correlated CVEs.

        Returns CVE combinations that form multi-stage attack patterns.
        """
        return await swarm.get_attack_chains()

    @router.get("/correlations", response_model=List[Dict[str, Any]])
    async def get_correlations(
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Get CVE correlations (common CWE, same product, etc.).

        Useful for understanding relationships between vulnerabilities.
        """
        return await swarm.get_correlations()

    @router.post("/correlations/{correlation_id}/feedback")
    async def record_cve_correlation_feedback(
        correlation_id: str,
        outcome: str = Query(..., description="confirmed or false_positive"),
        source: str = Query("user"),
        swarm: CVEHunterSwarm = Depends(get_swarm_dependency),
    ):
        """Record feedback for a CVE correlation."""
        if outcome not in {"confirmed", "false_positive"}:
            raise HTTPException(status_code=400, detail="Invalid outcome")
        success = await swarm.record_cve_correlation_feedback(
            correlation_id=correlation_id, outcome=outcome, source=source
        )
        if not success:
            raise HTTPException(status_code=404, detail="Correlation not found")
        return {
            "status": "recorded",
            "correlation_id": correlation_id,
            "outcome": outcome,
        }

    return router
