"""Persistence for single-use enrollment tokens.

The plaintext token is **never** stored in the database. Only its
SHA-256 hash persists in ``token_sha256``. The plaintext is shown to
the operator exactly once at creation time. Lost tokens cannot be
recovered — they must be re-minted.

Tokens are redeemed atomically: the same SQL statement that fetches
the unused row also marks it ``redeemed``, so a concurrent retry on
the same plaintext cannot enroll twice.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from core.observability.logging import get_logger
from plugins.red_agent.agent_models import (
    EnrollmentTokenIssued,
    EnrollmentTokenRecord,
    EnrollmentTokenState,
)

from ._conn import jsonb, open_conn
from ._tenant import tenant_scope

logger = get_logger(__name__)


# 32 bytes -> 256 bits of entropy. URL-safe base64 == 43 chars.
TOKEN_BYTES = 32


def _hash_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("ascii")).hexdigest()


def _row_to_record(row: dict[str, Any]) -> EnrollmentTokenRecord:
    return EnrollmentTokenRecord(
        id=row["id"] if isinstance(row["id"], UUID) else UUID(str(row["id"])),
        tenant_id=row["tenant_id"],
        token_sha256=row["token_sha256"],
        bind_agent_uuid=(
            row["bind_agent_uuid"]
            if row.get("bind_agent_uuid") is None
            or isinstance(row["bind_agent_uuid"], UUID)
            else UUID(str(row["bind_agent_uuid"]))
        ),
        labels=row.get("labels") or {},
        created_at=row["created_at"],
        created_by=row["created_by"],
        expires_at=row["expires_at"],
        state=EnrollmentTokenState(row["state"]),
        redeemed_at=row.get("redeemed_at"),
        redeemed_agent_uuid=(
            row["redeemed_agent_uuid"]
            if row.get("redeemed_agent_uuid") is None
            or isinstance(row["redeemed_agent_uuid"], UUID)
            else UUID(str(row["redeemed_agent_uuid"]))
        ),
        revoked_at=row.get("revoked_at"),
        revoked_by=row.get("revoked_by"),
    )


class EnrollmentTokenPersistence:
    """CRUD for ``red_agent_enrollment_tokens``."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def mint(
        self,
        *,
        tenant_id: str,
        created_by: str,
        ttl_seconds: int,
        bind_agent_uuid: UUID | None = None,
        labels: dict[str, Any] | None = None,
    ) -> EnrollmentTokenIssued:
        """Generate a fresh token, persist its hash, return plaintext once."""
        if not self.available:
            raise RuntimeError("red_agent: postgres not configured")
        plaintext = secrets.token_urlsafe(TOKEN_BYTES)
        token_id = uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                await conn.execute(
                    """
                    INSERT INTO red_agent_enrollment_tokens (
                        id, tenant_id, token_sha256, bind_agent_uuid,
                        labels, created_by, expires_at, state
                    ) VALUES (
                        %s, %s, %s, %s, %s::jsonb, %s, %s, 'unused'
                    )
                    """,
                    (
                        str(token_id),
                        tenant_id,
                        _hash_token(plaintext),
                        str(bind_agent_uuid) if bind_agent_uuid else None,
                        jsonb(labels or {}),
                        created_by,
                        expires_at,
                    ),
                )
        return EnrollmentTokenIssued(
            id=token_id,
            token=plaintext,
            tenant_id=tenant_id,
            expires_at=expires_at,
            bind_agent_uuid=bind_agent_uuid,
        )

    async def redeem(
        self,
        plaintext: str,
        *,
        agent_uuid: UUID,
    ) -> EnrollmentTokenRecord | None:
        """Atomically redeem a token.

        Looks up by hash, validates state and expiry and bind_agent_uuid,
        marks the row redeemed, and returns it. Returns None for any
        invalid token (unknown / expired / revoked / already redeemed /
        wrong bind). The caller MUST treat None as "reject enrollment".

        This is the only path that does NOT pre-set a tenant; it cannot
        — the caller does not yet know the tenant. RLS therefore would
        hide every row, so we run the lookup as a session-level
        privileged query (the application's DB role is the table owner
        and bypasses RLS unless ``FORCE ROW LEVEL SECURITY`` is set).
        Once the token's ``tenant_id`` is recovered, every subsequent
        write goes through ``tenant_scope`` like the rest of the API.
        """
        if not self.available:
            return None
        token_hash = _hash_token(plaintext)
        async with await open_conn(self.dsn) as conn:
            async with conn.transaction():
                row = await (
                    await conn.execute(
                        """
                        SELECT * FROM red_agent_enrollment_tokens
                         WHERE token_sha256 = %s
                           AND state = 'unused'
                           AND expires_at > now()
                           AND (bind_agent_uuid IS NULL OR bind_agent_uuid = %s)
                         FOR UPDATE
                        """,
                        (token_hash, str(agent_uuid)),
                    )
                ).fetchone()
                if row is None:
                    logger.info(
                        "red_agent.enrollment.token_invalid",
                        extra={"agent_uuid": str(agent_uuid)},
                    )
                    return None
                await conn.execute(
                    """
                    UPDATE red_agent_enrollment_tokens
                       SET state = 'redeemed',
                           redeemed_at = now(),
                           redeemed_agent_uuid = %s
                     WHERE id = %s
                    """,
                    (str(agent_uuid), str(row["id"])),
                )
        return _row_to_record(dict(row))

    async def revoke(
        self,
        token_id: UUID,
        *,
        tenant_id: str,
        revoked_by: str,
    ) -> bool:
        if not self.available:
            return False
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                result = await conn.execute(
                    """
                    UPDATE red_agent_enrollment_tokens
                       SET state = 'revoked',
                           revoked_at = now(),
                           revoked_by = %s
                     WHERE id = %s AND state = 'unused'
                    """,
                    (revoked_by, str(token_id)),
                )
                return (result.rowcount or 0) > 0

    async def list(
        self,
        *,
        tenant_id: str,
        state: EnrollmentTokenState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EnrollmentTokenRecord]:
        if not self.available:
            return []
        params: list[Any] = []
        if state is not None:
            sql = """
                SELECT * FROM red_agent_enrollment_tokens
                 WHERE state = %s
              ORDER BY created_at DESC
                 LIMIT %s OFFSET %s
            """
            params.append(state.value)
        else:
            sql = """
                SELECT * FROM red_agent_enrollment_tokens
              ORDER BY created_at DESC
                 LIMIT %s OFFSET %s
            """
        params.extend([limit, offset])
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                rows = await (await conn.execute(sql, tuple(params))).fetchall()
                return [_row_to_record(dict(r)) for r in rows]

    async def expire_due(self, *, tenant_id: str) -> int:
        """Mark expired tokens as ``expired``. Returns affected row count."""
        if not self.available:
            return 0
        async with await open_conn(self.dsn) as conn:
            async with tenant_scope(conn, tenant_id=tenant_id):
                result = await conn.execute(
                    """
                    UPDATE red_agent_enrollment_tokens
                       SET state = 'expired'
                     WHERE state = 'unused' AND expires_at < now()
                    """,
                )
                return result.rowcount or 0
