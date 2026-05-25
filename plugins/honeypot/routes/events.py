"""Event endpoints for Honeypot API.

Provides endpoints for listing and analyzing attack events.
"""

from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.observability.logging import get_logger
from ..models import EventListResponse
from ..dependencies import get_coordinator_dependency

if TYPE_CHECKING:
    from ..swarm.coordinator import HoneypotSwarmCoordinator

router = APIRouter()


@router.get("/events", response_model=EventListResponse)
async def list_events(
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by attack category"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
    country: Optional[str] = Query(
        None, description="Filter by country code (ISO 2-letter)"
    ),
    is_bot: Optional[bool] = Query(None, description="Filter by bot status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get list of attack events."""
    events_data = await coordinator.get_events(
        page=page,
        page_size=page_size,
        protocol=protocol,
        severity=severity,
        category=category,
        source_ip=source_ip,
        honeypot_id=honeypot_id,
        country=country,
        is_bot=is_bot,
    )

    return EventListResponse(
        items=events_data["items"],
        total=events_data["total"],
        page=events_data["page"],
        page_size=events_data["page_size"],
        has_more=events_data["page"] < events_data["total_pages"],
    )


@router.get("/events/{event_id}")
async def get_event(
    event_id: str,
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get details of a specific attack event."""
    event = await coordinator.get_event_full(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return event


@router.post("/events/{event_id}/analyze")
async def analyze_event(
    event_id: str,
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Trigger AI analysis for a specific attack event."""

    logger = get_logger(__name__)
    logger.info(f"Received analysis request for event {event_id}")

    result = await coordinator.analyze_event(event_id)

    logger.info(f"Analysis result for {event_id}: {bool(result)}")
    if not result:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return result


@router.get("/patterns")
async def get_attack_patterns(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get detected attack patterns and their frequencies."""
    return coordinator.get_attack_patterns()
