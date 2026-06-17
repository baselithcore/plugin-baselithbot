"""Durable Postgres-backed :class:`PitwallStore`.

Uses the shared async connection pool from :mod:`core.db.connection` (the same
pool the rest of the platform shares). Each entity round-trips losslessly through
a JSONB ``data`` column; scalar columns exist only for keying and insertion-order
reads. Schema self-initializes on :meth:`initialize` (idempotent DDL), mirroring
:class:`core.storage.postgres.PostgresStorage`.
"""

from __future__ import annotations

from psycopg.rows import dict_row

from core.config import get_storage_config
from core.db.connection import get_async_cursor
from core.observability.logging import get_logger

from ..models import Recommendation, StintState
from ..session_models import AuditRecord, RaceSession, RecommendationAck
from ._pg_util import _blob
from ._protocol import MAX_SNAPSHOTS_PER_CAR
from ._schema import _CHILD_TABLES, SCHEMA_DDL

logger = get_logger(__name__)


class PostgresPitwallStore:
    """Durable :class:`PitwallStore` backed by PostgreSQL JSONB tables."""

    async def initialize(self) -> None:
        """Create the pit-wall tables if absent. Fails fast if Postgres is off."""
        if not get_storage_config().postgres_enabled:
            raise RuntimeError(
                "pitwall persistence='postgres' requires POSTGRES_ENABLED=true."
            )
        async with get_async_cursor() as cur:
            await cur.execute(SCHEMA_DDL)
        logger.info("pitwall_postgres_store_initialized")

    # -- Sessions ----------------------------------------------------------

    async def save_session(self, session: RaceSession) -> RaceSession:
        sql = """
            INSERT INTO pitwall_sessions (tenant_id, id, data, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (tenant_id, id) DO UPDATE
                SET data = EXCLUDED.data, updated_at = NOW()
        """
        async with get_async_cursor() as cur:
            await cur.execute(sql, (session.tenant_id, session.id, _blob(session)))
        return session

    async def get_session(self, tenant_id: str, session_id: str) -> RaceSession | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore[call-overload]
            await cur.execute(
                "SELECT data FROM pitwall_sessions WHERE tenant_id = %s AND id = %s",
                (tenant_id, session_id),
            )
            row = await cur.fetchone()
        return RaceSession.model_validate(row["data"]) if row else None

    async def list_sessions(self, tenant_id: str) -> list[RaceSession]:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore[call-overload]
            await cur.execute(
                "SELECT data FROM pitwall_sessions WHERE tenant_id = %s "
                "ORDER BY created_at DESC",
                (tenant_id,),
            )
            rows = await cur.fetchall()
        return [RaceSession.model_validate(r["data"]) for r in rows]

    async def delete_session(self, tenant_id: str, session_id: str) -> bool:
        async with get_async_cursor() as cur:
            for table in _CHILD_TABLES:
                await cur.execute(
                    f"DELETE FROM {table} WHERE tenant_id = %s AND session_id = %s",
                    (tenant_id, session_id),
                )
            await cur.execute(
                "DELETE FROM pitwall_sessions WHERE tenant_id = %s AND id = %s",
                (tenant_id, session_id),
            )
            deleted = cur.rowcount
        return bool(deleted)

    # -- Recommendations ---------------------------------------------------

    async def save_recommendation(
        self, tenant_id: str, session_id: str, rec: Recommendation
    ) -> Recommendation:
        sql = """
            INSERT INTO pitwall_recommendations
                (tenant_id, session_id, id, car_id, data)
            VALUES (%s, %s, %s, %s, %s)
        """
        async with get_async_cursor() as cur:
            await cur.execute(
                sql, (tenant_id, session_id, rec.id, rec.car_id, _blob(rec))
            )
        return rec

    async def get_recommendation(
        self, tenant_id: str, session_id: str, rec_id: str
    ) -> Recommendation | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore[call-overload]
            await cur.execute(
                "SELECT data FROM pitwall_recommendations "
                "WHERE tenant_id = %s AND session_id = %s AND id = %s "
                "ORDER BY seq DESC LIMIT 1",
                (tenant_id, session_id, rec_id),
            )
            row = await cur.fetchone()
        return Recommendation.model_validate(row["data"]) if row else None

    async def list_recommendations(
        self,
        tenant_id: str,
        session_id: str,
        car_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Recommendation], int]:
        where = "tenant_id = %s AND session_id = %s"
        params: list[object] = [tenant_id, session_id]
        if car_id is not None:
            where += " AND car_id = %s"
            params.append(car_id)
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore[call-overload]
            await cur.execute(
                f"SELECT COUNT(*) AS n FROM pitwall_recommendations WHERE {where}",
                tuple(params),
            )
            total = int((await cur.fetchone())["n"])
            await cur.execute(
                f"SELECT data FROM pitwall_recommendations WHERE {where} "
                "ORDER BY seq DESC LIMIT %s OFFSET %s",
                (*params, limit, offset),
            )
            rows = await cur.fetchall()
        return [Recommendation.model_validate(r["data"]) for r in rows], total

    # -- Audit -------------------------------------------------------------

    async def add_audit(self, record: AuditRecord) -> None:
        async with get_async_cursor() as cur:
            await cur.execute(
                "INSERT INTO pitwall_audit (tenant_id, session_id, data) "
                "VALUES (%s, %s, %s)",
                (record.tenant_id, record.session_id, _blob(record)),
            )

    async def list_audit(
        self,
        tenant_id: str,
        session_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditRecord], int]:
        where = "tenant_id = %s"
        params: list[object] = [tenant_id]
        if session_id is not None:
            where += " AND session_id = %s"
            params.append(session_id)
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore[call-overload]
            await cur.execute(
                f"SELECT COUNT(*) AS n FROM pitwall_audit WHERE {where}", tuple(params)
            )
            total = int((await cur.fetchone())["n"])
            await cur.execute(
                f"SELECT data FROM pitwall_audit WHERE {where} "
                "ORDER BY seq DESC LIMIT %s OFFSET %s",
                (*params, limit, offset),
            )
            rows = await cur.fetchall()
        return [AuditRecord.model_validate(r["data"]) for r in rows], total

    # -- Acks --------------------------------------------------------------

    async def save_ack(self, ack: RecommendationAck) -> RecommendationAck:
        async with get_async_cursor() as cur:
            await cur.execute(
                "INSERT INTO pitwall_acks "
                "(tenant_id, session_id, recommendation_id, data) "
                "VALUES (%s, %s, %s, %s)",
                (ack.tenant_id, ack.session_id, ack.recommendation_id, _blob(ack)),
            )
        return ack

    async def list_acks(
        self,
        tenant_id: str,
        session_id: str,
        recommendation_id: str | None = None,
    ) -> list[RecommendationAck]:
        where = "tenant_id = %s AND session_id = %s"
        params: list[object] = [tenant_id, session_id]
        if recommendation_id is not None:
            where += " AND recommendation_id = %s"
            params.append(recommendation_id)
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore[call-overload]
            await cur.execute(
                f"SELECT data FROM pitwall_acks WHERE {where} ORDER BY seq DESC",
                tuple(params),
            )
            rows = await cur.fetchall()
        return [RecommendationAck.model_validate(r["data"]) for r in rows]

    # -- Stint snapshots ---------------------------------------------------

    async def add_stint_snapshot(
        self, tenant_id: str, session_id: str, stint: StintState
    ) -> None:
        async with get_async_cursor() as cur:
            await cur.execute(
                "INSERT INTO pitwall_snapshots (tenant_id, session_id, car_id, data) "
                "VALUES (%s, %s, %s, %s)",
                (tenant_id, session_id, stint.car_id, _blob(stint)),
            )

    async def list_stint_snapshots(
        self, tenant_id: str, session_id: str, car_id: str, limit: int = 200
    ) -> list[StintState]:
        limit = min(limit, MAX_SNAPSHOTS_PER_CAR)
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore[call-overload]
            await cur.execute(
                "SELECT data FROM pitwall_snapshots "
                "WHERE tenant_id = %s AND session_id = %s AND car_id = %s "
                "ORDER BY seq DESC LIMIT %s",
                (tenant_id, session_id, car_id, limit),
            )
            rows = await cur.fetchall()
        return [StintState.model_validate(r["data"]) for r in reversed(rows)]


__all__ = ["PostgresPitwallStore"]
