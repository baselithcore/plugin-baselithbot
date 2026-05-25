"""
Statistics aggregation logic for Honeypot.
"""

from core.observability.logging import get_logger
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone
from .database import get_connection

logger = get_logger(__name__)


async def get_stats(
    honeypot_id: Optional[str] = None,
    days: int = 7,
) -> Dict:
    """Get aggregated statistics from DB.

    Args:
        honeypot_id: Optional filter by honeypot
        days: Number of days to include in stats

    Returns:
        Dictionary with aggregated statistics
    """

    try:
        async with get_connection() as conn:
            params: dict = {}
            honeypot_filter = ""

            if honeypot_id:
                honeypot_filter = "AND honeypot_id = %(honeypot_id)s"
                params["honeypot_id"] = honeypot_id

            now = datetime.now(timezone.utc)
            params["today_start"] = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            params["week_start"] = now - timedelta(days=days)
            params["hour_ago"] = now - timedelta(hours=1)

            async with conn.cursor() as cur:
                # Total events
                query = (
                    f"SELECT COUNT(*) FROM honeypot_events WHERE 1=1 {honeypot_filter}"  # nosec
                )
                await cur.execute(query, params)
                row = await cur.fetchone()
                total_events = row[0] if row else 0

                # Unique IPs
                query = f"SELECT COUNT(DISTINCT source_ip) FROM honeypot_events WHERE 1=1 {honeypot_filter}"  # nosec
                await cur.execute(query, params)
                row = await cur.fetchone()
                unique_ips = row[0] if row else 0

                # Total sessions
                query = f"SELECT COUNT(*) FROM honeypot_sessions WHERE 1=1 {honeypot_filter}"  # nosec
                await cur.execute(query, params)
                row = await cur.fetchone()
                total_sessions = row[0] if row else 0

                # Active sessions (not ended)
                query = f"SELECT COUNT(*) FROM honeypot_sessions WHERE ended_at IS NULL {honeypot_filter}"  # nosec
                await cur.execute(query, params)
                row = await cur.fetchone()
                active_sessions = row[0] if row else 0

                # Events today
                query = f"""SELECT COUNT(*) FROM honeypot_events 
                    WHERE timestamp >= %(today_start)s {honeypot_filter}"""  # nosec
                await cur.execute(query, params)
                row = await cur.fetchone()
                events_today = row[0] if row else 0

                # Events this week
                query = f"""SELECT COUNT(*) FROM honeypot_events 
                    WHERE timestamp >= %(week_start)s {honeypot_filter}"""  # nosec
                await cur.execute(query, params)
                row = await cur.fetchone()
                events_this_week = row[0] if row else 0

                # Events last hour
                query = f"""SELECT COUNT(*) FROM honeypot_events 
                    WHERE timestamp >= %(hour_ago)s {honeypot_filter}"""  # nosec
                await cur.execute(query, params)
                row = await cur.fetchone()
                events_last_hour = row[0] if row else 0

                # Protocol breakdown
                query = f"""SELECT protocol, COUNT(*) FROM honeypot_events 
                    WHERE 1=1 {honeypot_filter}
                    GROUP BY protocol"""  # nosec
                await cur.execute(query, params)
                rows = await cur.fetchall()
                protocol_breakdown = {row[0]: row[1] for row in rows}

                # Severity breakdown
                query = f"""SELECT severity, COUNT(*) FROM honeypot_events 
                    WHERE 1=1 {honeypot_filter}
                    GROUP BY severity"""  # nosec
                await cur.execute(query, params)
                rows = await cur.fetchall()
                severity_breakdown = {row[0]: row[1] for row in rows}

                # Category breakdown
                query = f"""SELECT category, COUNT(*) FROM honeypot_events 
                    WHERE category IS NOT NULL {honeypot_filter}
                    GROUP BY category"""  # nosec
                await cur.execute(query, params)
                rows = await cur.fetchall()
                category_breakdown = {row[0]: row[1] for row in rows}

                # Top attacker IPs
                query = f"""SELECT 
                        source_ip, 
                        COUNT(*) as cnt,
                        MAX(meta->'geo'->>'country_code') as country_code
                    FROM honeypot_events 
                    WHERE 1=1 {honeypot_filter}
                    GROUP BY source_ip ORDER BY cnt DESC LIMIT 10"""  # nosec
                await cur.execute(query, params)
                rows = await cur.fetchall()
                top_attacker_ips = [
                    {"ip": row[0], "count": row[1], "country_code": row[2]}
                    for row in rows
                ]

                # Event counts
                query = f"""SELECT COUNT(*) FROM honeypot_events 
                    WHERE matched_cves IS NOT NULL AND matched_cves != '[]'::jsonb 
                    {honeypot_filter}"""  # nosec
                await cur.execute(query, params)
                row = await cur.fetchone()
                cve_correlations = row[0] if row else 0

                # Bot Breakdown (using is_bot column if populated, or fallback to meta logic?
                # migration handles column, so just use column)
                # Count True, False, and Null
                query = f"""SELECT 
                        count(*) filter (where is_bot = true) as bots,
                        count(*) filter (where is_bot = false) as humans,
                        count(*) filter (where is_bot is null) as unknown
                    FROM honeypot_events
                    WHERE 1=1 {honeypot_filter}"""  # nosec
                await cur.execute(query, params)
                row = await cur.fetchone()
                bot_breakdown = {
                    "bot": row[0] if row else 0,
                    "human": row[1] if row else 0,
                    "unknown": row[2] if row else 0,
                }

                # Activity history (last 60 minutes, bucketed by minute)
                activity_history = []
                try:
                    query = f"""
                        SELECT
                            date_trunc('minute', timestamp) as time_bucket,
                            COUNT(*) as count
                        FROM honeypot_events
                        WHERE timestamp >= %(hour_ago)s {honeypot_filter}
                        GROUP BY time_bucket
                        ORDER BY time_bucket ASC
                    """  # nosec
                    await cur.execute(query, params)
                    rows = await cur.fetchall()

                    # Convert to ISO format for frontend compatibility
                    activity_history = [
                        {"time": row[0].isoformat() if row[0] else "", "count": row[1]}
                        for row in rows
                    ]
                except Exception as e:
                    logger.error(f"Failed to get activity history: {e}")
                    activity_history = []

                # Top Matched CVEs
                top_matched_cves = []
                try:
                    query = f"""SELECT 
                            cve, 
                            COUNT(*) as cnt 
                        FROM honeypot_events,
                             jsonb_array_elements_text(matched_cves) as cve
                        WHERE matched_cves IS NOT NULL 
                          AND matched_cves != '[]'::jsonb 
                          {honeypot_filter}
                        GROUP BY cve 
                        ORDER BY cnt DESC 
                        LIMIT 10"""  # nosec
                    await cur.execute(query, params)
                    rows = await cur.fetchall()
                    top_matched_cves = [
                        {"cve_id": row[0], "count": row[1]} for row in rows
                    ]
                except Exception as e:
                    logger.error(f"Failed to get top CVEs: {e}")
                    top_matched_cves = []

            return {
                "total_connections": total_events,
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_events": total_events,
                "unique_ips": unique_ips,
                "banned_ips": 0,  # Would need separate tracking
                "top_attacker_ips": top_attacker_ips,
                "protocol_breakdown": protocol_breakdown,
                "severity_breakdown": severity_breakdown,
                "category_breakdown": category_breakdown,
                "bot_breakdown": bot_breakdown,
                "cve_correlations": cve_correlations,
                "top_matched_cves": top_matched_cves,
                "events_last_hour": events_last_hour,
                "events_today": events_today,
                "events_this_week": events_this_week,
                "activity_history": activity_history,
            }

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {}
