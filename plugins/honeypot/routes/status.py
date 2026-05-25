"""Status and control endpoints for Honeypot API.

Provides service status, statistics, and control endpoints.
"""

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from ..models import HoneypotStats, HoneypotStatus
from ..dependencies import get_coordinator_dependency

if TYPE_CHECKING:
    from ..swarm.coordinator import HoneypotSwarmCoordinator

router = APIRouter()


@router.get("/status", response_model=HoneypotStatus)
async def get_status(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get honeypot service status."""
    return coordinator.get_status()


@router.get("/stats", response_model=HoneypotStats)
async def get_stats(
    honeypot_id: str | None = None,
    from_db: bool = True,
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get aggregated attack statistics.

    Args:
        honeypot_id: Optional filter by honeypot ID
        from_db: If True, query stats directly from database (historical/persistent).
                 Default is True to ensure stats persist across restarts.
    """
    if from_db:
        return await coordinator.get_historical_stats(honeypot_id=honeypot_id)
    return coordinator.get_stats(honeypot_id=honeypot_id)


@router.post("/start")
async def start_honeypot(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Start honeypot services."""
    await coordinator.start()
    return {"status": "started", "message": "Honeypot services started"}


@router.post("/stop")
async def stop_honeypot(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Stop honeypot services."""
    await coordinator.stop()
    return {"status": "stopped", "message": "Honeypot services stopped"}


@router.get("/captor/stats")
async def get_captor_stats(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get HoneyDOC Captor module statistics.

    Returns comprehensive stats from all captor components:
    - Data capture: Network events, system activities
    - Data control: Blocked IPs, rules
    - Classification: Rule hits, matches
    - Flow control: Redirects, isolations
    - Stealth: Fingerprints, migrations
    """
    return coordinator.captor.get_stats()


@router.delete("/state")
async def reset_state(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Reset in-memory state (events, sessions, stats).

    This does NOT clear persistent storage (DB/Redis), only
    the in-memory buffers of the running coordinator.
    """
    await coordinator.reset_memory()
    return {"status": "reset", "message": "In-memory state cleared"}
