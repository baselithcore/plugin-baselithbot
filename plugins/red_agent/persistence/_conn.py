"""Shared async psycopg connection helpers used by every persistence class.

Centralizes the dict-row connect dance, pool management, and JSON encoding
so each sub-store stays under the per-file LOC cap and avoids duplication.

Hot paths (scan write, finding insert, audit append) acquire from a
process-wide :class:`AsyncConnectionPool` keyed by DSN, eliminating the
TLS+startup round-trip per call. Slow admin paths can still use
:func:`open_conn` for a one-shot connection.
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, cast

import psycopg
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

# Bound the libpq connect handshake so an unreachable Postgres surfaces as
# an error in seconds, not a 60-120s TCP retry. Without this the policy
# save endpoint (and any other persistence path) appears to hang the UI
# when the DB is offline.
_DEFAULT_CONNECT_TIMEOUT = 10
_DEFAULT_POOL_MIN_SIZE = 1
_DEFAULT_POOL_MAX_SIZE = 10
_DEFAULT_POOL_TIMEOUT = 10.0


def pg_connect_timeout() -> int:
    raw = os.getenv("RED_AGENT_PG_CONNECT_TIMEOUT")
    if not raw:
        return _DEFAULT_CONNECT_TIMEOUT
    try:
        v = int(raw)
        return v if v > 0 else _DEFAULT_CONNECT_TIMEOUT
    except ValueError:
        return _DEFAULT_CONNECT_TIMEOUT


def _pool_int(env: str, default: int) -> int:
    raw = os.getenv(env)
    if not raw:
        return default
    try:
        v = int(raw)
        return v if v > 0 else default
    except ValueError:
        return default


_POOLS: dict[str, Any] = {}
_POOLS_LOCK = asyncio.Lock()


async def _get_pool(dsn: str) -> Any:
    """Return a process-wide pool for the given DSN, creating it on first use."""
    pool = _POOLS.get(dsn)
    if pool is not None:
        return pool
    async with _POOLS_LOCK:
        pool = _POOLS.get(dsn)
        if pool is not None:
            return pool
        pool = cast(
            Any,
            AsyncConnectionPool(
                conninfo=dsn,
                min_size=_pool_int("RED_AGENT_PG_POOL_MIN", _DEFAULT_POOL_MIN_SIZE),
                max_size=_pool_int("RED_AGENT_PG_POOL_MAX", _DEFAULT_POOL_MAX_SIZE),
                timeout=_DEFAULT_POOL_TIMEOUT,
                kwargs={
                    "row_factory": dict_row,
                    "connect_timeout": pg_connect_timeout(),
                },
                open=False,
            ),
        )
        await pool.open()
        _POOLS[dsn] = pool
        return pool


@asynccontextmanager
async def acquire(dsn: str) -> AsyncIterator[psycopg.AsyncConnection[DictRow]]:
    """Acquire a pooled async connection for ``dsn``.

    Use this on hot paths (scan/finding writes, audit). The pool reuses
    open libpq connections, eliminating the TLS+startup cost every call.
    The pool's context manager commits on success and rolls back on
    exception; existing explicit ``conn.commit()`` calls remain valid.
    """
    if not dsn:
        raise RuntimeError("red_agent: postgres DSN not configured")
    pool = await _get_pool(dsn)
    async with pool.connection() as conn:
        yield cast("psycopg.AsyncConnection[DictRow]", conn)


async def close_pools() -> None:
    """Close every pool created by :func:`_get_pool`. Called on plugin shutdown."""
    async with _POOLS_LOCK:
        pools = list(_POOLS.values())
        _POOLS.clear()
    for pool in pools:
        try:
            await pool.close()
        except Exception:  # noqa: BLE001
            pass


async def open_conn(dsn: str) -> psycopg.AsyncConnection[DictRow]:
    """One-shot connection. Prefer :func:`acquire` on hot paths."""
    if not dsn:
        raise RuntimeError("red_agent: postgres DSN not configured")
    connect = cast(Any, psycopg.AsyncConnection.connect)
    return cast(
        "psycopg.AsyncConnection[DictRow]",
        await connect(
            dsn,
            row_factory=dict_row,
            connect_timeout=pg_connect_timeout(),
        ),
    )


def jsonb(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str)
