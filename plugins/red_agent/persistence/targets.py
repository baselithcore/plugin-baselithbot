"""CRUD + posture queries for the persistent ``red_agent_targets`` table.

Targets are first-class projects: each one accumulates scans (runs) and
findings over time. Scope, scanner profile and schedule live here so the
operator configures once and scans inherit consistent settings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List
from uuid import UUID

from psycopg import sql

from core.observability.logging import get_logger
from plugins.red_agent.models import (
    TargetCreate,
    TargetKind,
    TargetRecord,
    TargetUpdate,
)

from ._conn import jsonb
from ._target_posture import TargetPostureMixin

logger = get_logger(__name__)


def _row_to_record(row: dict[str, Any]) -> TargetRecord:
    rid = row["id"]
    return TargetRecord(
        id=rid if isinstance(rid, UUID) else UUID(str(rid)),
        kind=TargetKind(row["kind"]),
        name=row["name"],
        value=row["value"],
        environment=row.get("environment"),
        owner=row.get("owner"),
        tags=list(row.get("tags") or []),
        profile=row.get("profile") or {},
        schedule_cron=row.get("schedule_cron"),
        scope_overrides=row.get("scope_overrides") or {},
        description=row.get("description"),
        tenant_id=row.get("tenant_id"),
        created_by=row.get("created_by"),
        created_at=row.get("created_at") or datetime.now(timezone.utc),
        updated_at=row.get("updated_at") or datetime.now(timezone.utc),
        last_scan_at=row.get("last_scan_at"),
        archived_at=row.get("archived_at"),
    )


class TargetPersistence(TargetPostureMixin):
    """CRUD + posture queries for the persistent ``red_agent_targets`` table."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def create(
        self,
        body: TargetCreate,
        *,
        tenant_id: str | None,
        created_by: str,
    ) -> TargetRecord:
        if not self.available:
            raise RuntimeError("red_agent: postgres not configured")
        record = TargetRecord(
            kind=body.kind,
            name=body.name,
            value=body.value,
            environment=body.environment,
            owner=body.owner,
            tags=body.tags,
            profile=body.profile,
            schedule_cron=body.schedule_cron,
            scope_overrides=body.scope_overrides,
            description=body.description,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        async with await self._conn() as conn:
            await conn.execute(
                """
                INSERT INTO red_agent_targets
                  (id, kind, name, value, environment, owner, tags, profile,
                   schedule_cron, scope_overrides, description, tenant_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s, %s)
                ON CONFLICT (tenant_id, kind, value) DO UPDATE
                   SET name = EXCLUDED.name,
                       environment = EXCLUDED.environment,
                       owner = EXCLUDED.owner,
                       tags = EXCLUDED.tags,
                       profile = EXCLUDED.profile,
                       schedule_cron = EXCLUDED.schedule_cron,
                       scope_overrides = EXCLUDED.scope_overrides,
                       description = EXCLUDED.description,
                       updated_at = now(),
                       archived_at = NULL
                RETURNING id
                """,
                (
                    str(record.id),
                    record.kind.value,
                    record.name,
                    record.value,
                    record.environment,
                    record.owner,
                    record.tags,
                    jsonb(record.profile),
                    record.schedule_cron,
                    jsonb(record.scope_overrides),
                    record.description,
                    tenant_id,
                    created_by,
                ),
            )
            await conn.commit()
        existing = await self.get_by_value(
            record.kind, record.value, tenant_id=tenant_id
        )
        return existing or record

    async def get(self, target_id: UUID) -> TargetRecord | None:
        if not self.available:
            return None
        async with await self._conn() as conn:
            row = await (
                await conn.execute(
                    "SELECT * FROM red_agent_targets WHERE id = %s",
                    (str(target_id),),
                )
            ).fetchone()
            return _row_to_record(dict(row)) if row else None

    async def get_by_value(
        self, kind: TargetKind, value: str, *, tenant_id: str | None
    ) -> TargetRecord | None:
        if not self.available:
            return None
        async with await self._conn() as conn:
            row = await (
                await conn.execute(
                    """
                    SELECT * FROM red_agent_targets
                     WHERE kind = %s AND value = %s
                       AND (tenant_id IS NOT DISTINCT FROM %s)
                    """,
                    (kind.value, value, tenant_id),
                )
            ).fetchone()
            return _row_to_record(dict(row)) if row else None

    async def list(
        self,
        *,
        tenant_id: str | None = None,
        kind: TargetKind | None = None,
        environment: str | None = None,
        include_archived: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> List[TargetRecord]:
        if not self.available:
            return []
        try:
            return await self._list_impl(
                tenant_id=tenant_id,
                kind=kind,
                environment=environment,
                include_archived=include_archived,
                limit=limit,
                offset=offset,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("red_agent.targets.list_failed", extra={"err": str(e)})
            return []

    async def _list_impl(
        self,
        *,
        tenant_id: str | None,
        kind: TargetKind | None,
        environment: str | None,
        include_archived: bool,
        limit: int,
        offset: int,
    ) -> List[TargetRecord]:
        clauses: List[sql.Composable] = []
        params: List[Any] = []
        if tenant_id is not None:
            clauses.append(sql.SQL("tenant_id = %s"))
            params.append(tenant_id)
        if kind is not None:
            clauses.append(sql.SQL("kind = %s"))
            params.append(kind.value)
        if environment is not None:
            clauses.append(sql.SQL("environment = %s"))
            params.append(environment)
        if not include_archived:
            clauses.append(sql.SQL("archived_at IS NULL"))
        where = (
            sql.SQL("WHERE ") + sql.SQL(" AND ").join(clauses)
            if clauses
            else sql.SQL("")
        )
        params.extend([limit, offset])
        query = sql.SQL(
            """
            SELECT * FROM red_agent_targets
              {where}
          ORDER BY COALESCE(last_scan_at, created_at) DESC
             LIMIT %s OFFSET %s
            """
        ).format(where=where)
        async with await self._conn() as conn:
            rows = await (await conn.execute(query, tuple(params))).fetchall()
            return [_row_to_record(dict(r)) for r in rows]

    async def update(
        self, target_id: UUID, body: TargetUpdate, actor: str
    ) -> TargetRecord | None:
        if not self.available:
            return None
        sets: List[sql.Composable] = []
        params: List[Any] = []
        for field in ("name", "environment", "owner", "schedule_cron", "description"):
            value = getattr(body, field)
            if value is not None:
                sets.append(sql.SQL("{} = %s").format(sql.Identifier(field)))
                params.append(value)
        if body.tags is not None:
            sets.append(sql.SQL("tags = %s"))
            params.append(body.tags)
        if body.profile is not None:
            sets.append(sql.SQL("profile = %s::jsonb"))
            params.append(jsonb(body.profile))
        if body.scope_overrides is not None:
            sets.append(sql.SQL("scope_overrides = %s::jsonb"))
            params.append(jsonb(body.scope_overrides))
        if body.archived is not None:
            if body.archived:
                sets.append(sql.SQL("archived_at = now()"))
            else:
                sets.append(sql.SQL("archived_at = NULL"))
        if not sets:
            return await self.get(target_id)
        sets.append(sql.SQL("updated_at = now()"))
        del actor  # reserved for audit hook
        params.append(str(target_id))
        query = sql.SQL("UPDATE red_agent_targets SET {sets} WHERE id = %s").format(
            sets=sql.SQL(", ").join(sets)
        )
        async with await self._conn() as conn:
            await conn.execute(query, tuple(params))
            await conn.commit()
        return await self.get(target_id)

    async def archive(self, target_id: UUID) -> bool:
        """Soft-delete: stamp ``archived_at`` and bump ``updated_at``.

        Idempotent — re-archiving a target leaves the original timestamp.
        Returns True if a row was updated (i.e. the target exists and was
        not already archived).
        """
        if not self.available:
            return False
        async with await self._conn() as conn:
            cur = await conn.execute(
                """
                UPDATE red_agent_targets
                   SET archived_at = COALESCE(archived_at, now()),
                       updated_at  = now()
                 WHERE id = %s
                """,
                (str(target_id),),
            )
            await conn.commit()
            return (cur.rowcount or 0) > 0

    async def has_runs(self, target_id: UUID) -> bool:
        if not self.available:
            return False
        async with await self._conn() as conn:
            row = await (
                await conn.execute(
                    "SELECT 1 FROM red_agent_scans WHERE target_id = %s LIMIT 1",
                    (str(target_id),),
                )
            ).fetchone()
            return row is not None

    async def hard_delete(self, target_id: UUID, *, purge_runs: bool) -> bool:
        """Hard-delete a target.

        ``red_agent_scans.target_id`` has ``ON DELETE SET NULL`` so by
        default the target row vanishes while its scan history lingers
        (orphaned but readable). When ``purge_runs`` is true, every scan
        attached to the target is deleted first, which cascades to its
        findings via FK.

        Returns True if the target row was deleted.
        """
        if not self.available:
            return False
        async with await self._conn() as conn:
            if purge_runs:
                await conn.execute(
                    "DELETE FROM red_agent_scans WHERE target_id = %s",
                    (str(target_id),),
                )
            cur = await conn.execute(
                "DELETE FROM red_agent_targets WHERE id = %s",
                (str(target_id),),
            )
            await conn.commit()
            return (cur.rowcount or 0) > 0

    async def list_activity(
        self, target_id: UUID, *, limit: int = 100
    ) -> List[dict[str, Any]]:
        """Audit events whose ``scan_id`` belongs to a scan against this target."""
        if not self.available:
            return []
        async with await self._conn() as conn:
            rows = await (
                await conn.execute(
                    """
                    SELECT a.id, a.scan_id, a.actor, a.event, a.payload, a.created_at
                      FROM red_agent_audit a
                      JOIN red_agent_scans s ON s.id = a.scan_id
                     WHERE s.target_id = %s
                  ORDER BY a.created_at DESC
                     LIMIT %s
                    """,
                    (str(target_id), limit),
                )
            ).fetchall()
            return [
                {
                    "id": int(r["id"]),
                    "scan_id": str(r["scan_id"]) if r.get("scan_id") else None,
                    "actor": r.get("actor"),
                    "event": r["event"],
                    "payload": r.get("payload") or {},
                    "created_at": r.get("created_at"),
                }
                for r in rows
            ]
