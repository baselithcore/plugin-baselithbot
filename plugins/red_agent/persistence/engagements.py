"""Postgres store for Red Agent engagements / campaigns."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import sql

from core.observability.logging import get_logger
from plugins.red_agent.models import (
    EngagementCreate,
    EngagementRecord,
    EngagementStatus,
    EngagementUpdate,
)

from ._conn import acquire, jsonb

logger = get_logger(__name__)


class EngagementPersistence:
    """CRUD for red-team engagements.

    Engagements are the product-level unit of work: scope, objective,
    rules of engagement and the scans attached to that mission.
    """

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def create(
        self,
        record: EngagementRecord,
    ) -> EngagementRecord:
        if not self.available:
            return record
        async with acquire(self.dsn) as conn:
            await conn.execute(
                """
                INSERT INTO red_agent_engagements
                  (id, name, objective, status, rules, tags, tenant_id,
                   created_by, starts_at, ends_at)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                """,
                (
                    str(record.id),
                    record.name,
                    record.objective,
                    record.status.value,
                    jsonb(record.rules.model_dump(mode="json")),
                    record.tags,
                    record.tenant_id,
                    record.created_by,
                    record.starts_at,
                    record.ends_at,
                ),
            )
            await conn.commit()
        return record

    async def from_create(
        self,
        body: EngagementCreate,
        *,
        tenant_id: str | None,
        created_by: str | None,
    ) -> EngagementRecord:
        record = EngagementRecord(
            name=body.name,
            objective=body.objective,
            rules=body.rules,
            tags=body.tags,
            tenant_id=tenant_id,
            created_by=created_by,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
        )
        return await self.create(record)

    async def get(self, engagement_id: UUID) -> EngagementRecord | None:
        if not self.available:
            return None
        try:
            async with acquire(self.dsn) as conn:
                row = await (
                    await conn.execute(
                        "SELECT * FROM red_agent_engagements WHERE id = %s",
                        (str(engagement_id),),
                    )
                ).fetchone()
        except Exception as e:  # noqa: BLE001
            logger.warning("red_agent.engagement.get_failed", extra={"err": str(e)})
            return None
        return EngagementRecord.model_validate(row) if row else None

    async def list(
        self,
        *,
        tenant_id: str | None = None,
        status: EngagementStatus | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EngagementRecord]:
        if not self.available:
            return []
        clauses: list[sql.Composable] = []
        params: list[Any] = []
        if tenant_id is not None:
            clauses.append(sql.SQL("tenant_id = %s"))
            params.append(tenant_id)
        if status is not None:
            clauses.append(sql.SQL("status = %s"))
            params.append(status.value)
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
            SELECT *
              FROM red_agent_engagements
              {where}
          ORDER BY created_at DESC
             LIMIT %s OFFSET %s
            """
        ).format(where=where)
        try:
            async with acquire(self.dsn) as conn:
                rows = await (await conn.execute(query, tuple(params))).fetchall()
        except Exception as e:  # noqa: BLE001
            logger.warning("red_agent.engagement.list_failed", extra={"err": str(e)})
            return []
        return [EngagementRecord.model_validate(row) for row in rows]

    async def update(
        self,
        engagement_id: UUID,
        update: EngagementUpdate,
    ) -> EngagementRecord | None:
        if not self.available:
            return None
        sets: list[sql.Composable] = [sql.SQL("updated_at = now()")]
        params: list[Any] = []
        if update.name is not None:
            sets.append(sql.SQL("name = %s"))
            params.append(update.name)
        if update.objective is not None:
            sets.append(sql.SQL("objective = %s"))
            params.append(update.objective)
        if update.status is not None:
            sets.append(sql.SQL("status = %s"))
            params.append(update.status.value)
            if update.status == EngagementStatus.ARCHIVED:
                sets.append(sql.SQL("archived_at = COALESCE(archived_at, now())"))
        if update.rules is not None:
            sets.append(sql.SQL("rules = %s::jsonb"))
            params.append(jsonb(update.rules.model_dump(mode="json")))
        if update.tags is not None:
            sets.append(sql.SQL("tags = %s"))
            params.append(update.tags)
        if update.starts_at is not None:
            sets.append(sql.SQL("starts_at = %s"))
            params.append(update.starts_at)
        if update.ends_at is not None:
            sets.append(sql.SQL("ends_at = %s"))
            params.append(update.ends_at)
        params.append(str(engagement_id))
        query = sql.SQL(
            """
            UPDATE red_agent_engagements
               SET {sets}
             WHERE id = %s
         RETURNING *
            """
        ).format(sets=sql.SQL(", ").join(sets))
        async with acquire(self.dsn) as conn:
            row = await (await conn.execute(query, tuple(params))).fetchone()
            await conn.commit()
        return EngagementRecord.model_validate(row) if row else None

    async def archive(self, engagement_id: UUID) -> bool:
        updated = await self.update(
            engagement_id,
            EngagementUpdate(status=EngagementStatus.ARCHIVED),
        )
        return updated is not None
