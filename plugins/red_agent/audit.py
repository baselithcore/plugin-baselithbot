"""
Tamper-evident audit logger for Red Agent operations.

Every state transition (scan request, guardrail decision, HITL approval,
scanner start/end, finding insert) is appended to red_agent_audit. The
log is append-only at the SQL level (no UPDATE / DELETE policies).
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from datetime import datetime, timezone
from psycopg.rows import DictRow

from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.red_agent.events import ActivityEventBus, ScanEngagementIndex
from plugins.red_agent.persistence._conn import acquire

logger = get_logger(__name__)


class AuditLogger:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def record(
        self,
        *,
        scan_id: UUID | None,
        actor: str,
        event: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not self.dsn:
            logger.info(
                "red_agent.audit.skipped_no_dsn",
                extra={"actor": actor, "event": event},
            )
            await self._broadcast(
                scan_id=scan_id, actor=actor, event=event, payload=payload
            )
            return
        try:
            async with acquire(self.dsn) as conn:
                await conn.execute(
                    """
                    INSERT INTO red_agent_audit (scan_id, actor, event, payload)
                    VALUES (%s, %s, %s, %s::jsonb)
                    """,
                    (
                        str(scan_id) if scan_id else None,
                        actor,
                        event,
                        json.dumps(payload or {}, default=str),
                    ),
                )
                await conn.commit()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.audit.failed",
                extra={"actor": actor, "event": event, "err": str(e)},
            )
            return
        logger.info("red_agent.audit", extra={"actor": actor, "event": event})
        await self._broadcast(
            scan_id=scan_id, actor=actor, event=event, payload=payload
        )

    @staticmethod
    async def _broadcast(
        *,
        scan_id: UUID | None,
        actor: str,
        event: str,
        payload: dict[str, Any] | None,
    ) -> None:
        """Push the audit event to the cockpit activity bus, fail-open."""
        try:
            bus = ServiceRegistry.get(ActivityEventBus)
        except Exception:  # noqa: BLE001
            bus = None
        if bus is None:
            return
        engagement_id: str | None = None
        try:
            index = ServiceRegistry.get(ScanEngagementIndex)
        except Exception:  # noqa: BLE001
            index = None
        if index is not None and scan_id is not None:
            try:
                engagement_id = index.lookup(scan_id)
            except Exception:  # noqa: BLE001
                engagement_id = None
        try:
            await bus.publish(
                {
                    "scan_id": str(scan_id) if scan_id else None,
                    "engagement_id": engagement_id,
                    "actor": actor,
                    "event": event,
                    "payload": payload or {},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.activity_bus.publish_failed",
                extra={"event": event, "err": str(e)},
            )

    @staticmethod
    def _types_marker() -> type[DictRow]:
        return DictRow
