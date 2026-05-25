"""Tenant context manager for Row-Level-Security session binding.

Every daemon-related table (``red_agent_agents``, ``red_agent_agent_certs``,
``red_agent_enrollment_tokens``, ``red_agent_agent_commands``,
``red_agent_agent_telemetry``, ``red_agent_agent_audit_log``) carries an
RLS policy that gates rows on
``current_setting('app.tenant_id', true) = tenant_id``.

The session variable must be set inside an explicit transaction and is
scoped to that transaction with ``SET LOCAL`` so a leaked or pooled
connection cannot accidentally retain the binding. This module provides
the only sanctioned way to set it.

Usage::

    async with await open_conn(dsn) as conn:
        async with tenant_scope(conn, tenant_id="acme-prod"):
            await conn.execute("SELECT * FROM red_agent_agents WHERE ...")

The context manager opens a transaction (``BEGIN``), issues
``SET LOCAL app.tenant_id = ...``, yields, then commits on success or
rolls back on exception. The escape into ``set_session_tenant`` exists
only for tests that already manage their own transaction.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import psycopg
from psycopg.rows import DictRow

from core.observability.logging import get_logger

logger = get_logger(__name__)


_SAFE_TENANT_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:.@"
)


def _validate_tenant_id(tenant_id: str) -> str:
    if not tenant_id:
        raise ValueError("tenant_id must be non-empty")
    if len(tenant_id) > 128:
        raise ValueError("tenant_id too long (max 128 chars)")
    if any(ch not in _SAFE_TENANT_CHARS for ch in tenant_id):
        raise ValueError("tenant_id contains unsafe characters")
    return tenant_id


async def set_session_tenant(
    conn: psycopg.AsyncConnection[DictRow],
    tenant_id: str,
) -> None:
    """Bind ``app.tenant_id`` for the current transaction.

    Caller is responsible for the surrounding ``BEGIN`` / ``COMMIT``.
    Used by tests and by code that already owns a transaction;
    application code should prefer :func:`tenant_scope`.
    """
    safe = _validate_tenant_id(tenant_id)
    await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (safe,))


@asynccontextmanager
async def tenant_scope(
    conn: psycopg.AsyncConnection[DictRow],
    *,
    tenant_id: str,
) -> AsyncIterator[psycopg.AsyncConnection[DictRow]]:
    """Async context manager that opens a tenant-scoped transaction.

    On exit the transaction is committed (success) or rolled back
    (exception). The session variable is automatically scoped to the
    transaction by ``set_config(..., is_local=true)`` and cannot leak
    to subsequent transactions on the same connection.
    """
    safe = _validate_tenant_id(tenant_id)
    async with conn.transaction():
        await conn.execute("SELECT set_config('app.tenant_id', %s, true)", (safe,))
        try:
            yield conn
        except Exception:
            logger.debug(
                "red_agent.tenant_scope.rollback",
                extra={"tenant_id": safe},
            )
            raise
