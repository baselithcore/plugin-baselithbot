"""Time-Series Analytics for Honeypot Persistence.

SQL-powered time-bucketed aggregation for dashboard charts and trend analysis.
Uses PostgreSQL ``date_trunc()`` for efficient time-series queries.

Provides:
- Configurable time-bucketed event counts (hourly, daily, weekly)
- Group-by dimensions: protocol, severity, category, country
- Trend analysis: attack velocity, protocol distribution shifts
"""

from core.observability.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .database import get_connection

logger = get_logger(__name__)

# Valid time intervals for date_trunc
_VALID_INTERVALS = {"hour", "day", "week", "month"}

# Valid group-by dimensions
_VALID_GROUPS = {"protocol", "severity", "category", "country"}


async def get_timeseries(
    interval: str = "hour",
    honeypot_id: Optional[str] = None,
    days: int = 7,
    group_by: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return time-bucketed event counts for charting.

    Args:
        interval: Time bucket size — ``hour``, ``day``, ``week``, or ``month``.
        honeypot_id: Optional filter for a specific honeypot.
        days: Lookback window in days.
        group_by: Optional dimension to group by — ``protocol``, ``severity``,
                  ``category``, or ``country``.

    Returns:
        List of dicts, each with ``bucket`` (ISO timestamp), ``count``, and
        optionally the group-by dimension value.
    """
    if interval not in _VALID_INTERVALS:
        raise ValueError(
            f"Invalid interval '{interval}'. Must be one of {_VALID_INTERVALS}"
        )

    if group_by and group_by not in _VALID_GROUPS:
        raise ValueError(
            f"Invalid group_by '{group_by}'. Must be one of {_VALID_GROUPS}"
        )

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Build SELECT and GROUP BY
                if group_by == "country":
                    group_col = "meta->'geo'->>'country_code'"
                    group_alias = "country"
                elif group_by:
                    group_col = group_by
                    group_alias = group_by
                else:
                    group_col = None
                    group_alias = None

                select_parts = [
                    "date_trunc(%(interval)s, timestamp) AS bucket",
                    "COUNT(*) AS count",
                ]
                group_parts = ["bucket"]
                order_parts = ["bucket"]

                if group_col:
                    select_parts.append(f"{group_col} AS {group_alias}")
                    group_parts.append(group_alias)
                    order_parts.append(group_alias)

                # WHERE
                conditions = ["timestamp >= %(cutoff)s"]
                params: Dict[str, Any] = {
                    "interval": interval,
                    "cutoff": cutoff,
                }

                if honeypot_id:
                    conditions.append("honeypot_id = %(honeypot_id)s")
                    params["honeypot_id"] = honeypot_id

                where_clause = " AND ".join(conditions)

                query = f"""
                    SELECT {", ".join(select_parts)}
                    FROM honeypot_events
                    WHERE {where_clause}
                    GROUP BY {", ".join(group_parts)}
                    ORDER BY {", ".join(order_parts)}
                """  # nosec

                await cur.execute(query, params)
                rows = await cur.fetchall()

                results: List[Dict[str, Any]] = []
                for row in rows:
                    entry: Dict[str, Any] = {
                        "bucket": row[0].isoformat() if row[0] else None,
                        "count": row[1],
                    }
                    if group_alias and len(row) > 2:
                        entry[group_alias] = row[2]
                    results.append(entry)

                return results

    except Exception as e:
        logger.error(f"Failed to get timeseries data: {e}")
        return []


async def get_trends(days: int = 7) -> Dict[str, Any]:
    """Compute attack trends over a time window.

    Calculates:
    - Attack velocity (events/hour, compared to previous period)
    - Protocol distribution and shifts
    - New unique attacker IP rate
    - Severity escalation indicators

    Args:
        days: Lookback window in days.

    Returns:
        Dictionary with trend metrics.
    """
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)

    trends: Dict[str, Any] = {
        "period_days": days,
        "current_period": {
            "start": current_start.isoformat(),
            "end": now.isoformat(),
        },
        "attack_velocity": {
            "current_events_per_hour": 0.0,
            "previous_events_per_hour": 0.0,
            "change_pct": 0.0,
        },
        "protocol_distribution": {},
        "severity_distribution": {},
        "new_attacker_ips": 0,
        "top_emerging_categories": [],
    }

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # ---- Attack velocity ----
                await cur.execute(
                    "SELECT COUNT(*) FROM honeypot_events WHERE timestamp >= %(start)s",
                    {"start": current_start},
                )
                row = await cur.fetchone()
                current_count = row[0] if row else 0

                await cur.execute(
                    """
                    SELECT COUNT(*) FROM honeypot_events
                    WHERE timestamp >= %(prev_start)s AND timestamp < %(curr_start)s
                    """,
                    {"prev_start": previous_start, "curr_start": current_start},
                )
                row = await cur.fetchone()
                previous_count = row[0] if row else 0

                hours = days * 24
                current_rate = current_count / hours if hours > 0 else 0
                previous_rate = previous_count / hours if hours > 0 else 0
                change_pct = (
                    ((current_rate - previous_rate) / previous_rate * 100)
                    if previous_rate > 0
                    else 0.0
                )

                trends["attack_velocity"]["current_events_per_hour"] = round(
                    current_rate, 2
                )
                trends["attack_velocity"]["previous_events_per_hour"] = round(
                    previous_rate, 2
                )
                trends["attack_velocity"]["change_pct"] = round(change_pct, 1)

                # ---- Protocol distribution ----
                await cur.execute(
                    """
                    SELECT protocol, COUNT(*) FROM honeypot_events
                    WHERE timestamp >= %(start)s
                    GROUP BY protocol ORDER BY COUNT(*) DESC
                    """,
                    {"start": current_start},
                )
                trends["protocol_distribution"] = {
                    row[0]: row[1] for row in await cur.fetchall()
                }

                # ---- Severity distribution ----
                await cur.execute(
                    """
                    SELECT severity, COUNT(*) FROM honeypot_events
                    WHERE timestamp >= %(start)s
                    GROUP BY severity ORDER BY COUNT(*) DESC
                    """,
                    {"start": current_start},
                )
                trends["severity_distribution"] = {
                    row[0]: row[1] for row in await cur.fetchall()
                }

                # ---- New attacker IPs ----
                await cur.execute(
                    """
                    SELECT COUNT(DISTINCT source_ip)
                    FROM honeypot_events
                    WHERE timestamp >= %(curr_start)s
                      AND source_ip NOT IN (
                          SELECT DISTINCT source_ip
                          FROM honeypot_events
                          WHERE timestamp < %(curr_start)s
                      )
                    """,
                    {"curr_start": current_start},
                )
                row = await cur.fetchone()
                trends["new_attacker_ips"] = row[0] if row else 0

                # ---- Top emerging categories ----
                await cur.execute(
                    """
                    SELECT category, COUNT(*) AS cnt
                    FROM honeypot_events
                    WHERE timestamp >= %(start)s
                    GROUP BY category
                    ORDER BY cnt DESC
                    LIMIT 5
                    """,
                    {"start": current_start},
                )
                trends["top_emerging_categories"] = [
                    {"category": row[0], "count": row[1]}
                    for row in await cur.fetchall()
                ]

    except Exception as e:
        logger.error(f"Failed to compute trends: {e}")
        trends["error"] = str(e)

    return trends
