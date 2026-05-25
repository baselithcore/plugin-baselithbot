"""
Session persistence logic for Honeypot.
"""

import json
from core.observability.logging import get_logger
from typing import Optional, List
from datetime import timezone

from plugins.honeypot.models import (
    HoneypotSession,
    AttackCategory,
    AttackSeverity,
    GeoLocation,
    HoneypotProtocol,
)
from .database import get_connection

logger = get_logger(__name__)


async def save_session(session: HoneypotSession) -> None:
    """Upsert a honeypot session."""
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO honeypot_sessions (
                        session_id, honeypot_id, protocol, source_ip, source_port,
                        started_at, ended_at, duration_seconds, 
                        auth_attempts, auth_success, username,
                        primary_category, max_severity, country, ai_summary, meta
                    ) VALUES (
                        %(session_id)s, %(honeypot_id)s, %(protocol)s, %(source_ip)s, %(source_port)s,
                        %(started_at)s, %(ended_at)s, %(duration_seconds)s,
                        %(auth_attempts)s, %(auth_success)s, %(username)s,
                        %(primary_category)s, %(max_severity)s, %(country)s, %(ai_summary)s, %(meta)s
                    )
                    ON CONFLICT (session_id) DO UPDATE SET
                        ended_at = EXCLUDED.ended_at,
                        duration_seconds = EXCLUDED.duration_seconds,
                        auth_attempts = EXCLUDED.auth_attempts,
                        auth_success = EXCLUDED.auth_success,
                        primary_category = EXCLUDED.primary_category,
                        max_severity = EXCLUDED.max_severity,
                        ai_summary = EXCLUDED.ai_summary,
                        meta = EXCLUDED.meta
                """,
                    {
                        "session_id": session.session_id,
                        "honeypot_id": session.honeypot_id,
                        "protocol": session.protocol.value,
                        "source_ip": session.source_ip,
                        "source_port": session.source_port,
                        "started_at": session.started_at,
                        "ended_at": session.ended_at,
                        "duration_seconds": session.duration_seconds,
                        "auth_attempts": session.auth_attempts,
                        "auth_success": session.auth_success,
                        "username": session.username,
                        "primary_category": session.primary_category.value,
                        "max_severity": session.max_severity.value,
                        "country": session.geo.country if session.geo else None,
                        "ai_summary": session.ai_summary,
                        "meta": json.dumps(
                            {
                                "geo": session.geo.model_dump()
                                if session.geo
                                else None,
                                "matched_cves": session.matched_cves,
                                "commands": session.commands,
                                "paths": session.paths_accessed,
                            }
                        ),
                    },
                )
    except Exception as e:
        logger.error(f"Failed to save session {session.session_id}: {e}")


async def get_sessions(
    honeypot_id: Optional[str] = None,
    active_only: bool = False,
    page: int = 1,
    page_size: int = 100,
    protocol: Optional[str] = None,
) -> tuple[List[HoneypotSession], int]:
    """Query sessions from DB with pagination.

    Args:
        honeypot_id: Optional filter by honeypot
        active_only: Only return sessions without ended_at
        page: Page number (1-based)
        page_size: Items per page
        protocol: Optional filter by protocol

    Returns:
        Tuple of (List[HoneypotSession], total_count)
    """

    try:
        async with get_connection() as conn:
            conditions = []
            limit = page_size
            offset = (page - 1) * page_size
            params: dict = {"limit": limit, "offset": offset}

            if honeypot_id:
                conditions.append("honeypot_id = %(honeypot_id)s")
                params["honeypot_id"] = honeypot_id
            if protocol:
                conditions.append("protocol = %(protocol)s")
                params["protocol"] = protocol
            if active_only:
                conditions.append("ended_at IS NULL")

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            async with conn.cursor() as cur:
                # Get total count first
                count_query = (
                    f"SELECT COUNT(*) FROM honeypot_sessions WHERE {where_clause}"  # nosec
                )
                await cur.execute(count_query, params)
                total_row = await cur.fetchone()
                total = total_row[0] if total_row else 0

                # Get data
                query = f"""
                    SELECT session_id, honeypot_id, protocol, source_ip, source_port,
                           started_at, ended_at, duration_seconds,
                           auth_attempts, auth_success, username,
                           primary_category, max_severity, country, ai_summary, meta
                    FROM honeypot_sessions
                    WHERE {where_clause}
                    ORDER BY started_at DESC
                    LIMIT %(limit)s OFFSET %(offset)s
                    """  # nosec
                await cur.execute(query, params)
                rows = await cur.fetchall()

            sessions = []
            for row in rows:
                # Postgres JSONB is automatically dict
                meta = row[15] or {}

                # Postgres timestamps are automatically datetime
                started_at = row[5]
                if started_at and started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)

                ended_at = row[6]
                if ended_at and ended_at.tzinfo is None:
                    ended_at = ended_at.replace(tzinfo=timezone.utc)

                # Try to get full geo from meta, fallback to country column
                geo_data = meta.get("geo")
                geo = None
                if geo_data:
                    geo = GeoLocation(**geo_data)
                elif row[13]:  # country field fallback
                    geo = GeoLocation(country=row[13])

                sessions.append(
                    HoneypotSession(
                        session_id=row[0],
                        honeypot_id=row[1],
                        protocol=HoneypotProtocol(row[2]),
                        source_ip=row[3],
                        source_port=row[4] or 0,
                        started_at=started_at,
                        ended_at=ended_at,
                        duration_seconds=row[7],
                        auth_attempts=row[8] or 0,
                        auth_success=row[9] or False,
                        username=row[10],
                        primary_category=AttackCategory(row[11])
                        if row[11]
                        else AttackCategory.UNKNOWN,
                        max_severity=AttackSeverity(row[12])
                        if row[12]
                        else AttackSeverity.INFO,
                        geo=geo,
                        ai_summary=row[14],
                        matched_cves=meta.get("matched_cves", []),
                        commands=meta.get("commands", []),
                        paths_accessed=meta.get("paths", []),
                    )
                )

            return sessions, total

    except Exception as e:
        logger.error(f"Failed to query sessions: {e}")
        return [], 0


async def get_session_by_id(session_id: str) -> Optional[HoneypotSession]:
    """Get a specific session by ID.

    Args:
        session_id: The ID of the session to retrieve

    Returns:
        The session object if found, None otherwise
    """
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                query = """
                    SELECT session_id, honeypot_id, protocol, source_ip, source_port,
                           started_at, ended_at, duration_seconds,
                           auth_attempts, auth_success, username,
                           primary_category, max_severity, country, ai_summary, meta
                    FROM honeypot_sessions
                    WHERE session_id = %(session_id)s
                """  # nosec
                await cur.execute(query, {"session_id": session_id})
                row = await cur.fetchone()

                if not row:
                    return None

                # Postgres JSONB is automatically dict
                meta = row[15] or {}

                # Postgres timestamps are automatically datetime
                started_at = row[5]
                if started_at and started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)

                ended_at = row[6]
                if ended_at and ended_at.tzinfo is None:
                    ended_at = ended_at.replace(tzinfo=timezone.utc)

                # Try to get full geo from meta, fallback to country column
                geo_data = meta.get("geo")
                geo = None
                if geo_data:
                    geo = GeoLocation(**geo_data)
                elif row[13]:  # country field fallback
                    geo = GeoLocation(country=row[13])

                return HoneypotSession(
                    session_id=row[0],
                    honeypot_id=row[1],
                    protocol=HoneypotProtocol(row[2]),
                    source_ip=row[3],
                    source_port=row[4] or 0,
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_seconds=row[7],
                    auth_attempts=row[8] or 0,
                    auth_success=row[9] or False,
                    username=row[10],
                    primary_category=AttackCategory(row[11])
                    if row[11]
                    else AttackCategory.UNKNOWN,
                    max_severity=AttackSeverity(row[12])
                    if row[12]
                    else AttackSeverity.INFO,
                    geo=geo,
                    ai_summary=row[14],
                    matched_cves=meta.get("matched_cves", []),
                    commands=meta.get("commands", []),
                    paths_accessed=meta.get("paths", []),
                )

    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        return None


async def delete_sessions_by_ip(ip_address: str) -> int:
    """Delete all sessions from a specific IP address.

    Args:
        ip_address: The IP address to delete sessions for

    Returns:
        Number of deleted sessions
    """
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM honeypot_sessions WHERE source_ip = %(ip)s",
                    {"ip": ip_address},
                )
                deleted_count = cur.rowcount
                logger.info(f"Deleted {deleted_count} sessions from IP {ip_address}")
                return deleted_count
    except Exception as e:
        logger.error(f"Failed to delete sessions from IP {ip_address}: {e}")
        return 0


async def delete_session_by_id(session_id: str) -> bool:
    """Delete a specific session by ID and its associated events.

    Args:
        session_id: The ID of the session to delete

    Returns:
        True if the session was deleted, False otherwise
    """
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # 1. Delete associated events first (to safely handle missing CASCADE)
                await cur.execute(
                    "DELETE FROM honeypot_events WHERE session_id = %(session_id)s",
                    {"session_id": session_id},
                )

                # 2. Delete the session
                await cur.execute(
                    "DELETE FROM honeypot_sessions WHERE session_id = %(session_id)s",
                    {"session_id": session_id},
                )
                updated = cur.rowcount > 0
                if updated:
                    logger.info(f"Deleted session {session_id} and its events")
                return updated
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        return False
