"""CRUD for ``red_agent_agents`` (endpoint daemon registry)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import sql

from core.observability.logging import get_logger
from plugins.red_agent.agent_models import (
    AgentArch,
    AgentOS,
    AgentRecord,
    AgentStatus,
)

from ._conn import jsonb, open_conn
from ._tenant import tenant_scope

logger = get_logger(__name__)


def _row_to_record(row: dict[str, Any]) -> AgentRecord:
    return AgentRecord(
        agent_uuid=row["agent_uuid"]
        if isinstance(row["agent_uuid"], UUID)
        else UUID(str(row["agent_uuid"])),
        tenant_id=row["tenant_id"],
        os=AgentOS(row["os"]),
        os_version=row.get("os_version"),
        kernel_version=row.get("kernel_version"),
        arch=AgentArch(row["arch"]),
        hostname=row.get("hostname"),
        boot_id=row.get("boot_id"),
        cpu_count=row.get("cpu_count"),
        mem_total_bytes=row.get("mem_total_bytes"),
        daemon_version=row.get("daemon_version"),
        protocol_version=int(row["protocol_version"]),
        capabilities=list(row.get("capabilities") or []),
        labels=row.get("labels") or {},
        status=AgentStatus(row["status"]),
        last_seen_at=row.get("last_seen_at"),
        last_disconnect_reason=row.get("last_disconnect_reason"),
        enrolled_at=row["enrolled_at"],
        enrolled_by=row.get("enrolled_by"),
        archived_at=row.get("archived_at"),
    )


class AgentPersistence:
    """CRUD for the agent registry, with tenant-scoped RLS."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def upsert(
        self,
        record: AgentRecord,
        *,
        tenant_id: str,
    ) -> AgentRecord:
        """Insert or update an agent row.

        Used at enrollment (insert) and at every ``AgentHello`` to refresh
        platform metadata (update). The ON CONFLICT clause does not touch
        ``enrolled_at`` / ``enrolled_by`` so the original enrollment audit
        is preserved.
        """
        if not self.available:
            raise RuntimeError("red_agent: postgres not configured")
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                await conn.execute(
                    """
                    INSERT INTO red_agent_agents (
                        agent_uuid, tenant_id, os, os_version, kernel_version,
                        arch, hostname, boot_id, cpu_count, mem_total_bytes,
                        daemon_version, protocol_version, capabilities, labels,
                        status, last_seen_at, enrolled_at, enrolled_by
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s::jsonb,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (agent_uuid) DO UPDATE SET
                        os = EXCLUDED.os,
                        os_version = EXCLUDED.os_version,
                        kernel_version = EXCLUDED.kernel_version,
                        arch = EXCLUDED.arch,
                        hostname = EXCLUDED.hostname,
                        boot_id = EXCLUDED.boot_id,
                        cpu_count = EXCLUDED.cpu_count,
                        mem_total_bytes = EXCLUDED.mem_total_bytes,
                        daemon_version = EXCLUDED.daemon_version,
                        protocol_version = EXCLUDED.protocol_version,
                        capabilities = EXCLUDED.capabilities,
                        labels = EXCLUDED.labels,
                        status = EXCLUDED.status,
                        last_seen_at = COALESCE(EXCLUDED.last_seen_at, red_agent_agents.last_seen_at)
                    """,
                    (
                        str(record.agent_uuid),
                        tenant_id,
                        record.os.value,
                        record.os_version,
                        record.kernel_version,
                        record.arch.value,
                        record.hostname,
                        record.boot_id,
                        record.cpu_count,
                        record.mem_total_bytes,
                        record.daemon_version,
                        record.protocol_version,
                        record.capabilities,
                        jsonb(record.labels),
                        record.status.value,
                        record.last_seen_at,
                        record.enrolled_at,
                        record.enrolled_by,
                    ),
                )
        return await self.get(record.agent_uuid, tenant_id=tenant_id) or record

    async def get(self, agent_uuid: UUID, *, tenant_id: str) -> AgentRecord | None:
        if not self.available:
            return None
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                row = await (
                    await conn.execute(
                        "SELECT * FROM red_agent_agents WHERE agent_uuid = %s",
                        (str(agent_uuid),),
                    )
                ).fetchone()
                return _row_to_record(dict(row)) if row else None

    async def list(
        self,
        *,
        tenant_id: str,
        status: AgentStatus | None = None,
        os: AgentOS | None = None,
        labels_match: dict[str, Any] | None = None,
        include_archived: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> list[AgentRecord]:
        if not self.available:
            return []
        clauses: list[sql.Composable] = []
        params: list[Any] = []
        if status is not None:
            clauses.append(sql.SQL("status = %s"))
            params.append(status.value)
        if os is not None:
            clauses.append(sql.SQL("os = %s"))
            params.append(os.value)
        if labels_match:
            clauses.append(sql.SQL("labels @> %s::jsonb"))
            params.append(jsonb(labels_match))
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
            SELECT * FROM red_agent_agents
              {where}
          ORDER BY COALESCE(last_seen_at, enrolled_at) DESC
             LIMIT %s OFFSET %s
            """
        ).format(where=where)
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                rows = await (await conn.execute(query, tuple(params))).fetchall()
                return [_row_to_record(dict(r)) for r in rows]

    async def update_status(
        self,
        agent_uuid: UUID,
        *,
        tenant_id: str,
        status: AgentStatus,
        last_seen_at: Any | None = None,
        last_disconnect_reason: str | None = None,
    ) -> bool:
        if not self.available:
            return False
        sets: list[sql.Composable] = [sql.SQL("status = %s")]
        params: list[Any] = [status.value]
        if last_seen_at is not None:
            sets.append(sql.SQL("last_seen_at = %s"))
            params.append(last_seen_at)
        if last_disconnect_reason is not None:
            sets.append(sql.SQL("last_disconnect_reason = %s"))
            params.append(last_disconnect_reason)
        params.append(str(agent_uuid))
        query = sql.SQL(
            "UPDATE red_agent_agents SET {sets} WHERE agent_uuid = %s"
        ).format(sets=sql.SQL(", ").join(sets))
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                result = await conn.execute(query, tuple(params))
                return (result.rowcount or 0) > 0

    async def archive(self, agent_uuid: UUID, *, tenant_id: str) -> bool:
        if not self.available:
            return False
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                result = await conn.execute(
                    """
                    UPDATE red_agent_agents
                       SET status = 'disabled', archived_at = now()
                     WHERE agent_uuid = %s
                    """,
                    (str(agent_uuid),),
                )
                return (result.rowcount or 0) > 0
