"""Postgres governance mixin: versioning, audit trail, and applied changes.

Extracted from :mod:`._postgres` purely to keep each file under the size cap; the
methods here are part of :class:`PostgresProcessStore`'s contract and behave
identically to the in-memory backend. They depend only on the shared async
connection pool and the :func:`_blob` JSONB adapter, so the split is mechanical
(no behavioural change).
"""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row

from core.db.connection import get_async_cursor

from ..apply_models import AppliedChange
from ..versioning_models import AuditEvent, ProcessVersion
from ._pg_util import _blob


class _PgGovernanceMixin:
    """Versioning + audit + applied-change persistence for the Postgres store."""

    # -- Versioning & audit ------------------------------------------------

    async def add_version(
        self, tenant_id: str, version: ProcessVersion
    ) -> ProcessVersion:
        sql = """
            INSERT INTO bop_versions
                (tenant_id, process_id, version, content_hash, data)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, process_id, version) DO NOTHING
        """
        async with get_async_cursor() as cur:
            await cur.execute(
                sql,
                (
                    tenant_id,
                    version.process_id,
                    version.version,
                    version.content_hash,
                    _blob(version),
                ),
            )
        return version

    async def list_versions(
        self, tenant_id: str, process_id: str
    ) -> list[ProcessVersion]:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_versions WHERE tenant_id = %s AND process_id = %s "
                "ORDER BY version DESC",
                (tenant_id, process_id),
            )
            rows = await cur.fetchall()
        return [ProcessVersion.model_validate(r["data"]) for r in rows]

    async def get_version(
        self, tenant_id: str, process_id: str, version: int
    ) -> ProcessVersion | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_versions WHERE tenant_id = %s "
                "AND process_id = %s AND version = %s",
                (tenant_id, process_id, version),
            )
            row = await cur.fetchone()
        return ProcessVersion.model_validate(row["data"]) if row else None

    async def latest_version(
        self, tenant_id: str, process_id: str
    ) -> ProcessVersion | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_versions WHERE tenant_id = %s AND process_id = %s "
                "ORDER BY version DESC LIMIT 1",
                (tenant_id, process_id),
            )
            row = await cur.fetchone()
        return ProcessVersion.model_validate(row["data"]) if row else None

    async def add_audit(self, tenant_id: str, event: AuditEvent) -> None:
        sql = "INSERT INTO bop_audit (tenant_id, process_id, data) VALUES (%s, %s, %s)"
        async with get_async_cursor() as cur:
            await cur.execute(sql, (tenant_id, event.process_id, _blob(event)))

    async def list_audit(
        self, tenant_id: str, process_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        params: tuple[Any, ...] = (tenant_id,)
        sql = "SELECT data FROM bop_audit WHERE tenant_id = %s"
        if process_id is not None:
            sql += " AND process_id = %s"
            params = (tenant_id, process_id)
        sql += " ORDER BY seq DESC LIMIT %s"
        params = (*params, max(0, limit))
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(sql, params)
            rows = await cur.fetchall()
        return [AuditEvent.model_validate(r["data"]) for r in rows]

    # -- Applied changes ---------------------------------------------------

    async def save_change(self, tenant_id: str, change: AppliedChange) -> AppliedChange:
        sql = """
            INSERT INTO bop_changes
                (tenant_id, id, process_id, status, applied_at, data)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, id) DO UPDATE
                SET status = EXCLUDED.status, data = EXCLUDED.data
        """
        async with get_async_cursor() as cur:
            await cur.execute(
                sql,
                (
                    tenant_id,
                    change.id,
                    change.process_id,
                    change.status.value,
                    change.applied_at,
                    _blob(change),
                ),
            )
        return change

    async def get_change(self, tenant_id: str, change_id: str) -> AppliedChange | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_changes WHERE tenant_id = %s AND id = %s",
                (tenant_id, change_id),
            )
            row = await cur.fetchone()
        return AppliedChange.model_validate(row["data"]) if row else None

    async def list_changes(
        self, tenant_id: str, process_id: str
    ) -> list[AppliedChange]:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_changes WHERE tenant_id = %s AND process_id = %s "
                "ORDER BY applied_at DESC",
                (tenant_id, process_id),
            )
            rows = await cur.fetchall()
        return [AppliedChange.model_validate(r["data"]) for r in rows]


__all__ = ["_PgGovernanceMixin"]
