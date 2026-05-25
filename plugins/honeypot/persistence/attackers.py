"""
Attacker persistence logic for Honeypot.

Provides aggregated attacker data for Globe visualization.
"""

from core.observability.logging import get_logger
from typing import Optional, List

from .database import get_connection
from pydantic import BaseModel
from datetime import datetime, timezone

logger = get_logger(__name__)


class AttackerInfo(BaseModel):
    """Aggregated attacker information."""

    ip: str
    country_code: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    event_count: int = 0
    first_seen: datetime
    last_seen: datetime
    protocols: List[str] = []
    max_severity: str = "info"
    is_bot: bool = False


async def get_unique_attackers(
    honeypot_id: Optional[str] = None,
    limit: int = 500,
    since: Optional[datetime] = None,
) -> List[AttackerInfo]:
    """Get unique attackers aggregated by IP.

    This is optimized for Globe visualization - returns all unique IPs
    with aggregated statistics, regardless of how many events they've created.

    Args:
        honeypot_id: Optional filter by honeypot
        limit: Maximum number of attackers to return
        since: Optional filter for attacks since this time

    Returns:
        List of AttackerInfo objects
    """
    try:
        async with get_connection() as conn:
            params: dict = {"limit": limit}
            where_clause = "1=1"
            # Default geo_where_clause needs to work with the AND that follows
            geo_where_clause = ""

            if honeypot_id:
                where_clause += " AND honeypot_id = %(honeypot_id)s"
                geo_where_clause += "e2.honeypot_id = %(honeypot_id)s AND "
                params["honeypot_id"] = honeypot_id

            if since:
                where_clause += " AND timestamp >= %(since)s"
                # For geo query, we want the location of the most recent event within the window
                geo_where_clause += "e2.timestamp >= %(since)s AND "
                params["since"] = since

            async with conn.cursor() as cur:
                # Aggregate attackers by IP with stats
                query = f"""
                    SELECT 
                        source_ip,
                        COUNT(*) as event_count,
                        MIN(timestamp) as first_seen,
                        MAX(timestamp) as last_seen,
                        array_agg(DISTINCT protocol) as protocols,
                        MAX(CASE 
                            WHEN severity = 'critical' THEN 5
                            WHEN severity = 'high' THEN 4
                            WHEN severity = 'medium' THEN 3
                            WHEN severity = 'low' THEN 2
                            ELSE 1
                        END) as max_severity_rank,
                        -- Check if any event was flagged as bot
                        bool_or(is_bot) as is_bot,
                        -- Get geo from most recent event (filtered by honeypot if specified)
                        (SELECT meta->'geo' FROM honeypot_events e2 
                         WHERE {geo_where_clause} e2.source_ip = honeypot_events.source_ip 
                         ORDER BY e2.timestamp DESC LIMIT 1) as geo
                    FROM honeypot_events
                    WHERE {where_clause}
                    GROUP BY source_ip
                    ORDER BY MAX(timestamp) DESC
                    LIMIT %(limit)s
                """  # nosec - where_clause is built from validated inputs

                await cur.execute(query, params)
                rows = await cur.fetchall()

            attackers = []
            severity_map = {5: "critical", 4: "high", 3: "medium", 2: "low", 1: "info"}

            for row in rows:
                geo_data = row[7] or {}

                # Ensure timestamps are timezone-aware
                first_seen = row[2]
                last_seen = row[3]
                if first_seen and first_seen.tzinfo is None:
                    first_seen = first_seen.replace(tzinfo=timezone.utc)
                if last_seen and last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)

                attackers.append(
                    AttackerInfo(
                        ip=row[0],
                        event_count=row[1],
                        first_seen=first_seen,
                        last_seen=last_seen,
                        protocols=row[4] or [],
                        max_severity=severity_map.get(row[5], "info"),
                        is_bot=row[6] or False,
                        country_code=geo_data.get("country_code"),
                        country=geo_data.get("country"),
                        city=geo_data.get("city"),
                    )
                )

            return attackers

    except Exception as e:
        logger.error(f"Failed to get unique attackers: {e}")
        return []


async def get_attackers_count(
    honeypot_id: Optional[str] = None,
    since: Optional[datetime] = None,
) -> int:
    """Get total count of unique attackers.

    Args:
        honeypot_id: Optional filter by honeypot
        since: Optional filter for attacks since this time

    Returns:
        Count of unique IPs
    """
    try:
        async with get_connection() as conn:
            params: dict = {}
            where_clause = "1=1"

            if honeypot_id:
                where_clause += " AND honeypot_id = %(honeypot_id)s"
                params["honeypot_id"] = honeypot_id

            if since:
                where_clause += " AND timestamp >= %(since)s"
                params["since"] = since

            async with conn.cursor() as cur:
                query = f"""
                    SELECT COUNT(DISTINCT source_ip) 
                    FROM honeypot_events 
                    WHERE {where_clause}
                """  # nosec
                await cur.execute(query, params)
                row = await cur.fetchone()
                return row[0] if row else 0

    except Exception as e:
        logger.error(f"Failed to count attackers: {e}")
        return 0
