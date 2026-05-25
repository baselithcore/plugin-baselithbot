"""Memory and reputation endpoints for Honeypot API.

Provides endpoints for IP reputation and pattern statistics.
"""

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_coordinator_dependency

if TYPE_CHECKING:
    from ..swarm.coordinator import HoneypotSwarmCoordinator

router = APIRouter()


@router.get("/memory/ip-reputation/{ip}")
async def get_ip_reputation(
    ip: str,
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get reputation data for an IP."""
    if hasattr(coordinator, "_memory") and coordinator._memory:
        rep = coordinator._memory.get_ip_reputation(ip)
        if rep:
            return rep
    raise HTTPException(status_code=404, detail=f"No reputation data for {ip}")


@router.get("/memory/high-threat-ips")
async def get_high_threat_ips(
    threshold: float = Query(50.0),
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get IPs with high threat scores."""
    if hasattr(coordinator, "_memory") and coordinator._memory:
        return coordinator._memory.get_high_threat_ips(threshold=threshold)
    return []


@router.get("/memory/pattern-stats")
async def get_memory_pattern_stats(
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get pattern statistics from memory."""
    if hasattr(coordinator, "_memory") and coordinator._memory:
        return coordinator._memory.get_pattern_stats()
    return {}
