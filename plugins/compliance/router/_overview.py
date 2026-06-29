"""Compliance posture overview — one aggregation call for the dashboard.

Rolls up the four regulatory domains into a single read so the console landing
page can show the compliance posture at a glance: incident counts + overdue
deadlines (NIS2 + DORA), the nearest upcoming regulatory deadlines (the core GRC
signal), the DORA third-party concentration view, the GDPR provider count, and
the AI-Act disclosure status. Read-only; open to any authenticated reader.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from core.incidents import (
    IncidentStatus,
    get_dora_incident_service,
    get_incident_service,
)
from core.incidents.dora import DoraIncidentStatus
from core.privacy import get_data_subject_service
from core.thirdparty import get_register
from core.transparency import get_transparency_service

from ._guards import read_guard

router = APIRouter(tags=["compliance:overview"])

# How many nearest deadlines to surface on the dashboard.
_DEADLINE_LIMIT = 8


def _deadline_row(regime: str, incident: Any, milestone: Any) -> Dict[str, Any]:
    return {
        "regime": regime,
        "incident_id": incident.id,
        "title": incident.title,
        "kind": milestone.kind.value,
        "due_at": milestone.due_at.isoformat(),
        "overdue": milestone.is_overdue(),
    }


@router.get("/overview", dependencies=[Depends(read_guard)])
async def overview() -> Dict[str, Any]:
    """Aggregate the four compliance domains for the dashboard."""
    nis2 = get_incident_service()
    dora = get_dora_incident_service()
    register = get_register()
    transparency = get_transparency_service()

    nis2_all = await nis2.list_incidents()
    nis2_overdue = await nis2.overdue_milestones()
    dora_all = await dora.list_incidents()
    dora_overdue = await dora.overdue_milestones()

    # Collect every unsubmitted milestone (upcoming + overdue) across regimes,
    # sorted by due date — the reporting clock the operator must not miss.
    pending: List[tuple[Any, Any, str]] = []
    for inc in nis2_all:
        if inc.status == IncidentStatus.CLOSED:
            continue
        for ms in nis2.milestones(inc):
            if not ms.is_submitted:
                pending.append((inc, ms, "nis2"))
    for inc in dora_all:
        if inc.status == DoraIncidentStatus.CLOSED:
            continue
        for ms in dora.milestones(inc):
            if not ms.is_submitted:
                pending.append((inc, ms, "dora"))
    pending.sort(key=lambda t: t[1].due_at)
    deadlines = [_deadline_row(regime, inc, ms) for inc, ms, regime in pending[:_DEADLINE_LIMIT]]

    concentration = await register.concentration_summary()
    providers = [p.name for p in get_data_subject_service().registry.all()]

    return {
        "nis2": {
            "total": len(nis2_all),
            "open": len([i for i in nis2_all if i.status != IncidentStatus.CLOSED]),
            "overdue": len(nis2_overdue),
        },
        "dora": {
            "total": len(dora_all),
            "open": len([i for i in dora_all if i.status != DoraIncidentStatus.CLOSED]),
            "overdue": len(dora_overdue),
            "major": len([i for i in dora_all if i.is_major]),
        },
        "dsr": {"providers": len(providers)},
        "thirdparty": {
            "providers": concentration["providers"],
            "arrangements": concentration["arrangements"],
            "critical": concentration["critical_or_important_arrangements"],
            "flags": len(concentration["concentration_flags"]),
        },
        "transparency": {
            "enabled": transparency.enabled,
            "should_disclose": transparency.should_disclose(),
        },
        "deadlines": deadlines,
    }


__all__ = ["router"]
