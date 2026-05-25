"""Logs endpoints for Honeypot API.

Provides endpoints for retrieving discovery logs.
"""

from typing import TYPE_CHECKING, List

from core.observability.logging import get_logger
from fastapi import APIRouter, Depends, Query

from ..models import DiscoveryLog
from ..dependencies import get_coordinator_dependency

if TYPE_CHECKING:
    from ..swarm.coordinator import HoneypotSwarmCoordinator

logger = get_logger(__name__)

router = APIRouter()


@router.get("/logs", response_model=List[DiscoveryLog])
async def get_logs(
    limit: int = Query(100, ge=1, le=1000),
    coordinator: "HoneypotSwarmCoordinator" = Depends(get_coordinator_dependency),
):
    """Get recent discovery logs."""
    logs = await coordinator.get_discovery_logs(limit=limit)
    logger.info(f"Returning {len(logs)} discovery logs via API")
    return logs
