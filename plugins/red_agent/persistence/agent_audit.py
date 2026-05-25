"""Append-only, hash-chained audit log for endpoint-daemon events.

Distinct from the scan-focused ``red_agent_audit`` table. Every
enrollment, cert rotation, revocation, command authorization, and
policy distribution event lands here. Rows are hash-chained per
tenant: each row's ``row_hash`` is
``SHA-256(prev_hash || canonical(payload))``. A tampered or deleted
row breaks downstream verification. The chain is computed application
side (not in a trigger) so it remains auditable in code review.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from psycopg import sql

from core.observability.logging import get_logger

from ._conn import open_conn
from ._tenant import tenant_scope

logger = get_logger(__name__)


def _canonical_json(payload: dict[str, Any]) -> bytes:
    """Stable canonical JSON for hashing.

    ``sort_keys=True`` and no whitespace gives a deterministic byte
    representation across reordered dicts. ``default=str`` accommodates
    UUID / datetime values that Pydantic may emit.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


class AgentAuditLog:
    """Append rows to ``red_agent_agent_audit_log`` with hash chaining."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def record(
        self,
        *,
        tenant_id: str,
        actor: str,
        event: str,
        payload: dict[str, Any],
        agent_uuid: UUID | None = None,
    ) -> None:
        """Append one event to the chain.

        Failures are logged at ERROR but never raised: the audit path
        must not block the primary operation. Production deployments
        should monitor the ``red_agent.agent_audit.append_failed``
        log line.
        """
        if not self.available:
            return
        try:
            await self._append(
                tenant_id=tenant_id,
                actor=actor,
                event=event,
                payload=payload,
                agent_uuid=agent_uuid,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(
                "red_agent.agent_audit.append_failed",
                extra={
                    "event": event,
                    "agent_uuid": str(agent_uuid) if agent_uuid else None,
                    "error": str(e),
                },
            )

    async def _append(
        self,
        *,
        tenant_id: str,
        actor: str,
        event: str,
        payload: dict[str, Any],
        agent_uuid: UUID | None,
    ) -> None:
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                prev = await (
                    await conn.execute(
                        """
                        SELECT row_hash FROM red_agent_agent_audit_log
                         WHERE tenant_id = %s
                      ORDER BY id DESC
                         LIMIT 1
                        """,
                        (tenant_id,),
                    )
                ).fetchone()
                prev_hash: bytes = bytes(prev["row_hash"]) if prev else b""
                row_hash = hashlib.sha256(prev_hash + _canonical_json(payload)).digest()
                await conn.execute(
                    """
                    INSERT INTO red_agent_agent_audit_log (
                        tenant_id, agent_uuid, actor, event,
                        payload, prev_hash, row_hash
                    ) VALUES (
                        %s, %s, %s, %s, %s::jsonb, %s, %s
                    )
                    """,
                    (
                        tenant_id,
                        str(agent_uuid) if agent_uuid else None,
                        actor,
                        event,
                        json.dumps(payload, default=str),
                        prev_hash if prev else None,
                        row_hash,
                    ),
                )

    async def list(
        self,
        *,
        tenant_id: str,
        agent_uuid: UUID | None = None,
        event: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self.available:
            return []
        clauses: list[sql.Composable] = []
        params: list[Any] = []
        if agent_uuid is not None:
            clauses.append(sql.SQL("agent_uuid = %s"))
            params.append(str(agent_uuid))
        if event is not None:
            clauses.append(sql.SQL("event = %s"))
            params.append(event)
        where = (
            sql.SQL("WHERE ") + sql.SQL(" AND ").join(clauses)
            if clauses
            else sql.SQL("")
        )
        params.extend([limit, offset])
        query = sql.SQL(
            """
            SELECT id, agent_uuid, actor, event, payload,
                   occurred_at, prev_hash, row_hash
              FROM red_agent_agent_audit_log
              {where}
           ORDER BY id DESC
              LIMIT %s OFFSET %s
            """
        ).format(where=where)
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                rows = await (await conn.execute(query, tuple(params))).fetchall()
                return [
                    {
                        "id": int(r["id"]),
                        "agent_uuid": (
                            str(r["agent_uuid"]) if r.get("agent_uuid") else None
                        ),
                        "actor": r["actor"],
                        "event": r["event"],
                        "payload": r.get("payload") or {},
                        "occurred_at": r["occurred_at"],
                        "prev_hash": (
                            bytes(r["prev_hash"]).hex() if r.get("prev_hash") else None
                        ),
                        "row_hash": bytes(r["row_hash"]).hex(),
                    }
                    for r in rows
                ]

    async def verify_chain(self, *, tenant_id: str) -> dict[str, Any]:
        """Walk the chain and report integrity status.

        Returns ``{"valid": True, "rows": N}`` on success, or
        ``{"valid": False, "broken_at": id, "rows": N}`` on first
        mismatch. Intended for offline audit jobs and a manual
        ``baselith red-agent doctor`` command.
        """
        if not self.available:
            return {"valid": True, "rows": 0}
        prev_hash: bytes = b""
        rows_checked = 0
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                cursor = await conn.execute(
                    """
                    SELECT id, payload, prev_hash, row_hash
                      FROM red_agent_agent_audit_log
                  ORDER BY id ASC
                    """,
                )
                async for r in cursor:
                    rows_checked += 1
                    expected_prev = prev_hash if rows_checked > 1 else b""
                    actual_prev = bytes(r["prev_hash"]) if r.get("prev_hash") else b""
                    if actual_prev != expected_prev:
                        return {
                            "valid": False,
                            "broken_at": int(r["id"]),
                            "rows": rows_checked,
                            "reason": "prev_hash mismatch",
                        }
                    expected_hash = hashlib.sha256(
                        actual_prev + _canonical_json(r["payload"] or {})
                    ).digest()
                    if bytes(r["row_hash"]) != expected_hash:
                        return {
                            "valid": False,
                            "broken_at": int(r["id"]),
                            "rows": rows_checked,
                            "reason": "row_hash mismatch",
                        }
                    prev_hash = bytes(r["row_hash"])
        return {"valid": True, "rows": rows_checked}
