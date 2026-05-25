"""Persistence for ``red_agent_agent_telemetry`` (partitioned hot tier).

Append-only insert path used by the gRPC servicer to durably record
events arriving from connected daemons. Reads are served from the
same table for now; Phase 2 introduces a hot/warm tier split with
ClickHouse / Loki for fleet-wide analytical queries.

Writes are batched at the application layer: the gRPC handler calls
:meth:`AgentTelemetryStore.insert_batch` with the entire decoded
``TelemetryBatch`` so the round trip cost is amortized over N events.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from psycopg import sql

from core.observability.logging import get_logger

from ._conn import open_conn
from ._tenant import tenant_scope

logger = get_logger(__name__)


VALID_SEVERITIES = {"info", "low", "medium", "high", "critical"}


def _normalize_severity(raw: str) -> str:
    s = (raw or "info").lower()
    return s if s in VALID_SEVERITIES else "info"


class AgentTelemetryStore:
    """Append-only writer for the partitioned telemetry table."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def insert_batch(
        self,
        *,
        tenant_id: str,
        agent_uuid: UUID,
        batch_id: UUID,
        events: list[dict[str, Any]],
    ) -> int:
        """Insert all events in a single transaction.

        Each ``event`` dict is shaped per the proto ``TelemetryEvent``:
        ``observed_at``, ``kind``, ``severity``, ``attributes``,
        ``correlation_id``. Returns the number of rows persisted.
        Failures are logged at WARN and surface as 0 — telemetry must
        never block the gRPC stream.
        """
        if not self.available or not events:
            return 0
        try:
            return await self._insert_impl(
                tenant_id=tenant_id,
                agent_uuid=agent_uuid,
                batch_id=batch_id,
                events=events,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.telemetry.insert_failed",
                extra={
                    "agent_uuid": str(agent_uuid),
                    "batch_id": str(batch_id),
                    "error": str(e),
                    "event_count": len(events),
                },
            )
            return 0

    async def _insert_impl(
        self,
        *,
        tenant_id: str,
        agent_uuid: UUID,
        batch_id: UUID,
        events: list[dict[str, Any]],
    ) -> int:
        rows: list[tuple[Any, ...]] = []
        for seq, event in enumerate(events):
            observed_at = event.get("observed_at") or datetime.now(timezone.utc)
            rows.append(
                (
                    str(uuid4()),
                    tenant_id,
                    str(agent_uuid),
                    observed_at,
                    event.get("kind", "unknown"),
                    _normalize_severity(event.get("severity", "info")),
                    json.dumps(event.get("attributes") or {}, default=str),
                    event.get("correlation_id") or None,
                    str(batch_id),
                    seq,
                )
            )
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                async with conn.cursor() as cur:
                    await cur.executemany(
                        """
                        INSERT INTO red_agent_agent_telemetry (
                            id, tenant_id, agent_uuid, observed_at,
                            kind, severity, attributes, correlation_id,
                            batch_id, batch_seq
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s
                        )
                        """,
                        rows,
                    )
        return len(rows)

    async def list_recent(
        self,
        *,
        tenant_id: str,
        agent_uuid: UUID | None = None,
        kind: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Read recent telemetry. Used by the fleet UI's per-agent view."""
        if not self.available:
            return []
        clauses: list[sql.Composable] = []
        params: list[Any] = []
        if agent_uuid is not None:
            clauses.append(sql.SQL("agent_uuid = %s"))
            params.append(str(agent_uuid))
        if kind is not None:
            clauses.append(sql.SQL("kind = %s"))
            params.append(kind)
        where = (
            sql.SQL("WHERE ") + sql.SQL(" AND ").join(clauses)
            if clauses
            else sql.SQL("")
        )
        params.append(limit)
        query = sql.SQL(
            """
            SELECT id, tenant_id, agent_uuid, observed_at, received_at,
                   kind, severity, attributes, correlation_id, batch_id
              FROM red_agent_agent_telemetry
              {where}
          ORDER BY observed_at DESC
             LIMIT %s
            """
        ).format(where=where)
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                rows = await (await conn.execute(query, tuple(params))).fetchall()
                return [
                    {
                        "id": str(r["id"]),
                        "tenant_id": r["tenant_id"],
                        "agent_uuid": str(r["agent_uuid"]),
                        "observed_at": r["observed_at"],
                        "received_at": r["received_at"],
                        "kind": r["kind"],
                        "severity": r["severity"],
                        "attributes": r.get("attributes") or {},
                        "correlation_id": r.get("correlation_id"),
                        "batch_id": str(r["batch_id"]),
                    }
                    for r in rows
                ]
