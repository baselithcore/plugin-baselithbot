"""
CVE Hunter Persistence Layer.

Handles saving CVE definitions and alerts to the dedicated Analytics PostgreSQL database.
Manages its own connection logic to avoid modifying the core.
"""

from core.observability.logging import get_logger
import json
from typing import Any, Optional, AsyncIterator
from urllib.parse import quote_plus, urlencode
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from core.config import get_storage_config
from plugins.cve_hunter.models import CVERecord, VulnerabilityAlert

logger = get_logger(__name__)

# --- Local Analytics Configuration ---

ANALYTICS_DB_NAME = "agent_analytics"


def _storage() -> Any:
    """Resolve the storage config lazily.

    Reading the storage config at module-import time can capture stale
    defaults if the application has not yet finished bootstrapping (e.g.
    env vars not parsed, secret manager not online). Defer the lookup so
    every call sees the current configuration.
    """
    return get_storage_config()


def get_analytics_conninfo() -> str:
    """Build connection string for the analytics database."""
    cfg = _storage()
    user = quote_plus(cfg.db_user or "")
    raw_password = cfg.db_password
    if hasattr(raw_password, "get_secret_value"):
        raw_password = raw_password.get_secret_value()
    password = quote_plus(raw_password) if raw_password else ""
    password_fragment = f":{password}" if password else ""
    host = cfg.db_host or "localhost"
    port = cfg.db_port or 5432

    query_params = {}
    if cfg.db_ssl_mode:
        query_params["sslmode"] = cfg.db_ssl_mode
    query = f"?{urlencode(query_params)}" if query_params else ""

    return f"postgresql://{user}{password_fragment}@{host}:{port}/{ANALYTICS_DB_NAME}{query}"


def get_maintenance_conninfo() -> str:
    """Connection string to default DB for maintenance operations."""
    return _storage().conninfo


# --- Connection Management ---

_ANALYTICS_POOL: Optional[AsyncConnectionPool] = None


async def init_pool():
    global _ANALYTICS_POOL

    if not _storage().postgres_enabled:
        logger.debug("PostgreSQL disabled, skipping analytics pool initialization.")
        return

    if _ANALYTICS_POOL is None:
        try:
            pool = AsyncConnectionPool(
                conninfo=get_analytics_conninfo(),
                min_size=1,
                max_size=10,
                timeout=30.0,
                kwargs={"autocommit": True},
                open=False,
            )
            await pool.open()
            _ANALYTICS_POOL = pool
            logger.info(
                "Analytics pool initialized",
                extra={"db": ANALYTICS_DB_NAME, "min_size": 1, "max_size": 10},
            )
        except Exception as e:
            logger.error("Failed to initialize analytics pool", extra={"error": str(e)})


@asynccontextmanager
async def get_connection() -> AsyncIterator[AsyncConnection[object]]:
    """Yields a connection from the local pool."""
    if not _storage().postgres_enabled:
        raise RuntimeError("PostgreSQL is disabled.")

    if _ANALYTICS_POOL is None:
        await init_pool()
        if _ANALYTICS_POOL is None:
            raise RuntimeError("Analytics pool could not be initialized.")

    async with _ANALYTICS_POOL.connection() as conn:
        yield conn


async def ensure_database_exists():
    """Create the analytics database if it doesn't exist."""
    if not _storage().postgres_enabled:
        return

    try:
        conn = await AsyncConnection.connect(
            get_maintenance_conninfo(), autocommit=True
        )
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (ANALYTICS_DB_NAME,)
                )
                exists = await cur.fetchone()
                if not exists:
                    logger.info(f"Creating analytics database: {ANALYTICS_DB_NAME}")
                    await cur.execute(f"CREATE DATABASE {ANALYTICS_DB_NAME}")
    except Exception as e:
        logger.warning(f"Database creation check failed (might already exist): {e}")


