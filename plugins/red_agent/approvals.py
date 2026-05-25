"""
HITL approval registry for active/intrusive scans.

In-memory state holds the asyncio Future the orchestrator awaits.
Postgres backing (`red_agent_approvals`) is durable — on boot the
plugin loader can resurrect open rows and re-attach futures. A cross-
replica resolve fans out via the in-memory `resolve_external` hook
when the row state moves from `open` to a terminal state from another
process (next iteration: pg LISTEN/NOTIFY).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from core.observability.logging import get_logger

logger = get_logger(__name__)


class ApprovalStore(Protocol):
    """Persistence boundary — implemented by ApprovalPersistence (Postgres)."""

    async def insert_open(
        self, scan_id: UUID, reason: str, requested_by: str
    ) -> None: ...

    async def mark_resolved(
        self, scan_id: UUID, *, approved: bool, actor: str
    ) -> None: ...

    async def mark_timeout(self, scan_id: UUID) -> None: ...

    async def list_open(self) -> list[dict[str, Any]]: ...


class ApprovalRegistry:
    def __init__(self, store: ApprovalStore | None = None) -> None:
        self._futures: dict[str, asyncio.Future[bool]] = {}
        self._meta: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._store = store

    async def open(
        self, scan_id: UUID, *, reason: str, requested_by: str
    ) -> asyncio.Future[bool]:
        """Open a pending approval slot, return an awaitable future."""
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        async with self._lock:
            self._futures[str(scan_id)] = future
            self._meta[str(scan_id)] = {
                "reason": reason,
                "requested_by": requested_by,
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }
        if self._store is not None:
            try:
                await self._store.insert_open(scan_id, reason, requested_by)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "approval persistence insert_open failed",
                    extra={"scan_id": str(scan_id)},
                )
        logger.info(
            "red_agent.approval.opened",
            extra={"scan_id": str(scan_id), "reason": reason},
        )
        return future

    async def resolve(self, scan_id: UUID, approved: bool, actor: str) -> bool:
        """Resolve a pending approval. Returns True on success."""
        async with self._lock:
            future = self._futures.pop(str(scan_id), None)
            self._meta.pop(str(scan_id), None)
        if future is None or future.done():
            return False
        future.set_result(approved)
        if self._store is not None:
            try:
                await self._store.mark_resolved(scan_id, approved=approved, actor=actor)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "approval persistence mark_resolved failed",
                    extra={"scan_id": str(scan_id)},
                )
        logger.info(
            "red_agent.approval.resolved",
            extra={
                "scan_id": str(scan_id),
                "approved": approved,
                "actor": actor,
            },
        )
        return True

    async def mark_timeout(self, scan_id: UUID) -> None:
        if self._store is not None:
            try:
                await self._store.mark_timeout(scan_id)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "approval persistence mark_timeout failed",
                    extra={"scan_id": str(scan_id)},
                )

    async def list_pending(self) -> list[dict[str, Any]]:
        async with self._lock:
            return [
                {"scan_id": k, **v}
                for k, v in self._meta.items()
                if k in self._futures and not self._futures[k].done()
            ]

    async def rehydrate(self) -> int:
        """Rebuild in-memory state from the persistent store.

        Called once at boot. For each open row, recreate a Future so the
        approve/reject endpoints can resolve it. The Future is only
        useful if the orchestrator is also re-attached (current MVP
        marks rehydrated approvals as timeout — operators must resubmit
        the scan). Returns the number of rows rehydrated.
        """
        if self._store is None:
            return 0
        try:
            rows = await self._store.list_open()
        except Exception:  # noqa: BLE001
            logger.warning("approval rehydrate failed (store unavailable)")
            return 0

        loop = asyncio.get_running_loop()
        async with self._lock:
            for row in rows:
                key = str(row["scan_id"])
                if key in self._futures:
                    continue
                fut: asyncio.Future[bool] = loop.create_future()
                self._futures[key] = fut
                opened_at = row.get("opened_at")
                if isinstance(opened_at, datetime):
                    opened_at_iso = opened_at.isoformat()
                elif isinstance(opened_at, str) and opened_at:
                    opened_at_iso = opened_at
                else:
                    opened_at_iso = datetime.now(timezone.utc).isoformat()
                self._meta[key] = {
                    "reason": row.get("reason", ""),
                    "requested_by": row.get("requested_by", "unknown"),
                    "opened_at": opened_at_iso,
                }
        logger.info(
            "red_agent.approval.rehydrated",
            extra={"count": len(rows)},
        )
        return len(rows)
