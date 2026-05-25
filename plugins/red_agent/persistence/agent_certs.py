"""Cert lifecycle persistence for the endpoint daemon.

Tracks every cert ever issued to an agent so revocation, rotation
audits, and forensic queries (``which cert was active at T?``) all
work. The ``state='active'`` partial unique index in the schema
guarantees at most one active cert per agent at any moment.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from psycopg import sql

from core.observability.logging import get_logger
from plugins.red_agent.agent_models import AgentCertRecord, CertState

from ._conn import open_conn
from ._tenant import tenant_scope

logger = get_logger(__name__)


def _row_to_record(row: dict[str, Any]) -> AgentCertRecord:
    return AgentCertRecord(
        serial=row["serial"],
        agent_uuid=row["agent_uuid"]
        if isinstance(row["agent_uuid"], UUID)
        else UUID(str(row["agent_uuid"])),
        tenant_id=row["tenant_id"],
        fingerprint_sha256=row["fingerprint_sha256"],
        spiffe_uri=row["spiffe_uri"],
        not_before=row["not_before"],
        not_after=row["not_after"],
        state=CertState(row["state"]),
        issued_at=row["issued_at"],
        rotated_at=row.get("rotated_at"),
        revoked_at=row.get("revoked_at"),
        revoked_reason=row.get("revoked_reason"),
        revoked_by=row.get("revoked_by"),
    )


class AgentCertPersistence:
    """CRUD for ``red_agent_agent_certs``."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def issue(
        self,
        record: AgentCertRecord,
        *,
        tenant_id: str,
    ) -> AgentCertRecord:
        """Insert a new active cert, marking any prior active cert as rotated.

        Performed in a single transaction so we cannot leave the agent
        with two active certs (also enforced by the partial unique
        index ``red_agent_certs_active_per_agent_uq``).
        """
        if not self.available:
            raise RuntimeError("red_agent: postgres not configured")
        if record.state != CertState.ACTIVE:
            raise ValueError("issue() must receive a CertState.ACTIVE record")
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                await conn.execute(
                    """
                    UPDATE red_agent_agent_certs
                       SET state = 'rotated', rotated_at = now()
                     WHERE agent_uuid = %s AND state = 'active'
                    """,
                    (str(record.agent_uuid),),
                )
                await conn.execute(
                    """
                    INSERT INTO red_agent_agent_certs (
                        serial, agent_uuid, tenant_id, fingerprint_sha256,
                        spiffe_uri, not_before, not_after, state, issued_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        record.serial,
                        str(record.agent_uuid),
                        tenant_id,
                        record.fingerprint_sha256.lower(),
                        record.spiffe_uri,
                        record.not_before,
                        record.not_after,
                        record.state.value,
                        record.issued_at,
                    ),
                )
        return record

    async def get_active(
        self, agent_uuid: UUID, *, tenant_id: str
    ) -> AgentCertRecord | None:
        if not self.available:
            return None
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                row = await (
                    await conn.execute(
                        """
                        SELECT * FROM red_agent_agent_certs
                         WHERE agent_uuid = %s AND state = 'active'
                        """,
                        (str(agent_uuid),),
                    )
                ).fetchone()
                return _row_to_record(dict(row)) if row else None

    async def get_by_fingerprint(
        self, fingerprint_sha256: str, *, tenant_id: str
    ) -> AgentCertRecord | None:
        if not self.available:
            return None
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                row = await (
                    await conn.execute(
                        """
                        SELECT * FROM red_agent_agent_certs
                         WHERE fingerprint_sha256 = %s
                        """,
                        (fingerprint_sha256.lower(),),
                    )
                ).fetchone()
                return _row_to_record(dict(row)) if row else None

    async def revoke(
        self,
        serial: str,
        *,
        tenant_id: str,
        reason: str,
        revoked_by: str,
    ) -> bool:
        if not self.available:
            return False
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                result = await conn.execute(
                    """
                    UPDATE red_agent_agent_certs
                       SET state = 'revoked',
                           revoked_at = now(),
                           revoked_reason = %s,
                           revoked_by = %s
                     WHERE serial = %s AND state IN ('active', 'rotated')
                    """,
                    (reason, revoked_by, serial),
                )
                return (result.rowcount or 0) > 0

    async def list_for_agent(
        self,
        agent_uuid: UUID,
        *,
        tenant_id: str,
        limit: int = 100,
    ) -> list[AgentCertRecord]:
        if not self.available:
            return []
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                rows = await (
                    await conn.execute(
                        sql.SQL(
                            """
                            SELECT * FROM red_agent_agent_certs
                             WHERE agent_uuid = %s
                          ORDER BY issued_at DESC
                             LIMIT %s
                            """
                        ),
                        (str(agent_uuid), limit),
                    )
                ).fetchall()
                return [_row_to_record(dict(r)) for r in rows]

    async def expire_due(self, *, tenant_id: str) -> int:
        """Sweep certs whose ``not_after`` is in the past.

        Returns the number of rows transitioned to ``expired``. Run on
        a periodic task; not required for security (TLS handshake will
        already reject expired certs) but keeps the registry clean.
        """
        if not self.available:
            return 0
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                result = await conn.execute(
                    """
                    UPDATE red_agent_agent_certs
                       SET state = 'expired'
                     WHERE state = 'active' AND not_after < now()
                    """,
                )
                return result.rowcount or 0

    async def now(self) -> datetime:
        """Helper exposing server-side now() for callers that need it."""
        del self  # currently unused but kept for symmetry
        return datetime.now(timezone.utc)
