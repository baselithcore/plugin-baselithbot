"""Auto-remediation endpoint: open a fix-PR for a finding."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.dependencies import get_red_agent, require_security_operator
from plugins.red_agent.integrations import AutoRemediationService
from plugins.red_agent.persistence import RedAgentPersistence

logger = get_logger(__name__)

router = APIRouter(prefix="/findings", tags=["red-agent"])


def _get_service() -> AutoRemediationService:
    svc = ServiceRegistry.get(AutoRemediationService)
    if svc is None or not svc.enabled:
        raise HTTPException(status_code=404, detail="auto-remediation disabled")
    return svc


def _get_persistence() -> RedAgentPersistence:
    p = ServiceRegistry.get(RedAgentPersistence)
    if p is None or not p.available:
        raise HTTPException(status_code=503, detail="persistence unavailable")
    return p


def _get_audit() -> AuditLogger:
    a = ServiceRegistry.get(AuditLogger)
    if a is None:
        raise HTTPException(status_code=503, detail="audit unavailable")
    return a


@router.post("/{finding_id}/auto-remediate", dependencies=[require_security_operator()])
async def auto_remediate(
    finding_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
    service: AutoRemediationService = Depends(_get_service),
    persistence: RedAgentPersistence = Depends(_get_persistence),
    audit: AuditLogger = Depends(_get_audit),
) -> dict[str, Any]:
    """Open a fix-PR on the upstream repository for the matching finding.

    Operator-triggered. The finding must carry
    ``evidence.osv_fixed_in`` (populated by the OSV.dev enricher) plus
    ``evidence.repo_owner`` / ``evidence.repo_name`` so the service knows
    which GitHub repository to write to.
    """
    finding = await _resolve_finding(agent, finding_id)
    result = await service.remediate(finding)
    await audit.record(
        scan_id=None,
        actor="auto_remediation",
        event="finding.auto_remediation",
        payload={
            "finding_id": str(finding_id),
            "success": result.success,
            "pr_url": result.pr_url,
            "branch": result.branch,
            "fixed_version": result.fixed_version,
            "error": result.error,
        },
    )
    if result.success and result.pr_url:
        try:
            await persistence.update_finding_external_ref(finding_id, result.pr_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "red_agent.autopr.update_external_ref_failed",
                extra={"finding_id": str(finding_id), "err": str(exc)},
            )
    if not result.success:
        raise HTTPException(
            status_code=422,
            detail=result.error or "auto_remediation_failed",
        )
    return {
        "finding_id": str(finding_id),
        "pr_url": result.pr_url,
        "branch": result.branch,
        "fixed_version": result.fixed_version,
    }


async def _resolve_finding(agent: RedAgent, finding_id: UUID) -> Any:
    """Pull the finding from the most recent scan that contains it.

    The persistence layer keeps findings under their parent scan id, so
    we cannot ``get`` by finding-id alone — we walk recent scans until
    a match shows up. Sufficient for the operator-triggered use case;
    a dedicated ``find_by_id`` query is a future enhancement.
    """
    persistence: RedAgentPersistence = ServiceRegistry.get(RedAgentPersistence)  # type: ignore[assignment]
    if persistence is None:
        raise HTTPException(status_code=503, detail="persistence unavailable")
    findings = await persistence.list_findings(limit=1000)
    for f in findings:
        if f.id == finding_id:
            return f
    del agent
    raise HTTPException(status_code=404, detail="finding not found")
