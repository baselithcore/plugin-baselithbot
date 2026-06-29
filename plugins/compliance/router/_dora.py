"""DORA Art. 19 major-incident routes (consume ``core.incidents.dora``).

Read-only listing/detail for any authenticated reader; opening, classifying, and
advancing an incident through the initial-notification (4h) / intermediate (72h)
/ final (one month) milestones requires effective-admin. Console over
:func:`core.incidents.get_dora_incident_service`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth.types import AuthUser
from core.incidents import (
    DoraImpactAssessment,
    DoraIncidentNotFoundError,
    IncidentSeverity,
    get_dora_incident_service,
)

from ._guards import admin_principal, read_guard

router = APIRouter(prefix="/dora", tags=["compliance:dora"])


class OpenDoraRequest(BaseModel):
    """Payload to record a newly detected DORA incident."""

    title: str = Field(..., min_length=1, max_length=300)
    severity: IncidentSeverity = IncidentSeverity.HIGH
    description: str = ""
    affected_systems: List[str] = Field(default_factory=list)
    affected_clients: int = Field(default=0, ge=0)


class ClassifyRequest(BaseModel):
    """DORA major-incident classification criteria (Delegated Reg. 2024/1772)."""

    critical_services_affected: bool = False
    clients_affected: bool = False
    reputational_impact: bool = False
    service_downtime: bool = False
    geographical_spread: bool = False
    data_losses: bool = False
    economic_impact: bool = False
    major_override: Optional[bool] = None


def _payload(service: Any, incident: Any) -> Dict[str, Any]:
    data = incident.to_dict()
    data["milestones"] = [m.to_dict() for m in service.milestones(incident)]
    return data


@router.get("", dependencies=[Depends(read_guard)])
async def list_dora(status: Optional[str] = None) -> Dict[str, Any]:
    """List DORA incidents (optionally by status) with an overdue count."""
    service = get_dora_incident_service()
    from core.incidents import DoraIncidentStatus

    status_filter = DoraIncidentStatus(status) if status else None
    incidents = await service.list_incidents(status=status_filter)
    overdue = await service.overdue_milestones()
    return {
        "incidents": [_payload(service, i) for i in incidents],
        "overdue_count": len(overdue),
    }


@router.get("/overdue", dependencies=[Depends(read_guard)])
async def overdue_dora() -> Dict[str, Any]:
    """Return ``(incident, milestone)`` pairs whose deadline has passed."""
    service = get_dora_incident_service()
    overdue = await service.overdue_milestones()
    return {
        "overdue": [
            {"incident": inc.to_dict(), "milestone": ms.to_dict()}
            for inc, ms in overdue
        ]
    }


@router.get("/{incident_id}", dependencies=[Depends(read_guard)])
async def get_dora(incident_id: str) -> Dict[str, Any]:
    """Fetch a single DORA incident with its milestones."""
    service = get_dora_incident_service()
    incident = await service.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return _payload(service, incident)


@router.post("", status_code=201)
async def open_dora(
    body: OpenDoraRequest, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Record a newly detected DORA incident (unclassified)."""
    service = get_dora_incident_service()
    incident = await service.open_incident(
        body.title,
        body.severity,
        description=body.description,
        affected_systems=body.affected_systems,
        affected_clients=body.affected_clients,
    )
    return _payload(service, incident)


@router.post("/{incident_id}/classify")
async def classify_dora(
    incident_id: str, body: ClassifyRequest, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Classify the incident; if major, starts the 4h reporting clock."""
    service = get_dora_incident_service()
    assessment = DoraImpactAssessment(
        critical_services_affected=body.critical_services_affected,
        clients_affected=body.clients_affected,
        reputational_impact=body.reputational_impact,
        service_downtime=body.service_downtime,
        geographical_spread=body.geographical_spread,
        data_losses=body.data_losses,
        economic_impact=body.economic_impact,
    )
    try:
        incident = await service.classify(
            incident_id, assessment, major_override=body.major_override
        )
    except DoraIncidentNotFoundError:
        raise HTTPException(status_code=404, detail="incident not found")
    return _payload(service, incident)


_ADVANCE = {
    "initial-notification": "record_initial_notification",
    "intermediate-report": "record_intermediate_report",
    "final-report": "record_final_report",
    "close": "close_incident",
}


@router.post("/{incident_id}/{milestone}")
async def advance_dora(
    incident_id: str, milestone: str, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Stamp a DORA milestone (initial-notification / intermediate-report / final-report / close)."""
    method = _ADVANCE.get(milestone)
    if method is None:
        raise HTTPException(status_code=400, detail=f"unknown milestone: {milestone}")
    service = get_dora_incident_service()
    try:
        incident = await getattr(service, method)(incident_id)
    except DoraIncidentNotFoundError:
        raise HTTPException(status_code=404, detail="incident not found")
    return _payload(service, incident)


__all__ = ["router"]
