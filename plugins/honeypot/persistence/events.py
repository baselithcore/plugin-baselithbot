"""
Event persistence logic for Honeypot.
"""

import json
from core.observability.logging import get_logger
from typing import Optional, List, Tuple, Any, Dict
from datetime import datetime, timezone

from psycopg.types.json import Json


from plugins.honeypot.models import (
    AttackEvent,
    AttackCategory,
    AttackSeverity,
    GeoLocation,
    HoneypotProtocol,
)
from .database import get_connection

logger = get_logger(__name__)


async def save_event(event: AttackEvent) -> None:
    """Save a honeypot event."""
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO honeypot_events (
                        event_id, session_id, honeypot_id, protocol, 
                        timestamp, source_ip, event_type,
                        command, path, raw_data,
                        category, severity, ai_classification,
                        matched_cves, is_bot, meta
                    ) VALUES (
                        %(event_id)s, %(session_id)s, %(honeypot_id)s, %(protocol)s,
                        %(timestamp)s, %(source_ip)s, %(event_type)s,
                        %(command)s, %(path)s, %(raw_data)s,
                        %(category)s, %(severity)s, %(ai_classification)s,
                        %(matched_cves)s, %(is_bot)s, %(meta)s
                    )
                    ON CONFLICT (event_id) DO NOTHING
                """,
                    {
                        "event_id": event.event_id,
                        "session_id": event.session_id,
                        "honeypot_id": event.honeypot_id,
                        "protocol": event.protocol.value,
                        "timestamp": event.timestamp,
                        "source_ip": event.source_ip,
                        "event_type": event.event_type,
                        "command": event.command,
                        "path": event.http_path,
                        "raw_data": event.raw_data[:2000] if event.raw_data else None,
                        "category": event.category.value,
                        "severity": event.severity.value,
                        "ai_classification": event.ai_classification,
                        "matched_cves": Json(event.matched_cves),
                        "is_bot": event.is_bot,  # Can be None, effectively NULL
                        "meta": Json(
                            {
                                "geo": event.geo.model_dump() if event.geo else None,
                                "username": event.username,
                                "password": event.password,
                                "http_method": event.http_method,
                                "http_headers": event.http_headers,
                                "detected_patterns": event.detected_patterns,
                                # Bot detection data (also kept in meta for now as signals are there)
                                "bot_confidence": event.bot_confidence,
                                "bot_classification": event.bot_classification,
                                "bot_signals": event.bot_signals,
                            }
                        ),
                    },
                )
    except Exception as e:
        import traceback

        logger.error(f"Failed to save event {event.event_id}: {e}")
        logger.error(traceback.format_exc())
        print(f"[ERROR] Failed to save event {event.event_id}: {e}", flush=True)


async def update_event_analysis(
    event_id: str,
    analysis: str,
    category: Optional[str] = None,
    matched_cves: Optional[List[str]] = None,
) -> bool:
    """Update event with AI analysis results.

    Args:
        event_id: The event ID to update
        analysis: The AI analysis summary/content
        category: Optional updated category from AI
        matched_cves: Optional list of matched CVE IDs

    Returns:
        True if event was updated
    """
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                updates = ["ai_classification = %(analysis)s"]
                params = {"event_id": event_id, "analysis": analysis}

                if category:
                    updates.append("category = %(category)s")
                    params["category"] = category

                if matched_cves is not None:
                    updates.append("matched_cves = %(matched_cves)s")
                    params["matched_cves"] = json.dumps(matched_cves)

                query = f"""
                    UPDATE honeypot_events 
                    SET {", ".join(updates)}
                    WHERE event_id = %(event_id)s
                """  # nosec

                await cur.execute(query, params)
                updated = cur.rowcount > 0
                if updated:
                    logger.info(f"Updated analysis for event {event_id}")
                return updated
    except Exception as e:
        logger.error(f"Failed to update analysis for {event_id}: {e}")
        return False


async def delete_events_by_ip(ip_address: str) -> int:
    """Delete all events and associated sessions from a specific IP address.

    Args:
        ip_address: The IP address to delete events for

    Returns:
        Number of deleted events
    """
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # 1. Delete from events first (to safely handle cases where CASCADE is missing)
                await cur.execute(
                    "DELETE FROM honeypot_events WHERE source_ip = %(ip)s",
                    {"ip": ip_address},
                )
                events_deleted = cur.rowcount

                # 2. Delete from sessions
                await cur.execute(
                    "DELETE FROM honeypot_sessions WHERE source_ip = %(ip)s",
                    {"ip": ip_address},
                )
                sessions_deleted = cur.rowcount

                logger.info(
                    f"Deleted {events_deleted} events and {sessions_deleted} sessions from IP {ip_address}"
                )
                return events_deleted

    except Exception as e:
        logger.error(f"Failed to delete events from IP {ip_address}: {e}")
        return 0


async def delete_event_by_id(event_id: str) -> bool:
    """Delete a specific event by ID.

    Args:
        event_id: The ID of the event to delete

    Returns:
        True if the event was deleted, False otherwise
    """
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM honeypot_events WHERE event_id = %(event_id)s",
                    {"event_id": event_id},
                )
                updated = cur.rowcount > 0
                if updated:
                    logger.info(f"Deleted event {event_id}")
                return updated
    except Exception as e:
        logger.error(f"Failed to delete event {event_id}: {e}")
        return False


async def get_events(
    page: int = 1,
    page_size: int = 50,
    honeypot_id: Optional[str] = None,
    protocol: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    source_ip: Optional[str] = None,
    country: Optional[str] = None,
    is_bot: Optional[bool] = None,
    start_time: Optional[datetime] = None,
) -> Tuple[List[AttackEvent], int]:
    """Query events from DB with filtering and pagination.

    Returns:
        Tuple of (events list, total count)
    """

    try:
        async with get_connection() as conn:
            # Build WHERE clause
            conditions = []
            params: dict = {}

            if honeypot_id:
                conditions.append("honeypot_id = %(honeypot_id)s")
                params["honeypot_id"] = honeypot_id
            if protocol:
                conditions.append("protocol = %(protocol)s")
                params["protocol"] = protocol
            if severity:
                if "," in severity:
                    # Handle multiple severities (e.g. "critical,high")
                    sevs = severity.split(",")
                    conditions.append("severity = ANY(%(severities)s)")
                    params["severities"] = sevs
                else:
                    conditions.append("severity = %(severity)s")
                    params["severity"] = severity
            if category:
                conditions.append("category = %(category)s")
                params["category"] = category
            if source_ip:
                # Use LIKE for partial matches (starts with) to support autocomplete
                conditions.append("source_ip LIKE %(source_ip_pattern)s")
                params["source_ip_pattern"] = f"{source_ip}%"
            if country:
                # Query JSONB meta field for country code OR name with partial match
                conditions.append(
                    "(meta->'geo'->>'country_code' ILIKE %(country_pattern)s OR meta->'geo'->>'country' ILIKE %(country_pattern)s)"
                )
                params["country_pattern"] = f"{country}%"
            if start_time:
                conditions.append("timestamp >= %(start_time)s")
                params["start_time"] = start_time
            if is_bot is not None:
                conditions.append("is_bot = %(is_bot)s")
                params["is_bot"] = is_bot

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Get total count
            async with conn.cursor() as cur:
                query = f"SELECT COUNT(*) FROM honeypot_events WHERE {where_clause}"  # nosec
                await cur.execute(query, params)
                row = await cur.fetchone()
                total = row[0] if row else 0

            # Get paginated results
            offset = (page - 1) * page_size
            params["limit"] = page_size
            params["offset"] = offset

            async with conn.cursor() as cur:
                query = f"""
                    SELECT event_id, session_id, honeypot_id, protocol,
                           timestamp, source_ip, event_type,
                           command, path, raw_data,
                           category, severity, ai_classification,
                           matched_cves, is_bot, meta
                    FROM honeypot_events
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT %(limit)s OFFSET %(offset)s
                    """  # nosec
                await cur.execute(query, params)
                rows = await cur.fetchall()

            events = []
            for row in rows:
                try:
                    meta_raw = row[15]
                    meta: Dict[str, Any] = {}
                    if isinstance(meta_raw, str):
                        try:
                            meta = json.loads(meta_raw)
                        except Exception:
                            meta = {}
                    elif isinstance(meta_raw, dict):
                        meta = meta_raw
                    # else None -> empty dict

                    # Handle matched_cves
                    matched_cves_raw = row[13]
                    matched_cves: List[str] = []
                    if isinstance(matched_cves_raw, str):
                        try:
                            matched_cves = json.loads(matched_cves_raw)
                        except Exception:
                            matched_cves = []
                    elif isinstance(matched_cves_raw, list):
                        matched_cves = matched_cves_raw

                    geo_data = meta.get("geo") or {}
                    # Handle case where geo_data is string (double serialized)
                    if isinstance(geo_data, str):
                        try:
                            geo_data = json.loads(geo_data)
                        except Exception:
                            geo_data = {}

                    geo = None
                    if geo_data and isinstance(geo_data, dict):
                        try:
                            geo = GeoLocation(**geo_data)
                        except Exception:
                            geo = None

                    # Ensure Enums don't crash
                    try:
                        proto = HoneypotProtocol(row[3])
                    except ValueError:
                        proto = HoneypotProtocol.TCP  # Fallback

                    try:
                        cat = (
                            AttackCategory(row[10])
                            if row[10]
                            else AttackCategory.UNKNOWN
                        )
                    except ValueError:
                        cat = AttackCategory.UNKNOWN

                    try:
                        sev = (
                            AttackSeverity(row[11]) if row[11] else AttackSeverity.INFO
                        )
                    except ValueError:
                        sev = AttackSeverity.INFO

                    # Ensure timestamp is timezone-aware
                    ts = row[4]
                    if ts and ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)

                    events.append(
                        AttackEvent(
                            event_id=row[0],
                            session_id=row[1],
                            honeypot_id=row[2],
                            protocol=proto,
                            timestamp=ts,
                            source_ip=row[5],
                            source_port=0,  # Not stored, default
                            event_type=row[6] or "command",
                            command=row[7],
                            http_path=row[8],
                            raw_data=row[9] or "",
                            category=cat,
                            severity=sev,
                            ai_classification=row[12],
                            matched_cves=matched_cves,
                            geo=geo,
                            detected_patterns=meta.get("detected_patterns") or [],
                            username=meta.get("username"),
                            password=meta.get("password"),
                            http_method=meta.get("http_method"),
                            http_headers=meta.get("http_headers"),
                            # Bot detection fields
                            is_bot=row[14]
                            if row[14] is not None
                            else meta.get("is_bot"),
                            bot_confidence=meta.get("bot_confidence"),
                            bot_classification=meta.get("bot_classification"),
                            bot_signals=meta.get("bot_signals"),
                        )
                    )
                except Exception as e:
                    # Log but continue processing other events
                    logger.warning(f"Failed to hydrate event {row[0]}: {e}")
                    continue

            return events, total

    except Exception as e:
        logger.error(f"Failed to query events: {e}")
        return [], 0


async def get_event_by_id(event_id: str) -> Optional[AttackEvent]:
    """Get a single event by ID."""
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT event_id, session_id, honeypot_id, protocol,
                           timestamp, source_ip, event_type,
                           command, path, raw_data,
                           category, severity, ai_classification,
                           matched_cves, is_bot, meta
                    FROM honeypot_events
                    WHERE event_id = %(event_id)s
                    """,
                    {"event_id": event_id},
                )
                row = await cur.fetchone()

                if not row:
                    return None

                meta_raw = row[15]
                meta: Dict[str, Any] = {}
                if isinstance(meta_raw, str):
                    try:
                        meta = json.loads(meta_raw)
                    except Exception:
                        meta = {}
                elif isinstance(meta_raw, dict):
                    meta = meta_raw

                geo_data = meta.get("geo")
                geo = GeoLocation(**geo_data) if geo_data else None

                ts = row[4]
                # Postgres timestamp is automatically datetime
                ts = row[4]
                if ts and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)

                return AttackEvent(
                    event_id=row[0],
                    session_id=row[1],
                    honeypot_id=row[2],
                    protocol=HoneypotProtocol(row[3]),
                    timestamp=ts,
                    source_ip=row[5],
                    source_port=0,
                    event_type=row[6] or "command",
                    command=row[7],
                    http_path=row[8],
                    raw_data=row[9] or "",
                    category=AttackCategory(row[10])
                    if row[10]
                    else AttackCategory.UNKNOWN,
                    severity=AttackSeverity(row[11])
                    if row[11]
                    else AttackSeverity.INFO,
                    ai_classification=row[12],
                    matched_cves=row[13]
                    if isinstance(row[13], list)
                    else (json.loads(row[13]) if isinstance(row[13], str) else []),
                    geo=geo,
                    detected_patterns=meta.get("detected_patterns", []),
                    username=meta.get("username"),
                    password=meta.get("password"),
                    http_method=meta.get("http_method"),
                    http_headers=meta.get("http_headers"),
                    # Bot detection fields
                    is_bot=row[14] if row[14] is not None else meta.get("is_bot"),
                    bot_confidence=meta.get("bot_confidence"),
                    bot_classification=meta.get("bot_classification"),
                    bot_signals=meta.get("bot_signals"),
                )

    except Exception as e:
        logger.error(f"Failed to get event {event_id}: {e}")
        return None


async def get_recent_events(limit: int = 1000) -> List[AttackEvent]:
    """Load recent events for in-memory hydration on startup.

    Args:
        limit: Maximum number of events to load

    Returns:
        List of recent AttackEvents ordered by timestamp ASC (oldest first)
    """
    events, _ = await get_events(page=1, page_size=limit)
    # Events come in DESC order, reverse for ASC (chronological for deque append)
    return list(reversed(events))
