"""GeoIP endpoints for Honeypot API.

Provides endpoints for IP geolocation and attack visualization.
"""

from typing import TYPE_CHECKING, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_coordinator_dependency

if TYPE_CHECKING:
    from ..swarm.coordinator import HoneypotSwarmCoordinator

router = APIRouter()


@router.get("/geo/lookup/{ip}")
async def geo_lookup(ip: str):
    """Lookup geographic location for an IP with normalized display."""
    from ..geo import get_geo_service
    from ..utils import get_ip_type, is_private_or_local, normalize_ip_display

    geo_service = get_geo_service()
    result = await geo_service.lookup(ip)

    # Build response with normalized IP info
    response = {
        "raw_ip": ip,
        "display_ip": normalize_ip_display(ip),
        "ip_type": get_ip_type(ip),
        "is_private": is_private_or_local(ip),
        "geo": result.model_dump() if result else None,
    }

    return response


@router.get("/geo/heatmap")
async def get_geo_heatmap(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get attack heatmap data by country."""
    from ..geo import AttackHeatmapGenerator, get_geo_service

    heatmap = AttackHeatmapGenerator(get_geo_service())

    # Add recent attacks to heatmap
    events_data = (
        await coordinator.get_events(page_size=100)
        if hasattr(coordinator, "get_events")
        else {}
    )
    events = events_data.get("items", [])

    for event in events[:50]:  # Limit to prevent rate limiting
        if hasattr(event, "source_ip"):
            await heatmap.add_attack(event.source_ip)

    return {
        "heatmap": heatmap.get_heatmap_data(),
        "top_countries": heatmap.get_top_countries(10),
    }


@router.post("/geo/bulk-lookup")
async def bulk_geo_lookup(ips: List[str]):
    """Bulk lookup geographic locations."""
    from ..geo import get_geo_service

    if len(ips) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 IPs per request")

    geo_service = get_geo_service()
    results = await geo_service.bulk_lookup(ips)
    return {ip: geo.model_dump() if geo else None for ip, geo in results.items()}


@router.get("/geo/attacks")
async def get_geo_attacks(
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get attack data with geo coordinates for map visualization.

    Returns attack flows with source/target coordinates for
    animated arc visualization on a world map.
    """
    from ..stream import GeoAttackData

    # Get events with optional filtering
    events_data = await coordinator.get_events(
        page=1,
        page_size=limit,
        severity=severity,
    )
    events = events_data.get("items", [])

    # Process with geo data
    geo_processor = GeoAttackData()
    result = await geo_processor.process_events(events)

    return result
