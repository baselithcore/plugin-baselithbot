"""Scan trigger + status endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from core.di.container import ServiceRegistry
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.dependencies import (
    get_red_agent,
    require_security_operator,
    require_viewer,
)
from plugins.red_agent.guardrails import GuardrailViolation
from plugins.red_agent.models import (
    ScanIntensity,
    ScanRequest,
    ScanResult,
    ScanStatus,
    Target,
    TargetType,
)
from plugins.red_agent.persistence import EngagementPersistence

_TERMINAL_SCAN_STATES = {ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED}

router = APIRouter(prefix="/scans", tags=["red-agent"])


class ScanCreate(BaseModel):
    target: Target
    engagement_id: UUID | None = None
    scanners: list[str]
    intensity: ScanIntensity = ScanIntensity.PASSIVE
    bug_bounty_program: str | None = None
    notes: str | None = None


@router.post(
    "", status_code=status.HTTP_202_ACCEPTED, dependencies=[require_security_operator()]
)
async def create_scan(
    body: ScanCreate,
    agent: RedAgent = Depends(get_red_agent),
) -> dict[str, str]:
    if body.engagement_id is not None:
        store = (
            ServiceRegistry.get(EngagementPersistence)
            if ServiceRegistry.has(EngagementPersistence)
            else None
        )
        if store is None or await store.get(body.engagement_id) is None:
            raise HTTPException(404, "engagement not found")
    request = ScanRequest(
        target=body.target,
        engagement_id=body.engagement_id,
        scanners=body.scanners,
        intensity=body.intensity,
        requested_by="api-caller",
        bug_bounty_program=body.bug_bounty_program,
        notes=body.notes,
    )
    try:
        scan_id = await agent.submit_scan(request)
    except GuardrailViolation as e:
        raise HTTPException(
            status_code=400, detail={"code": e.code, "message": e.message}
        )
    return {"scan_id": str(scan_id)}


@router.get("", dependencies=[require_viewer()])
async def list_scans(
    agent: RedAgent = Depends(get_red_agent),
    status_filter: str | None = None,
    engagement_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    from plugins.red_agent.models import ScanStatus

    sf = ScanStatus(status_filter) if status_filter else None
    rows = await agent.persistence.list_scans(
        status_filter=sf, engagement_id=engagement_id, limit=limit, offset=offset
    )
    for r in rows:
        r["id"] = str(r["id"])
    return rows


@router.get("/{scan_id}", dependencies=[require_viewer()])
async def get_scan(
    scan_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
) -> ScanResult:
    result = await agent.get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return result


@router.post(
    "/quick",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[require_security_operator()],
)
async def quick_scan(
    target_value: str,
    agent: RedAgent = Depends(get_red_agent),
) -> dict[str, str]:
    Target(type=TargetType.URL, value=target_value)
    scan_id = await agent.quick_scan(target_value, requested_by="api-caller")
    return {"scan_id": str(scan_id)}


@router.post(
    "/{scan_id}/cancel",
    dependencies=[require_security_operator()],
)
async def cancel_scan(
    scan_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
) -> dict[str, str]:
    ok = await agent.cancel_scan(scan_id, actor="api-caller")
    if not ok:
        raise HTTPException(409, "scan not running or already terminal")
    return {"status": "cancelled", "scan_id": str(scan_id)}


@router.delete(
    "/{scan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    dependencies=[require_security_operator()],
)
async def delete_scan(
    scan_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
) -> None:
    """Permanently delete a scan and its findings.

    Only allowed when the scan has reached a terminal state — running or
    pending scans must be cancelled first via ``POST /scans/{id}/cancel``.
    Findings cascade via the FK on ``red_agent_findings.scan_id``.
    """
    existing = await agent.persistence.get_scan(scan_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="scan not found")
    if existing.status not in _TERMINAL_SCAN_STATES:
        raise HTTPException(
            status_code=409,
            detail="scan is not in a terminal state — cancel it first",
        )
    deleted = await agent.persistence.delete_scan(scan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="scan not found")
    await agent.audit.record(
        scan_id=scan_id,
        actor="api-caller",
        event="scan.deleted",
        payload={"prior_status": existing.status.value},
    )
