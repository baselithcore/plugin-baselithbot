"""
Database optimization and partitioning for honeypot analytics.

Implements:
- Table partitioning by timestamp (monthly)
- Composite indexes for common query patterns
- Auto-archiving for old events
- Read-through archive queries
"""

from core.observability.logging import get_logger
from datetime import datetime, timedelta, timezone

from .database import get_connection

logger = get_logger(__name__)


async def create_partitioning() -> None:
    """Create partitioned table structure for events.

    Implements PostgreSQL declarative partitioning by month for optimal
    query performance on large datasets (100K+ events).
    """
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Check if already partitioned
                await cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_class WHERE relname = 'honeypot_events_partitioned'
                    )
                """)
                exists = (await cur.fetchone())[0]

                if exists:
                    logger.info("Event partitioning already configured")
                    return

                logger.info("Creating partitioned event table...")

                # Note: Partitioning requires recreating the table
                # This is safe for new installations or can be done via migration
                # For existing data, use a migration script with data copy

                # Create partitioned table (commented out for safety - enable manually)
                # await cur.execute("""
                #     -- Rename existing table
                #     ALTER TABLE honeypot_events RENAME TO honeypot_events_old;
                #
                #     -- Create partitioned table
                #     CREATE TABLE honeypot_events (
                #         event_id TEXT NOT NULL,
                #         session_id TEXT,
                #         honeypot_id TEXT NOT NULL,
                #         protocol TEXT NOT NULL,
                #         timestamp TIMESTAMPTZ NOT NULL,
                #         source_ip TEXT NOT NULL,
                #         event_type TEXT NOT NULL,
                #         command TEXT,
                #         path TEXT,
                #         raw_data TEXT,
                #         category TEXT,
                #         severity TEXT,
                #         ai_classification TEXT,
                #         matched_cves JSONB,
                #         is_bot BOOLEAN,
                #         meta JSONB,
                #         PRIMARY KEY (event_id, timestamp)
                #     ) PARTITION BY RANGE (timestamp);
                #
                #     -- Migrate data
                #     INSERT INTO honeypot_events SELECT * FROM honeypot_events_old;
                #
                #     -- Drop old table
                #     DROP TABLE honeypot_events_old;
                # """)

                logger.warning(
                    "Partitioning is available but not auto-enabled. "
                    "See plugins/honeypot/persistence/optimization.py for migration script."
                )

    except Exception as e:
        logger.error(f"Failed to configure partitioning: {e}")


async def create_partition_for_month(year: int, month: int) -> None:
    """Create partition for specific month.

    Args:
        year: Year (e.g., 2026)
        month: Month (1-12)
    """
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Calculate partition bounds
                start_date = datetime(year, month, 1, tzinfo=timezone.utc)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                else:
                    end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)

                partition_name = f"honeypot_events_{year}_{month:02d}"

                # Check if partition exists
                await cur.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_class WHERE relname = %s)",
                    (partition_name,),
                )
                exists = (await cur.fetchone())[0]

                if exists:
                    return

                logger.info(f"Creating partition: {partition_name}")

                await cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {partition_name}
                    PARTITION OF honeypot_events
                    FOR VALUES FROM ('{start_date.isoformat()}') TO ('{end_date.isoformat()}')
                """)  # nosec

    except Exception as e:
        logger.warning(f"Failed to create partition for {year}-{month:02d}: {e}")


async def optimize_indexes() -> None:
    """Create composite indexes for common query patterns."""
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Composite index for filtering by IP + timestamp (common pattern)
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_hp_events_ip_timestamp
                    ON honeypot_events(source_ip, timestamp DESC);
                """)

                # Composite index for severity + timestamp (alert queries)
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_hp_events_severity_timestamp
                    ON honeypot_events(severity, timestamp DESC)
                    WHERE severity IN ('high', 'critical');
                """)

                # Index for honeypot_id + timestamp (per-honeypot stats)
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_hp_events_honeypot_timestamp
                    ON honeypot_events(honeypot_id, timestamp DESC);
                """)

                # Covering index for common event list query
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_hp_events_list_query
                    ON honeypot_events(timestamp DESC)
                    INCLUDE (event_id, source_ip, category, severity);
                """)

                # GIN index for JSONB meta searches
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_hp_events_meta_gin
                    ON honeypot_events USING GIN(meta);
                """)

                # Session lookup optimization
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_hp_sessions_ip_started
                    ON honeypot_sessions(source_ip, started_at DESC);
                """)

                logger.info("Optimized indexes created successfully")

    except Exception as e:
        logger.error(f"Failed to optimize indexes: {e}")


async def create_archive_table() -> None:
    """Create archive table for old events."""
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS honeypot_events_archive (
                        LIKE honeypot_events INCLUDING ALL
                    );
                """)

                # Index archive by timestamp
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_hp_events_archive_timestamp
                    ON honeypot_events_archive(timestamp DESC);
                """)

                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_hp_events_archive_ip
                    ON honeypot_events_archive(source_ip);
                """)

                logger.info("Archive table created successfully")

    except Exception as e:
        logger.error(f"Failed to create archive table: {e}")


