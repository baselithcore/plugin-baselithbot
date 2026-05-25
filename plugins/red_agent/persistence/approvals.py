"""Postgres-backed implementation of the ``ApprovalStore`` protocol."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import DictRow

from core.observability.logging import get_logger

from ._conn import open_conn

logger = get_logger(__name__)


class ApprovalPersistence:
    """Postgres-backed implementation of the ApprovalStore protocol."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def _conn(self) -> psycopg.AsyncConnection[DictRow]:
        return await open_conn(self.dsn)

    async def insert_open(self, scan_id: UUID, reason: str, requested_by: str) -> None:
        if not self.available:
            return
        async with await self._conn() as conn:
            await conn.execute(
                """
                INSERT INTO red_agent_approvals
                  (scan_id, state, reason, requested_by)
                VALUES (%s, 'open', %s, %s)
                ON CONFLICT (scan_id) DO UPDATE
                  SET state = 'open',
                      reason = EXCLUDED.reason,
                      requested_by = EXCLUDED.requested_by,
                      resolved_by = NULL,
                      resolved_at = NULL
                """,
                (str(scan_id), reason, requested_by),
            )
            await conn.commit()

    async def mark_resolved(self, scan_id: UUID, *, approved: bool, actor: str) -> None:
        if not self.available:
            return
        async with await self._conn() as conn:
            await conn.execute(
                """
                UPDATE red_agent_approvals
                   SET state = %s,
                       resolved_by = %s,
                       resolved_at = now()
                 WHERE scan_id = %s
                """,
                (
                    "approved" if approved else "rejected",
                    actor,
                    str(scan_id),
                ),
            )
            await conn.commit()

    async def mark_timeout(self, scan_id: UUID) -> None:
        if not self.available:
            return
        async with await self._conn() as conn:
            await conn.execute(
                """
                UPDATE red_agent_approvals
                   SET state = 'timeout', resolved_at = now()
                 WHERE scan_id = %s AND state = 'open'
                """,
                (str(scan_id),),
            )
            await conn.commit()

    async def list_open(self) -> list[dict[str, Any]]:
        if not self.available:
            return []
        try:
            return await self._list_open_impl()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.approvals.list_open_failed", extra={"err": str(e)}
            )
            return []

    async def _list_open_impl(self) -> list[dict[str, Any]]:
        async with await self._conn() as conn:
            rows = await (
                await conn.execute(
                    """
                    SELECT scan_id, reason, requested_by, opened_at
                      FROM red_agent_approvals
                     WHERE state = 'open'
                  ORDER BY opened_at ASC
                    """
                )
            ).fetchall()
            return [
                {
                    "scan_id": str(r["scan_id"]),
                    "reason": r["reason"],
                    "requested_by": r["requested_by"],
                    "opened_at": r["opened_at"],
                }
                for r in rows
            ]
