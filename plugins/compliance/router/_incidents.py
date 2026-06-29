"""NIS2 Art. 23 incident-reporting routes (consume ``core.incidents``).

Read-only listing/detail for any authenticated reader; opening an incident and
advancing it through the early-warning (24h) / notification (72h) / final-report
(one month) milestones requires effective-admin. The plugin holds no state — it
is a console over :func:`core.incidents.get_incident_service`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth.types import AuthUser
from core.incidents import (
    IncidentNotFoundError,
    IncidentSeverity,
    get_incident_service,
)

from ._guards import admin_principal, read_guard

router = APIRouter(prefix="/incidents", tags=["compliance:incidents"])


class OpenIncidentRequest(BaseModel):
    """Payload to record a newly detected NIS2 incident."""

    title: str = Field(..., min_length=1, max_length=300)
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    significant: bool = True
    description: str = ""
    affected_systems: List[str] = Field(default_factory=list)
    affected_subjects: int = Field(default=0, ge=0)


def _incident_payload(service: Any, incident: Any) -> Dict[str, Any]:
    """Serialise an incident together with its computed reporting milestones."""
    data = incident.to_dict()
    data["milestones"] = [m.to_dict() for m in service.milestones(incident)]
    return data


@router.get("", dependencies=[Depends(read_guard)])
async def list_incidents(status: Optional[str] = None) -> Dict[str, Any]:
    """List incidents (optionally by status) with an overdue-deadline count."""
    service = get_incident_service()
    from core.incidents import IncidentStatus

    status_filter = IncidentStatus(status) if status else None
    incidents = await service.list_incidents(status=status_filter)
    overdue = await service.overdue_milestones()
    return {
        "incidents": [_incident_payload(service, i) for i in incidents],
        "overdue_count": len(overdue),
    }


@router.get("/overdue", dependencies=[Depends(read_guard)])
async def overdue_incidents() -> Dict[str, Any]:
    """Return ``(incident, milestone)`` pairs whose deadline has passed."""
    service = get_incident_service()
    overdue = await service.overdue_milestones()
    return {
        "overdue": [
            {"incident": inc.to_dict(), "milestone": ms.to_dict()}
            for inc, ms in overdue
        ]
    }


@router.get("/{incident_id}", dependencies=[Depends(read_guard)])
async def get_incident(incident_id: str) -> Dict[str, Any]:
    """Fetch a single incident with its milestones."""
    service = get_incident_service()
    incident = await service.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return _incident_payload(service, incident)


@router.post("", status_code=201)
async def open_incident(
    body: OpenIncidentRequest, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Record a newly detected incident (starts the reporting clock)."""
    service = get_incident_service()
    incident = await service.open_incident(
        body.title,
        body.severity,
        significant=body.significant,
        description=body.description,
        affected_systems=body.affected_systems,
        affected_subjects=body.affected_subjects,
    )
    return _incident_payload(service, incident)


_ADVANCE = {
    "early-warning": "record_early_warning",
    "notification": "record_notification",
    "final-report": "record_final_report",
    "close": "close_incident",
}


@router.post("/{incident_id}/{milestone}")
async def advance_incident(
    incident_id: str, milestone: str, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Stamp a reporting milestone (early-warning / notification / final-report / close)."""
    method = _ADVANCE.get(milestone)
    if method is None:
        raise HTTPException(status_code=400, detail=f"unknown milestone: {milestone}")
    service = get_incident_service()
    try:
        incident = await getattr(service, method)(incident_id)
    except IncidentNotFoundError:
        raise HTTPException(status_code=404, detail="incident not found")
    return _incident_payload(service, incident)


__all__ = ["router"]
