"""Data Retention Service for Honeypot Persistence.

Provides configurable retention policies for automatic cleanup of old data:
- Time-based retention (delete events/sessions older than N days)
- Row-count retention (keep at most N rows, delete oldest)
- Retention status reporting for monitoring dashboards

Complements optimization.archive_old_events by adding policy-driven
automated retention with status tracking.
"""

from core.observability.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from .database import get_connection

logger = get_logger(__name__)


async def apply_retention_policy(
    max_age_days: int = 90,
    max_rows: int = 1_000_000,
) -> Dict[str, Any]:
    """Apply data retention policy to events and sessions.

    Deletes events and sessions older than ``max_age_days`` and, if the
    table still exceeds ``max_rows``, trims the oldest rows.

    Args:
        max_age_days: Maximum age of events in days.
        max_rows: Maximum number of events to retain.

    Returns:
        Summary dict with counts of deleted events and sessions.
    """
    result: Dict[str, Any] = {
        "events_deleted_by_age": 0,
        "sessions_deleted_by_age": 0,
        "events_deleted_by_count": 0,
        "retention_applied_at": datetime.now(timezone.utc).isoformat(),
    }

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # ---- Age-based retention ----
                await cur.execute(
                    "DELETE FROM honeypot_events WHERE timestamp < %(cutoff)s",
                    {"cutoff": cutoff},
                )
                result["events_deleted_by_age"] = cur.rowcount

                await cur.execute(
                    "DELETE FROM honeypot_sessions WHERE started_at < %(cutoff)s",
                    {"cutoff": cutoff},
                )
                result["sessions_deleted_by_age"] = cur.rowcount

                # ---- Row-count retention (events only) ----
                await cur.execute("SELECT COUNT(*) FROM honeypot_events")
                row = await cur.fetchone()
                total = row[0] if row else 0

                if total > max_rows:
                    excess = total - max_rows
                    await cur.execute(
                        """
                        DELETE FROM honeypot_events
                        WHERE event_id IN (
                            SELECT event_id FROM honeypot_events
                            ORDER BY timestamp ASC
                            LIMIT %(excess)s
                        )
                        """,
                        {"excess": excess},
                    )
                    result["events_deleted_by_count"] = cur.rowcount

        total_deleted = (
            result["events_deleted_by_age"]
            + result["sessions_deleted_by_age"]
            + result["events_deleted_by_count"]
        )
        if total_deleted > 0:
            logger.info(
                f"Retention policy applied: {total_deleted} records deleted "
                f"(age: {result['events_deleted_by_age']}e + "
                f"{result['sessions_deleted_by_age']}s, "
                f"count: {result['events_deleted_by_count']}e)"
            )
        else:
            logger.debug("Retention policy applied: no records to delete")

    except Exception as e:
        logger.error(f"Failed to apply retention policy: {e}")
        result["error"] = str(e)

    return result


async def get_retention_status() -> Dict[str, Any]:
    """Return current retention status for monitoring.

    Reports current row counts, storage age range, and estimated
    database size for events and sessions tables.

    Returns:
        Dictionary with table statistics and age information.
    """
    status: Dict[str, Any] = {
        "events_count": 0,
        "sessions_count": 0,
        "oldest_event": None,
        "newest_event": None,
        "oldest_session": None,
        "data_age_days": 0,
        "estimated_size_mb": 0.0,
    }

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Event counts
                await cur.execute("SELECT COUNT(*) FROM honeypot_events")
                row = await cur.fetchone()
                status["events_count"] = row[0] if row else 0

                # Session counts
                await cur.execute("SELECT COUNT(*) FROM honeypot_sessions")
                row = await cur.fetchone()
                status["sessions_count"] = row[0] if row else 0

                # Age range for events
                await cur.execute(
                    "SELECT MIN(timestamp), MAX(timestamp) FROM honeypot_events"
                )
                row = await cur.fetchone()
                if row and row[0]:
                    status["oldest_event"] = row[0].isoformat()
                    status["newest_event"] = row[1].isoformat() if row[1] else None
                    age_delta = datetime.now(timezone.utc) - row[0].replace(
                        tzinfo=timezone.utc
                    )
                    status["data_age_days"] = age_delta.days

                # Oldest session
                await cur.execute("SELECT MIN(started_at) FROM honeypot_sessions")
                row = await cur.fetchone()
                if row and row[0]:
                    status["oldest_session"] = row[0].isoformat()

                # Estimated table sizes
                await cur.execute(
                    """
                    SELECT
                        COALESCE(pg_total_relation_size('honeypot_events'), 0) +
                        COALESCE(pg_total_relation_size('honeypot_sessions'), 0)
                    """
                )
                row = await cur.fetchone()
                if row and row[0]:
                    status["estimated_size_mb"] = round(row[0] / (1024 * 1024), 2)

    except Exception as e:
        logger.error(f"Failed to get retention status: {e}")
        status["error"] = str(e)

    return status
