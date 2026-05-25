"""Finding triage endpoints (lifecycle transitions)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from plugins.red_agent.agent import RedAgent
from plugins.red_agent.dependencies import get_red_agent, require_security_operator
from plugins.red_agent.models import FindingTriageUpdate

router = APIRouter(prefix="/findings", tags=["red-agent"])


@router.patch("/{finding_id}", dependencies=[require_security_operator()])
async def update_finding(
    finding_id: UUID,
    body: FindingTriageUpdate,
    agent: RedAgent = Depends(get_red_agent),
) -> dict[str, str]:
    ok = await agent.persistence.update_finding_triage(
        finding_id, body, actor="api-caller"
    )
    if not ok:
        raise HTTPException(404, "finding not found or no fields to update")
    return {"finding_id": str(finding_id), "status": "updated"}