class CVEHunterDAO:
    """Data Access Object for CVE Hunter analytics."""

    @staticmethod
    async def ensure_schema() -> None:
        """Create necessary tables in the analytics database."""
        if not _storage().postgres_enabled:
            return

        await ensure_database_exists()
        await init_pool()

        try:
            async with get_connection() as conn:
                async with conn.cursor() as cur:
                    # CVE Definitions Table
                    await cur.execute("""
                        CREATE TABLE IF NOT EXISTS cve_definitions (
                            cve_id TEXT PRIMARY KEY,
                            title TEXT,
                            description TEXT,
                            severity TEXT,
                            cvss_score FLOAT,
                            cvss_vector TEXT,
                            source TEXT,
                            published_date TIMESTAMPTZ,
                            last_modified TIMESTAMPTZ,
                            exploit_available BOOLEAN DEFAULT FALSE,
                            patch_available BOOLEAN DEFAULT FALSE,
                            affected_products JSONB,
                            ai_summary TEXT,
                            meta JSONB,
                            last_updated_at TIMESTAMPTZ DEFAULT NOW()
                        );
                        CREATE INDEX IF NOT EXISTS idx_cve_severity ON cve_definitions(severity);
                        CREATE INDEX IF NOT EXISTS idx_cve_cvss ON cve_definitions(cvss_score DESC);
                    """)

                    # Alerts Table
                    await cur.execute("""
                        CREATE TABLE IF NOT EXISTS cve_alerts (
                            alert_id TEXT PRIMARY KEY,
                            cve_id TEXT REFERENCES cve_definitions(cve_id),
                            alert_type TEXT,
                            priority INTEGER,
                            created_at TIMESTAMPTZ NOT NULL,
                            acknowledged BOOLEAN DEFAULT FALSE,
                            acknowledged_by TEXT,
                            notes TEXT,
                            meta JSONB
                        );
                        CREATE INDEX IF NOT EXISTS idx_cve_alerts_created ON cve_alerts(created_at DESC);
                        CREATE INDEX IF NOT EXISTS idx_cve_alerts_priority ON cve_alerts(priority);
                    """)
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")

    @staticmethod
    async def save_cve(cve: CVERecord) -> None:
        """Upsert a CVE record."""
        if not _storage().postgres_enabled:
            return

        try:
            async with get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO cve_definitions (
                            cve_id, title, description, severity, 
                            cvss_score, cvss_vector, source,
                            published_date, last_modified,
                            exploit_available, patch_available,
                            affected_products, ai_summary, meta, last_updated_at
                        ) VALUES (
                            %(cve_id)s, %(title)s, %(description)s, %(severity)s,
                            %(cvss_score)s, %(cvss_vector)s, %(source)s,
                            %(published_date)s, %(last_modified)s,
                            %(exploit_available)s, %(patch_available)s,
                            %(affected_products)s, %(ai_summary)s, %(meta)s, NOW()
                        )
                        ON CONFLICT (cve_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            severity = EXCLUDED.severity,
                            cvss_score = EXCLUDED.cvss_score,
                            cvss_vector = EXCLUDED.cvss_vector,
                            last_modified = EXCLUDED.last_modified,
                            exploit_available = EXCLUDED.exploit_available,
                            patch_available = EXCLUDED.patch_available,
                            affected_products = EXCLUDED.affected_products,
                            ai_summary = EXCLUDED.ai_summary,
                            meta = EXCLUDED.meta,
                            last_updated_at = NOW()
                    """,
                        {
                            "cve_id": cve.cve_id,
                            "title": cve.title,
                            "description": cve.description,
                            "severity": cve.severity.value,
                            "cvss_score": cve.cvss_score,
                            "cvss_vector": cve.cvss.vector_string if cve.cvss else None,
                            "source": cve.source.value,
                            "published_date": cve.published_date,
                            "last_modified": cve.last_modified,
                            "exploit_available": cve.exploit_available,
                            "patch_available": cve.patch_available,
                            "affected_products": json.dumps(
                                [p.model_dump() for p in cve.affected_products]
                            ),
                            "ai_summary": cve.ai_summary,
                            "meta": json.dumps(
                                {
                                    "references": [
                                        r.model_dump() for r in cve.references
                                    ],
                                    "cwe_ids": cve.cwe_ids,
                                }
                            ),
                        },
                    )
        except Exception as e:
            logger.error(f"Failed to save CVE {cve.cve_id}: {e}")

    @staticmethod
    async def save_alert(alert: VulnerabilityAlert) -> None:
        """Save a new vulnerability alert."""
        if not _storage().postgres_enabled:
            return

        try:
            # Ensure CVE exists first
            await CVEHunterDAO.save_cve(alert.cve)

            async with get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO cve_alerts (
                            alert_id, cve_id, alert_type, priority,
                            created_at, acknowledged, acknowledged_by, notes, meta
                        ) VALUES (
                            %(alert_id)s, %(cve_id)s, %(alert_type)s, %(priority)s,
                            %(created_at)s, %(acknowledged)s, %(acknowledged_by)s, %(notes)s, %(meta)s
                        )
                        ON CONFLICT (alert_id) DO NOTHING
                    """,
                        {
                            "alert_id": alert.alert_id,
                            "cve_id": alert.cve.cve_id,
                            "alert_type": alert.alert_type,
                            "priority": alert.priority,
                            "created_at": alert.created_at,
                            "acknowledged": alert.acknowledged,
                            "acknowledged_by": alert.acknowledged_by,
                            "notes": alert.notes,
                            "meta": json.dumps({}),
                        },
                    )
        except Exception as e:
            logger.error(f"Failed to save alert {alert.alert_id}: {e}")

    @staticmethod
    async def load_all_cves() -> list[CVERecord]:
        """Load all CVEs from the database."""
        cves = []
        if not _storage().postgres_enabled:
            return cves

        try:
            # Ensure tables exist (idempotent)
            await CVEHunterDAO.ensure_schema()

            async with get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT 
                            cve_id, title, description, severity, 
                            cvss_score, cvss_vector, source,
                            published_date, last_modified,
                            exploit_available, patch_available,
                            affected_products, ai_summary, meta
                        FROM cve_definitions
                    """)
                    rows = await cur.fetchall()

                    for row in rows:
                        try:
                            # Parse JSON fields if they haven't been automatically adapted
                            # psycopg 3 adapts jsonb to python objects automatically
                            affected_products_val = row[11]
                            if isinstance(affected_products_val, str):
                                affected_products_val = json.loads(
                                    affected_products_val
                                )

                            meta_val = row[13]
                            if isinstance(meta_val, str):
                                meta_val = json.loads(meta_val)
                            meta_val = meta_val or {}

                            # Construct dictionary for Pydantic
                            cve_data = {
                                "cve_id": row[0],
                                "title": row[1],
                                "description": row[2],
                                "severity": row[3],
                                # cvss field requires a dict or object
                                "source": row[6],
                                "published_date": row[7],
                                "last_modified": row[8],
                                "exploit_available": row[9],
                                "patch_available": row[10],
                                "affected_products": affected_products_val,
                                "ai_summary": row[12],
                                # Extract fields stored in meta
                                "cwe_ids": meta_val.get("cwe_ids", []),
                                "references": meta_val.get("references", []),
                                "raw_data": meta_val.get("raw_data"),
                            }

                            # Reconstruct CVSS object if vector/score are present
                            if row[5] or row[4]:
                                cve_data["cvss"] = {
                                    "vector_string": row[5],
                                    "base_score": row[4] or 0.0,
                                    "version": "3.1",
                                }

                            cve = CVERecord(**cve_data)
                            cves.append(cve)
                        except Exception as e:
                            logger.warning(f"Skipping invalid CVE record {row[0]}: {e}")
                            continue

        except Exception as e:
            logger.error(f"Failed to load CVEs: {e}")

        return cves
