"""Node-child leadership election for the dbview plugin.

The embedded dbview NestJS app is a **single-instance** service: its state
(connection registry, JIT-mirrored users, refresh sessions, query history,
engine pools) lives in per-process in-memory maps backed by JSON files that
are read **once** at startup and never re-read. That is fine for one process,
but under a multi-worker deployment (e.g. ``WEB_CONCURRENCY=3``) every uvicorn
worker used to spawn *its own* Node child on *its own* ephemeral port. Requests
round-robin across workers, so a connection created on child A was invisible to
child B — surfacing to the user as *"Could not load schema — Connection <id>
not found"* immediately after creating it.

The fix is to run **exactly one** Node child for the whole deployment and have
every worker's reverse proxy forward to it over a fixed loopback port. This
module elects the single owning worker with a session-level PostgreSQL advisory
lock (``pg_try_advisory_lock``) — the same primitive the auth plugin uses for
schema init and the honeypot plugin uses for listener leadership. The lock is
held on a dedicated connection for the leader's whole process lifetime (a
pooled connection would reset the session on return and drop the lock) and
released on shutdown. Non-leader workers skip spawning entirely and proxy to
the leader-owned child on the shared port.

Degrades open: if Postgres is disabled or unreachable the caller assumes
leadership (single-worker / dev behaviour), preserving the pre-existing
one-child-per-worker semantics rather than failing to boot.
"""

from __future__ import annotations

from typing import Optional

from psycopg import AsyncConnection

from core.config import get_storage_config
from core.observability.logging import get_logger

logger = get_logger(__name__)

# Distinct 64-bit advisory-lock key for dbview Node-child leadership.
# ASCII "DbvChild" — namespaced away from auth's schema lock (0x41757468) and
# the honeypot listener lock (0x48704C697374656E).
DBVIEW_LEADER_LOCK_KEY = 0x4462764368696C64


class DbviewLeadership:
    """Handle for a dbview Node-child leadership decision.

    Attributes:
        is_leader: True if this worker owns the single Node child (spawns it).
        degraded: True when leadership was assumed without coordination
            (Postgres unavailable), rather than won via advisory lock.
    """

    def __init__(
        self,
        is_leader: bool,
        conn: Optional[AsyncConnection[object]] = None,
        degraded: bool = False,
    ) -> None:
        self.is_leader = is_leader
        self.degraded = degraded
        self._conn = conn

    async def release(self) -> None:
        """Release the advisory lock by closing the held connection."""
        if self._conn is None:
            return
        try:
            await self._conn.close()
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            logger.debug(f"Error closing dbview leader connection: {exc}")
        finally:
            self._conn = None


async def acquire_dbview_leadership() -> DbviewLeadership:
    """Try to become the single Node-child-owning worker across the deployment.

    Returns:
        A ``DbviewLeadership`` whose ``is_leader`` says whether this worker
        should spawn the Node child. Degrades to leader when Postgres is
        unavailable so single-worker/dev deployments keep working.
    """
    storage = get_storage_config()

    if not storage.postgres_enabled:
        logger.warning(
            "Postgres disabled; dbview runs without cross-worker coordination "
            "(assuming single-worker leadership — one Node child per worker)."
        )
        return DbviewLeadership(is_leader=True, degraded=True)

    try:
        conn = await AsyncConnection.connect(storage.conninfo, autocommit=True)
    except Exception as exc:
        logger.warning(
            f"dbview leader-election DB connect failed ({exc}); "
            "assuming leadership (degraded)."
        )
        return DbviewLeadership(is_leader=True, degraded=True)

    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT pg_try_advisory_lock(%s)", (DBVIEW_LEADER_LOCK_KEY,)
            )
            row = await cur.fetchone()
        won = bool(row and row[0])
    except Exception as exc:
        await _safe_close(conn)
        logger.warning(
            f"dbview leader-election query failed ({exc}); "
            "assuming leadership (degraded)."
        )
        return DbviewLeadership(is_leader=True, degraded=True)

    if won:
        logger.info(
            "Acquired dbview Node-child leadership; this worker spawns the child."
        )
        # Keep the connection open to hold the session-level advisory lock.
        return DbviewLeadership(is_leader=True, conn=conn)

    await _safe_close(conn)
    logger.info(
        "Another worker owns the dbview Node child; proxying to the shared port."
    )
    return DbviewLeadership(is_leader=False)


async def _safe_close(conn: AsyncConnection[object]) -> None:
    try:
        await conn.close()
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        logger.debug(f"Error closing dbview leader-election connection: {exc}")


__all__ = [
    "DbviewLeadership",
    "acquire_dbview_leadership",
    "DBVIEW_LEADER_LOCK_KEY",
]