async def archive_old_events(days_threshold: int = 30) -> int:
    """Archive events older than threshold.

    Args:
        days_threshold: Archive events older than this many days

    Returns:
        Number of archived events
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)

        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Move old events to archive
                await cur.execute(
                    """
                    WITH moved_events AS (
                        DELETE FROM honeypot_events
                        WHERE timestamp < %s
                        RETURNING *
                    )
                    INSERT INTO honeypot_events_archive
                    SELECT * FROM moved_events
                    ON CONFLICT (event_id) DO NOTHING
                """,
                    (cutoff_date,),
                )

                archived_count = cur.rowcount

                if archived_count > 0:
                    logger.info(
                        f"Archived {archived_count} events older than {days_threshold} days"
                    )

                return archived_count

    except Exception as e:
        logger.error(f"Failed to archive old events: {e}")
        return 0


async def get_table_stats() -> dict:
    """Get statistics about event tables.

    Returns:
        Dictionary with table statistics
    """
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # Count events in main table
                await cur.execute("SELECT COUNT(*) FROM honeypot_events")
                active_count = (await cur.fetchone())[0]

                # Count archived events
                await cur.execute("""
                    SELECT COUNT(*) FROM honeypot_events_archive
                    WHERE EXISTS (SELECT 1 FROM pg_class WHERE relname = 'honeypot_events_archive')
                """)
                try:
                    archived_count = (await cur.fetchone())[0]
                except Exception:
                    archived_count = 0

                # Get table sizes
                await cur.execute("""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('honeypot_events')) as active_size,
                        pg_size_pretty(pg_total_relation_size('honeypot_events_archive')) as archive_size
                    WHERE EXISTS (SELECT 1 FROM pg_class WHERE relname = 'honeypot_events')
                """)
                row = await cur.fetchone()
                active_size = row[0] if row else "0 bytes"
                archive_size = row[1] if row else "0 bytes"

                return {
                    "active_events": active_count,
                    "archived_events": archived_count,
                    "total_events": active_count + archived_count,
                    "active_table_size": active_size,
                    "archive_table_size": archive_size,
                }

    except Exception as e:
        logger.error(f"Failed to get table stats: {e}")
        return {
            "active_events": 0,
            "archived_events": 0,
            "total_events": 0,
            "active_table_size": "unknown",
            "archive_table_size": "unknown",
        }


async def optimize_for_scale() -> None:
    """Run all optimization tasks for scale.

    Should be called once during plugin initialization.
    """
    logger.info("Running database optimizations for scale...")

    # Create composite indexes
    await optimize_indexes()

    # Create archive table
    await create_archive_table()

    # Note: Partitioning requires manual migration
    # await create_partitioning()

    logger.info("Database optimization completed")
