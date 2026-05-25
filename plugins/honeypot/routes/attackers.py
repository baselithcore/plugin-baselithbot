"""Attackers endpoint for Honeypot API.

Provides aggregated attacker data optimized for Globe visualization.
"""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List

from datetime import datetime, timedelta, timezone

from ..persistence.attackers import (
    get_unique_attackers,
    get_attackers_count,
    AttackerInfo,
)

router = APIRouter()


class AttackersResponse(BaseModel):
    """Response schema for attackers endpoint."""

    attackers: List[AttackerInfo]
    total: int


@router.get("/attackers", response_model=AttackersResponse)
async def list_attackers(
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
    limit: int = Query(500, ge=1, le=1000, description="Maximum attackers to return"),
    time_range: Optional[str] = Query(
        "24h", description="Time range (1h, 24h, 7d, 30d, all)"
    ),
):
    """Get unique attackers aggregated by IP.

    This endpoint is optimized for Globe visualization - it returns ALL unique
    attacker IPs with aggregated statistics, regardless of how many individual
    events they've generated.

    Args:
        honeypot_id: Optional filter by honeypot
        limit: Max attackers to return
        time_range: Time window for data (1h, 24h, 7d, 30d, all)

    Returns:
        List of unique attackers with geo data and stats
    """
    # Calculate since timestamp based on time_range
    since = None
    if time_range and time_range != "all":
        now = datetime.now(timezone.utc)
        if time_range == "1h":
            since = now - timedelta(hours=1)
        elif time_range == "24h":
            since = now - timedelta(hours=24)
        elif time_range == "7d":
            since = now - timedelta(days=7)
        elif time_range == "30d":
            since = now - timedelta(days=30)
        else:
            # Default fallback if invalid string
            since = now - timedelta(hours=24)

    attackers = await get_unique_attackers(
        honeypot_id=honeypot_id, limit=limit, since=since
    )
    total = await get_attackers_count(honeypot_id=honeypot_id, since=since)

    return AttackersResponse(attackers=attackers, total=total)
