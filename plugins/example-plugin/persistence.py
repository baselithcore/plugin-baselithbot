"""
Persistence layer for the Example Plugin.

This module demonstrates how to manage database connections and schemas
within a plugin using the core configuration.
"""

from core.observability.logging import get_logger
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from urllib.parse import quote_plus

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from core.config import get_storage_config
from core.context import get_tenant_or_default

logger = get_logger(__name__)

# Reusing core storage config but targeting a custom database or existing one
# For this example, we'll use the default core DB but create a separate table.
_storage_config = get_storage_config()

_POOL: Optional[AsyncConnectionPool] = None


def get_conninfo() -> str:
    """Build connection string reusing core credentials."""
    user = quote_plus(_storage_config.db_user or "")
    # ``db_password`` is a ``SecretStr`` in core config; unwrap before quoting.
    raw_password = (
        _storage_config.db_password.get_secret_value()
        if _storage_config.db_password
        else ""
    )
    password = quote_plus(raw_password) if raw_password else ""
    password_fragment = f":{password}" if password else ""
    host = _storage_config.db_host or "localhost"
    port = _storage_config.db_port or 5432
    dbname = _storage_config.db_name  # Using core DB for example simplicity

    return f"postgresql://{user}{password_fragment}@{host}:{port}/{dbname}"


async def init_pool():
    """Initialize the database connection pool."""
    global _POOL
    if _POOL is None:
        try:
            if _storage_config.postgres_enabled:
                _POOL = AsyncConnectionPool(
                    conninfo=get_conninfo(),
                    min_size=1,
                    max_size=5,
                    timeout=30.0,
                    kwargs={"autocommit": True},
                    open=False,
                )
                await _POOL.open()
                logger.info("Example Plugin: DB pool initialized")
            else:
                logger.warning("PostgreSQL disabled, persistence will not work.")
        except Exception as e:
            logger.error(f"Failed to initialize example pool: {e}")
            raise


async def close_pool():
    """Close the database connection pool."""
    global _POOL
    if _POOL is not None:
        await _POOL.close()
        _POOL = None
        logger.info("Example Plugin: DB pool closed")


@asynccontextmanager
async def get_connection() -> AsyncIterator[AsyncConnection[object]]:
    """Yields a connection from the pool."""
    if _POOL is None:
        await init_pool()

    if _POOL is None:
        raise RuntimeError("Failed to initialize database pool")

    async with _POOL.connection() as conn:
        yield conn


async def ensure_schema():
    """Create example tables."""
    if not _storage_config.postgres_enabled:
        return

    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                # ``tenant_id`` scopes every row to the authenticated tenant
                # (identity-derived; see core.context). DEFAULT 'default' keeps
                # existing single-tenant rows working; the ALTER upgrades a table
                # created before tenancy. This is the reference pattern every
                # data-persisting plugin should follow.
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS example_items (
                        id SERIAL PRIMARY KEY,
                        tenant_id TEXT NOT NULL DEFAULT 'default',
                        name TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        data JSONB
                    );
                """)
                await cur.execute(
                    "ALTER TABLE example_items "
                    "ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';"
                )
                await cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_example_items_tenant "
                    "ON example_items(tenant_id);"
                )
        logger.info("Example Plugin: Schema ensured")
    except Exception as e:
        logger.error(f"Example Plugin: Schema initialization failed: {e}")


class ExampleDAO:
    """Data Access Object for example items."""

    @staticmethod
    async def create_item(name: str, data: dict) -> int:
        """Create a new item."""
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO example_items (tenant_id, name, data) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (get_tenant_or_default(), name, Jsonb(data)),
                )
                row = await cur.fetchone()
                return row[0] if row else -1

    @staticmethod
    async def get_items() -> list:
        """Get all items for the current tenant."""
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id, name, data FROM example_items WHERE tenant_id = %s",
                    (get_tenant_or_default(),),
                )
                return await cur.fetchall()
