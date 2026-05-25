"""
Background maintenance tasks for the Red Agent plugin.

The current MVP runs these from the plugin's `initialize()` as long-
lived asyncio tasks. When BaselithCore's task queue (`core.task_queue`)
is wired in, replace `asyncio.sleep` with proper cron triggers.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

import psycopg
from psycopg.rows import DictRow, dict_row

from core.observability.logging import get_logger
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.cron import is_due
from plugins.red_agent.guardrails import GuardrailViolation
from plugins.red_agent.models import (
    ScanIntensity,
    ScanRequest,
    Target,
    TargetKind,
    TargetType,
)

if TYPE_CHECKING:
    from plugins.red_agent.agent import RedAgent
    from plugins.red_agent.persistence import TargetPersistence

logger = get_logger(__name__)


async def _delete_expired_audit(dsn: str, retention_days: int) -> int:
    """Delete audit rows older than retention_days. Returns rows removed."""
    connect = cast(Any, psycopg.AsyncConnection.connect)
    conn = cast(
        "psycopg.AsyncConnection[DictRow]",
        await connect(dsn, row_factory=dict_row),
    )
    async with conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                DELETE FROM red_agent_audit
                 WHERE created_at < now() - (%s || ' days')::interval
                """,
                (retention_days,),
            )
            removed = cur.rowcount or 0
        await conn.commit()
    return removed


class AuditRetentionTask:
    """Periodic deletion of audit rows past `audit_retention_days`."""

    def __init__(
        self,
        dsn: str,
        config: RedAgentConfig,
        *,
        interval_seconds: int = 24 * 3600,
    ) -> None:
        self.dsn = dsn
        self.config = config
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                removed = await _delete_expired_audit(
                    self.dsn, self.config.audit_retention_days
                )
                logger.info(
                    "red_agent.audit.retention_swept",
                    extra={
                        "removed": removed,
                        "retention_days": self.config.audit_retention_days,
                    },
                )
            except Exception:  # noqa: BLE001
                logger.exception("audit retention sweep failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())
            logger.info("red_agent.audit.retention_task_started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await asyncio.gather(self._task, return_exceptions=True)


def _infer_target_type(kind: TargetKind, value: str) -> TargetType:
    if kind == TargetKind.WEB:
        return (
            TargetType.URL
            if value.startswith(("http://", "https://"))
            else TargetType.HOSTNAME
        )
    if kind == TargetKind.NETWORK:
        return TargetType.CIDR if "/" in value else TargetType.IP
    return TargetType.HOSTNAME


class ScheduleDispatcherTask:
    """Polls ``red_agent_targets`` for ``schedule_cron`` matches and fires scans.

    Tick cadence is ``tick_seconds`` (default 60s). On each tick, the loop:

    1. Loads non-archived targets with a non-null ``schedule_cron``.
    2. For each, asks :func:`is_due` whether the cron expression has fired
       since ``last_scan_at``.
    3. If yes, builds a :class:`ScanRequest` from the target's stored profile
       and submits it through the agent (full guardrail / HITL pipeline).

    The dispatcher is intentionally cooperative: a tick that takes longer
    than ``tick_seconds`` simply delays the next tick. Targets without a
    schedule are skipped. Cron parse errors are logged once per target per
    tick and do not crash the loop.
    """

    def __init__(
        self,
        agent: "RedAgent",
        targets: "TargetPersistence",
        *,
        tick_seconds: int = 60,
    ) -> None:
        self.agent = agent
        self.targets = targets
        self.tick_seconds = tick_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def _tick(self) -> int:
        if not self.targets.available:
            return 0
        records = await self.targets.list(include_archived=False, limit=500)
        now = datetime.now(timezone.utc)
        fired = 0
        for record in records:
            if not record.schedule_cron:
                continue
            if not is_due(
                record.schedule_cron, now=now, last_fired_at=record.last_scan_at
            ):
                continue
            try:
                target_type = _infer_target_type(record.kind, record.value)
                profile = record.profile or {}
                request = ScanRequest(
                    target=Target(type=target_type, value=record.value),
                    target_id=record.id,
                    scanners=list(profile.get("scanners") or ["nmap", "nuclei"]),
                    intensity=ScanIntensity(profile.get("intensity") or "passive"),
                    requested_by="scheduler",
                    tenant_id=record.tenant_id,
                    notes=f"scheduled by cron: {record.schedule_cron}",
                )
                await self.agent.submit_scan(request)
                fired += 1
                logger.info(
                    "red_agent.scheduler.fired",
                    extra={
                        "target_id": str(record.id),
                        "kind": record.kind.value,
                        "cron": record.schedule_cron,
                    },
                )
            except GuardrailViolation as exc:
                logger.warning(
                    "red_agent.scheduler.guardrail_block",
                    extra={
                        "target_id": str(record.id),
                        "code": exc.code,
                        "message": exc.message,
                    },
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "red_agent.scheduler.tick_target_failed",
                    extra={"target_id": str(record.id)},
                )
        return fired

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception:  # noqa: BLE001
                logger.exception("red_agent.scheduler.tick_failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.tick_seconds)
            except asyncio.TimeoutError:
                continue

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())
            logger.info("red_agent.scheduler.task_started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await asyncio.gather(self._task, return_exceptions=True)
