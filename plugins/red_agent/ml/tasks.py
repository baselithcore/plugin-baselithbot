"""Background tasks for the ML layer.

Currently hosts :class:`AnomalyDetectorTask`, which periodically pulls
recent telemetry, scores it via :class:`AnomalyDetectorService`, and
materializes flagged hosts as synthetic findings + audit events.

Kept in a separate module from the core :mod:`plugins.red_agent.tasks`
so the ML maintenance loops can be wired (and unit-tested) without
touching the schedule dispatcher / audit-retention sweepers.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from core.observability.logging import get_logger
from plugins.red_agent.ml.models.anomaly import AnomalyScore

if TYPE_CHECKING:
    from plugins.red_agent.audit import AuditLogger
    from plugins.red_agent.config import RedAgentConfig
    from plugins.red_agent.events import ScanEventBus
    from plugins.red_agent.ml.models import AnomalyDetectorService
    from plugins.red_agent.persistence import AgentPersistence, AgentTelemetryStore

logger = get_logger(__name__)


class AnomalyDetectorTask:
    """Periodic detection loop over the agent telemetry firehose.

    Cadence is :attr:`RedAgentConfig.ml_anomaly_tick_seconds`. Each tick:

    1. Resolves the active tenant set from the agent persistence layer
       (one IsolationForest fit per tenant — never cross-tenant).
    2. Pulls recent telemetry per tenant via
       :meth:`AgentTelemetryStore.list_recent`.
    3. Calls :meth:`AnomalyDetectorService.score_window` on the batch.
    4. Emits an audit event + WS event for every host flagged as an
       anomaly. Synthetic-finding ingest is deferred to a follow-up
       (needs a ``Finding`` record without a paired scan_id, currently
       outside the persistence schema's foreign key).

    The task is fully cooperative: a slow tick simply delays the next
    one. Failures are logged at WARN and never crash the loop.
    """

    def __init__(
        self,
        *,
        detector: "AnomalyDetectorService",
        telemetry: "AgentTelemetryStore",
        agents: "AgentPersistence",
        audit: "AuditLogger",
        events: "ScanEventBus",
        config: "RedAgentConfig",
    ) -> None:
        self.detector = detector
        self.telemetry = telemetry
        self.agents = agents
        self.audit = audit
        self.events = events
        self.config = config
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    @property
    def enabled(self) -> bool:
        return self.detector.enabled and self.telemetry.available

    async def _tick(self) -> int:
        if not self.enabled:
            return 0

        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=self.config.ml_anomaly_window_minutes)

        try:
            tenants = await self._resolve_tenants()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.ml.anomaly.tenant_resolve_failed", extra={"err": str(e)}
            )
            return 0

        flagged = 0
        for tenant_id in tenants:
            try:
                events = await self.telemetry.list_recent(
                    tenant_id=tenant_id, limit=5000
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "red_agent.ml.anomaly.fetch_failed",
                    extra={"tenant_id": tenant_id, "err": str(e)},
                )
                continue
            scores = self.detector.score_window(
                events=events, window_start=start, window_end=end
            )
            for s in scores:
                if s.is_anomaly:
                    await self._emit(s)
                    flagged += 1
        return flagged

    async def _resolve_tenants(self) -> list[str]:
        """Tenants the detector should iterate over.

        The ``AgentPersistence`` query API currently requires a tenant
        scope (no cross-tenant ``list_all``), so for the MVP we run
        against ``"default"``. Multi-tenant fleets can extend this by
        plugging a tenant-discovery hook (e.g. a separate `tenants`
        table) without touching the loop body.
        """
        _ = self.agents  # placeholder until tenant-discovery lands
        return ["default"]

    async def _emit(self, score: AnomalyScore) -> None:
        await self.audit.record(
            scan_id=None,
            actor="red_agent.ml.anomaly",
            event="agent.anomaly_detected",
            payload={
                "agent_uuid": str(score.agent_uuid),
                "tenant_id": score.tenant_id,
                "score": score.score,
                "sample_count": score.sample_count,
                "features": score.features,
                "window_start": score.window_start.isoformat(),
                "window_end": score.window_end.isoformat(),
            },
        )
        # ScanEventBus is keyed by scan_id; reuse the agent_uuid as the
        # logical channel so the fleet UI can subscribe to per-host
        # anomaly streams without inventing a new bus.
        try:
            await self.events.publish(
                score.agent_uuid,
                {
                    "type": "anomaly",
                    "agent_uuid": str(score.agent_uuid),
                    "score": score.score,
                    "features": score.features,
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.debug(
                "red_agent.ml.anomaly.publish_failed",
                extra={"agent_uuid": str(score.agent_uuid), "err": str(e)},
            )

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception:  # noqa: BLE001
                logger.exception("red_agent.ml.anomaly.tick_failed")
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.config.ml_anomaly_tick_seconds
                )
            except asyncio.TimeoutError:
                continue

    def start(self) -> None:
        if not self.enabled:
            logger.info("red_agent.ml.anomaly.task_disabled")
            return
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())
            logger.info("red_agent.ml.anomaly.task_started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await asyncio.gather(self._task, return_exceptions=True)
