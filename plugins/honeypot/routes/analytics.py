"""Analytics endpoints for Honeypot API.

Provides time-series, trend, heatmap, and retention management endpoints
for the intelligence dashboard.
"""

from typing import Optional

from fastapi import APIRouter, Query

from ..persistence import (
    apply_retention_policy,
    get_retention_status,
    get_timeseries,
    get_trends,
    get_top_attackers,
    get_attack_heatmap,
    get_cve_trends,
)

router = APIRouter(tags=["analytics"])


# =========================================================================
# Time-Series & Trends
# =========================================================================


@router.get("/analytics/timeseries")
async def timeseries(
    interval: str = Query("hour", description="Time bucket: hour, day, week, month"),
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
    days: int = Query(7, ge=1, le=365, description="Lookback window in days"),
    group_by: Optional[str] = Query(
        None, description="Group by: protocol, severity, category, country"
    ),
):
    """Get time-bucketed event counts for charting."""
    return await get_timeseries(
        interval=interval,
        honeypot_id=honeypot_id,
        days=days,
        group_by=group_by,
    )


@router.get("/analytics/trends")
async def trends(
    days: int = Query(7, ge=1, le=365, description="Lookback window in days"),
):
    """Get attack trend analysis (velocity, protocol shifts, new IPs)."""
    return await get_trends(days=days)


@router.get("/analytics/heatmap")
async def heatmap(
    days: int = Query(7, ge=1, le=365, description="Lookback window in days"),
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
):
    """Get attack category × hour-of-day heatmap."""
    return await get_attack_heatmap(days=days, honeypot_id=honeypot_id)


@router.get("/analytics/top-attackers")
async def top_attackers(
    days: int = Query(7, ge=1, le=365, description="Lookback window in days"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
):
    """Get top attacker IPs with geo enrichment."""
    return await get_top_attackers(days=days, limit=limit, honeypot_id=honeypot_id)


@router.get("/analytics/cve-trends")
async def cve_trends_endpoint(
    days: int = Query(30, ge=1, le=365, description="Lookback window in days"),
    limit: int = Query(10, ge=1, le=50, description="Max top CVEs"),
):
    """Get CVE correlation trends over time."""
    return await get_cve_trends(days=days, limit=limit)


# =========================================================================
# Retention Management
# =========================================================================


@router.get("/admin/retention/status")
async def retention_status():
    """Get current retention policy status and table statistics."""
    return await get_retention_status()


@router.post("/admin/retention/run")
async def run_retention(
    max_age_days: int = Query(90, ge=1, description="Max age in days"),
    max_rows: int = Query(1_000_000, ge=1000, description="Max rows to retain"),
):
    """Manually trigger retention policy execution."""
    return await apply_retention_policy(max_age_days=max_age_days, max_rows=max_rows)
