"""
Database schema management for Honeypot persistence.
"""

from core.observability.logging import get_logger
from .database import ensure_database_exists, init_pool, get_connection

logger = get_logger(__name__)

_schema_initialized = False


async def ensure_schema() -> None:
    """Create necessary tables in the analytics database."""
    global _schema_initialized
    if _schema_initialized:
        return

    await ensure_database_exists()
    await init_pool()  # Initialize pool connects to the new DB

    # PostgreSQL-only types
    json_type = "JSONB"
    timestamp_type = "TIMESTAMPTZ"

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Sessions Table
                await cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS honeypot_sessions (
                        session_id TEXT PRIMARY KEY,
                        honeypot_id TEXT NOT NULL,
                        protocol TEXT NOT NULL,
                        source_ip TEXT NOT NULL,
                        source_port INTEGER,
                        started_at {timestamp_type} NOT NULL,
                        ended_at {timestamp_type},
                        duration_seconds FLOAT,
                        auth_attempts INTEGER DEFAULT 0,
                        auth_success BOOLEAN DEFAULT FALSE,
                        username TEXT,
                        primary_category TEXT,
                        max_severity TEXT,
                        country TEXT,
                        ai_summary TEXT,
                        meta {json_type}
                    );
                """)
                await cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_hp_sessions_ip ON honeypot_sessions(source_ip);"
                )
                await cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_hp_sessions_started ON honeypot_sessions(started_at DESC);"
                )

                # Events Table
                await cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS honeypot_events (
                        event_id TEXT PRIMARY KEY,
                        session_id TEXT REFERENCES honeypot_sessions(session_id) ON DELETE CASCADE,
                        honeypot_id TEXT NOT NULL,
                        protocol TEXT NOT NULL,
                        timestamp {timestamp_type} NOT NULL,
                        source_ip TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        command TEXT,
                        path TEXT,
                        raw_data TEXT,
                        category TEXT,
                        severity TEXT,
                        ai_classification TEXT,
                        matched_cves {json_type},
                        is_bot BOOLEAN,
                        meta {json_type}
                    );
                """)
                await cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_hp_events_session ON honeypot_events(session_id);"
                )
                await cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_hp_events_ip ON honeypot_events(source_ip);"
                )
                await cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_hp_events_timestamp ON honeypot_events(timestamp DESC);"
                )
                await cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_hp_events_severity ON honeypot_events(severity);"
                )
                await cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_hp_events_is_bot ON honeypot_events(is_bot);"
                )

        _schema_initialized = True
    except Exception as e:
        logger.error(f"Schema initialization failed: {e}")

    # Ensure pentest tables are created
    from .pentest.schema import ensure_pentest_tables

    await ensure_pentest_tables()

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Discovery Results Table
                await cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS discovery_results (
                        analysis_id TEXT PRIMARY KEY,
                        honeypot_id TEXT,
                        analyzed_at {timestamp_type} NOT NULL,
                        result_json {json_type} NOT NULL
                    );
                """)
                await cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_discovery_honeypot ON discovery_results(honeypot_id);"
                )
                await cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_discovery_analyzed_at ON discovery_results(analyzed_at DESC);"
                )
    except Exception as e:
        logger.error(f"Discovery schema initialization failed: {e}")

    # Perform lightweight migration (add columns if missing) due to schemaless evolution
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Add potentially missing columns to honeypot_events
                for col, dtype in [
                    ("matched_cves", json_type),
                    ("ai_classification", "TEXT"),
                    ("is_bot", "BOOLEAN"),
                    ("meta", json_type),
                    ("session_id", "TEXT"),  # Ensure FK column exists
                ]:
                    await cur.execute(f"""
                        ALTER TABLE honeypot_events 
                        ADD COLUMN IF NOT EXISTS {col} {dtype};
                    """)

                # Add potentially missing columns to honeypot_sessions
                for col, dtype in [
                    ("meta", json_type),
                    ("ai_summary", "TEXT"),
                    ("max_severity", "TEXT"),
                    ("auth_attempts", "INTEGER"),
                ]:
                    await cur.execute(f"""
                        ALTER TABLE honeypot_sessions 
                        ADD COLUMN IF NOT EXISTS {col} {dtype};
                    """)
    except Exception as e:
        logger.warning(f"Migration step failed (safe to ignore if columns exist): {e}")
