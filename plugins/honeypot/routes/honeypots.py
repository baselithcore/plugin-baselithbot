"""Honeypot registry endpoints.

Provides endpoints for listing and querying honeypots.
"""

from typing import TYPE_CHECKING, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models import EventListResponse, HoneypotInfo
from ..dependencies import get_coordinator_dependency

if TYPE_CHECKING:
    from ..swarm.coordinator import HoneypotSwarmCoordinator

router = APIRouter()


@router.get("/honeypots", response_model=List[HoneypotInfo])
async def list_honeypots(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get list of all configured honeypots with stats from database."""
    return await coordinator.get_honeypots()


@router.get("/honeypots/{honeypot_id}", response_model=HoneypotInfo)
async def get_honeypot(
    honeypot_id: str,
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get specific honeypot details and stats from database."""
    honeypot = await coordinator.get_honeypot(honeypot_id)
    if not honeypot:
        raise HTTPException(status_code=404, detail=f"Honeypot {honeypot_id} not found")
    return honeypot


@router.get("/honeypots/{honeypot_id}/events", response_model=EventListResponse)
async def get_honeypot_events(
    honeypot_id: str,
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by attack category"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get events for a specific honeypot."""

    # Verify honeypot exists
    honeypot = await coordinator.get_honeypot(honeypot_id)
    if not honeypot:
        raise HTTPException(status_code=404, detail=f"Honeypot {honeypot_id} not found")

    events_data = await coordinator.get_events(
        page=page,
        page_size=page_size,
        protocol=protocol,
        severity=severity,
        category=category,
        source_ip=source_ip,
        honeypot_id=honeypot_id,
    )

    return EventListResponse(
        items=events_data["items"],
        total=events_data["total"],
        page=events_data["page"],
        page_size=events_data["page_size"],
        has_more=events_data["page"] < events_data["total_pages"],
    )


@router.get("/honeypots/{honeypot_id}/attackers")
async def get_honeypot_attackers(
    honeypot_id: str,
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get unique attackers targeting this honeypot."""

    # Verify honeypot exists
    honeypot = await coordinator.get_honeypot(honeypot_id)
    if not honeypot:
        raise HTTPException(status_code=404, detail=f"Honeypot {honeypot_id} not found")

    # Get all events for this honeypot
    events_data = await coordinator.get_events(
        page=1,
        page_size=10000,  # Get all
        honeypot_id=honeypot_id,
    )

    # Aggregate by attacker IP
    attackers = {}
    for event in events_data["items"]:
        ip = event.source_ip
        if ip not in attackers:
            attackers[ip] = {
                "ip": ip,
                "event_count": 0,
                "country_code": event.geo.country_code if event.geo else None,
                "country": event.geo.country if event.geo else None,
                "protocols": set(),
                "severities": set(),
                "first_seen": event.timestamp,
                "last_seen": event.timestamp,
            }
        attackers[ip]["event_count"] += 1
        attackers[ip]["protocols"].add(event.protocol.value)
        attackers[ip]["severities"].add(event.severity.value)
        if event.timestamp < attackers[ip]["first_seen"]:
            attackers[ip]["first_seen"] = event.timestamp
        if event.timestamp > attackers[ip]["last_seen"]:
            attackers[ip]["last_seen"] = event.timestamp

    # Convert sets to lists for JSON serialization
    result = []
    for attacker in attackers.values():
        attacker["protocols"] = list(attacker["protocols"])
        attacker["severities"] = list(attacker["severities"])
        result.append(attacker)

    # Sort by event_count desc
    result.sort(key=lambda x: x["event_count"], reverse=True)

    return {
        "honeypot_id": honeypot_id,
        "attackers": result,
        "total": len(result),
    }
