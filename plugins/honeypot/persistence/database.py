"""
Database connection management for Honeypot persistence.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from urllib.parse import urlsplit, urlunsplit

from core.observability.logging import get_logger

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from core.config import get_storage_config
from plugins.honeypot.config import get_honeypot_config

logger = get_logger(__name__)

# --- Local Analytics Configuration ---

# We reuse the Core storage config to get credentials, but target a different DB.
_storage_config = get_storage_config()
_honeypot_config = get_honeypot_config()

# Define the target analytics database name
ANALYTICS_DB_NAME = "honeypot_analytics"


def get_analytics_conninfo() -> str:
    """Build connection string for the analytics database."""
    parsed = urlsplit(_storage_config.conninfo)
    return urlunsplit(parsed._replace(path=f"/{ANALYTICS_DB_NAME}"))


# We also need a maintenance connection to create the DB if missing
def get_maintenance_conninfo() -> str:
    """Connection string to default DB for maintenance operations."""
    return _storage_config.conninfo


# --- Connection Management ---

_ANALYTICS_POOL: Optional[AsyncConnectionPool] = None


async def init_pool():
    global _ANALYTICS_POOL
    if _ANALYTICS_POOL is None:
        try:
            if _storage_config.postgres_enabled:
                _ANALYTICS_POOL = AsyncConnectionPool(
                    conninfo=get_analytics_conninfo(),
                    min_size=5,  # Increased from 2 for high-volume warmup
                    max_size=50,  # Increased from 20 for extreme scalability
                    timeout=60.0,  # Increased from 45s for burst resilience
                    kwargs={"autocommit": True},
                    open=False,
                )
                await _ANALYTICS_POOL.open()
            else:
                logger.warning(
                    "PostgreSQL disabled, Honeypot persistence will not work."
                )

        except Exception as e:
            logger.error(f"Failed to initialize analytics pool: {e}")
            raise


async def close_pool():
    global _ANALYTICS_POOL
    if _ANALYTICS_POOL is not None:
        try:
            await _ANALYTICS_POOL.close()
            _ANALYTICS_POOL = None
        except Exception as e:
            logger.error(f"Failed to close analytics pool: {e}")


@asynccontextmanager
async def get_connection() -> AsyncIterator[AsyncConnection[object]]:
    """Yields a connection from the local pool."""
    if _ANALYTICS_POOL is None:
        await init_pool()

    if _ANALYTICS_POOL is None:
        raise RuntimeError("Failed to initialize database pool")

    async with _ANALYTICS_POOL.connection() as conn:
        yield conn


async def ensure_database_exists():
    """Create the analytics database if it doesn't exist.

    Handles migration from old 'agent_analytics' name if present.
    """
    if not _storage_config.postgres_enabled:
        return

    try:
        # Use a temporary connection to the maintenance DB
        conn = await AsyncConnection.connect(
            get_maintenance_conninfo(), autocommit=True
        )
        async with conn:
            async with conn.cursor() as cur:
                # 1. Check if target DB exists
                await cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (ANALYTICS_DB_NAME,)
                )
                exists = await cur.fetchone()

                if exists:
                    return

                # 2. Check if old DB exists (for migration)
                old_db_name = "agent_analytics"
                await cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (old_db_name,)
                )
                old_exists = await cur.fetchone()

                if old_exists:
                    logger.info(
                        f"Migrating database: {old_db_name} -> {ANALYTICS_DB_NAME}"
                    )
                    # Terminate other connections to the old DB before renaming
                    await cur.execute(
                        """
                        SELECT pg_terminate_backend(pid) 
                        FROM pg_stat_activity 
                        WHERE datname = %s AND pid <> pg_backend_pid()
                        """,
                        (old_db_name,),
                    )
                    await cur.execute(
                        f'ALTER DATABASE "{old_db_name}" RENAME TO "{ANALYTICS_DB_NAME}"'
                    )  # nosec
                else:
                    logger.info(f"Creating analytics database: {ANALYTICS_DB_NAME}")
                    await cur.execute(f'CREATE DATABASE "{ANALYTICS_DB_NAME}"')

    except Exception as e:
        logger.warning(f"Database creation/migration check failed: {e}")
