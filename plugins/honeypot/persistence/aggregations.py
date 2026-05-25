"""Advanced Aggregation Queries for Honeypot Persistence.

Complex database queries designed for intelligence dashboards:
- Top attackers with geo enrichment
- Attack category heatmaps (category × hour-of-day)
- CVE correlation trends over time
"""

from core.observability.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .database import get_connection

logger = get_logger(__name__)


async def get_top_attackers(
    days: int = 7,
    limit: int = 20,
    honeypot_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return top attacker IPs with event counts and geo data.

    Args:
        days: Lookback window in days.
        limit: Maximum number of attackers to return.
        honeypot_id: Optional filter for a specific honeypot.

    Returns:
        List of dicts with ``ip``, ``event_count``, ``first_seen``,
        ``last_seen``, ``protocols``, ``max_severity``, and ``geo``.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                conditions = ["timestamp >= %(cutoff)s"]
                params: Dict[str, Any] = {"cutoff": cutoff, "limit": limit}

                if honeypot_id:
                    conditions.append("honeypot_id = %(honeypot_id)s")
                    params["honeypot_id"] = honeypot_id

                where_clause = " AND ".join(conditions)

                query = f"""
                    SELECT
                        source_ip,
                        COUNT(*) AS event_count,
                        MIN(timestamp) AS first_seen,
                        MAX(timestamp) AS last_seen,
                        array_agg(DISTINCT protocol) AS protocols,
                        MAX(severity) AS max_severity,
                        (
                            SELECT meta->'geo'
                            FROM honeypot_events e2
                            WHERE e2.source_ip = honeypot_events.source_ip
                              AND e2.meta->'geo' IS NOT NULL
                              AND e2.meta->'geo' != 'null'::jsonb
                            ORDER BY e2.timestamp DESC
                            LIMIT 1
                        ) AS latest_geo
                    FROM honeypot_events
                    WHERE {where_clause}
                    GROUP BY source_ip
                    ORDER BY event_count DESC
                    LIMIT %(limit)s
                """  # nosec

                await cur.execute(query, params)
                rows = await cur.fetchall()

                results: List[Dict[str, Any]] = []
                for row in rows:
                    geo_data = row[6]
                    if isinstance(geo_data, str):
                        import json

                        try:
                            geo_data = json.loads(geo_data)
                        except Exception:
                            geo_data = None

                    results.append(
                        {
                            "ip": row[0],
                            "event_count": row[1],
                            "first_seen": row[2].isoformat() if row[2] else None,
                            "last_seen": row[3].isoformat() if row[3] else None,
                            "protocols": row[4] or [],
                            "max_severity": row[5],
                            "geo": geo_data,
                        }
                    )

                return results

    except Exception as e:
        logger.error(f"Failed to get top attackers: {e}")
        return []


async def get_attack_heatmap(
    days: int = 7,
    honeypot_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Generate attack category × hour-of-day heatmap matrix.

    Returns counts of events grouped by category and hour of day, suitable
    for rendering a heatmap chart on the frontend.

    Args:
        days: Lookback window in days.
        honeypot_id: Optional filter for a specific honeypot.

    Returns:
        List of dicts with ``category``, ``hour`` (0-23), and ``count``.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                conditions = ["timestamp >= %(cutoff)s"]
                params: Dict[str, Any] = {"cutoff": cutoff}

                if honeypot_id:
                    conditions.append("honeypot_id = %(honeypot_id)s")
                    params["honeypot_id"] = honeypot_id

                where_clause = " AND ".join(conditions)

                query = f"""
                    SELECT
                        category,
                        EXTRACT(HOUR FROM timestamp) AS hour,
                        COUNT(*) AS count
                    FROM honeypot_events
                    WHERE {where_clause}
                    GROUP BY category, hour
                    ORDER BY category, hour
                """  # nosec

                await cur.execute(query, params)
                rows = await cur.fetchall()

                return [
                    {
                        "category": row[0],
                        "hour": int(row[1]),
                        "count": row[2],
                    }
                    for row in rows
                ]

    except Exception as e:
        logger.error(f"Failed to get attack heatmap: {e}")
        return []


async def get_cve_trends(
    days: int = 30,
    limit: int = 10,
) -> Dict[str, Any]:
    """Analyze CVE correlation trends over time.

    Returns the most frequently matched CVEs and their daily occurrence
    counts for trend visualization.

    Args:
        days: Lookback window in days.
        limit: Maximum number of top CVEs to return.

    Returns:
        Dictionary with ``top_cves`` list and ``daily_counts`` time-series.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result: Dict[str, Any] = {
        "top_cves": [],
        "daily_counts": [],
        "total_correlations": 0,
    }

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Total correlations in period
                await cur.execute(
                    """
                    SELECT COUNT(*) FROM honeypot_events
                    WHERE timestamp >= %(cutoff)s
                      AND matched_cves IS NOT NULL
                      AND jsonb_array_length(matched_cves) > 0
                    """,
                    {"cutoff": cutoff},
                )
                row = await cur.fetchone()
                result["total_correlations"] = row[0] if row else 0

                # Top CVEs by frequency
                await cur.execute(
                    """
                    SELECT cve, COUNT(*) AS cnt
                    FROM honeypot_events,
                         jsonb_array_elements_text(matched_cves) AS cve
                    WHERE timestamp >= %(cutoff)s
                    GROUP BY cve
                    ORDER BY cnt DESC
                    LIMIT %(limit)s
                    """,
                    {"cutoff": cutoff, "limit": limit},
                )
                result["top_cves"] = [
                    {"cve_id": row[0], "count": row[1]} for row in await cur.fetchall()
                ]

                # Daily CVE correlation counts
                await cur.execute(
                    """
                    SELECT
                        date_trunc('day', timestamp) AS day,
                        COUNT(*) AS count
                    FROM honeypot_events
                    WHERE timestamp >= %(cutoff)s
                      AND matched_cves IS NOT NULL
                      AND jsonb_array_length(matched_cves) > 0
                    GROUP BY day
                    ORDER BY day
                    """,
                    {"cutoff": cutoff},
                )
                result["daily_counts"] = [
                    {
                        "date": row[0].isoformat() if row[0] else None,
                        "count": row[1],
                    }
                    for row in await cur.fetchall()
                ]

    except Exception as e:
        logger.error(f"Failed to get CVE trends: {e}")
        result["error"] = str(e)

    return result
