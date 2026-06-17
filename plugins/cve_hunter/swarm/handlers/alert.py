"""CVE Hunter Alert Mixin.

Handles CVE analysis, alert creation, persistence and agent status updates
for CVEHunterSwarm.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from core.observability.logging import get_logger

from ...events import CVEHunterEvents, emit_cve_event
from ...models import AgentTaskStatus, CVERecord, VulnerabilityAlert

logger = get_logger(__name__)


class AlertMixin:
    """Mixin for CVE analysis, alert lifecycle, and agent status tracking."""

    async def _analyze_new_cves(self, cves: List[CVERecord]) -> None:
        """Analyze newly discovered CVEs."""
        self._update_agent_status("analyzer-1", AgentTaskStatus.ANALYZING)
        self._add_discovery_log(
            f"ANALYZER: Starting analysis of {len(cves)} new CVEs..."
        )

        try:
            for cve in cves[:10]:
                started = datetime.now(timezone.utc)
                success = False
                try:
                    analysis = await self._analyzer.analyze_cve(cve)
                    if analysis.get("ai_summary"):
                        cve.ai_summary = analysis["ai_summary"]
                        async with self._cache_lock:
                            self._cve_cache[cve.cve_id] = cve
                        self._add_discovery_log(
                            f"ANALYZER: Completed analysis for {cve.cve_id}"
                        )

                        try:
                            from ...persistence import CVEHunterDAO

                            await CVEHunterDAO.save_cve(cve)
                        except Exception as e:
                            logger.error(
                                "Failed to persist analyzed CVE",
                                extra={"cve_id": cve.cve_id, "error": str(e)},
                            )

                        try:
                            await self.vector_store.index_cve(
                                cve_id=cve.cve_id,
                                description=(
                                    cve.description or cve.title or cve.cve_id
                                ),
                                severity=cve.severity.value,
                                cvss_score=cve.cvss_score,
                                cwe_ids=cve.cwe_ids,
                                metadata={"source": cve.source.value},
                            )
                        except Exception as e:
                            logger.debug(
                                "Vector index skipped",
                                extra={"cve_id": cve.cve_id, "error": str(e)},
                            )

                        success = True
                finally:
                    duration = (datetime.now(timezone.utc) - started).total_seconds()
                    self.metrics.record_analysis(
                        cve_id=cve.cve_id, duration=duration, success=success
                    )
        finally:
            self._update_agent_status("analyzer-1", AgentTaskStatus.IDLE)
            self.metrics.set_cve_cache_size(len(self._cve_cache))
            self._add_discovery_log("ANALYZER: Batch analysis complete.")

    def _should_alert(self, cve: CVERecord) -> bool:
        """Determine if CVE should generate an alert."""
        if cve.severity.value == "critical" and self.config.alert_on_critical:
            return True
        if cve.severity.value == "high" and self.config.alert_on_high:
            return True
        return False

    async def _create_alert(self, cve: CVERecord) -> VulnerabilityAlert:
        """Create an alert for a CVE."""
        alert = VulnerabilityAlert(
            alert_id=str(uuid4()),
            cve=cve,
            alert_type="new_cve",
            priority=self._analyzer.calculate_priority_score(cve),
            created_at=datetime.now(timezone.utc),
        )
        self._alerts.append(alert)
        self.metrics.record_alert(cve.severity.value)
        logger.warning(
            "Vulnerability alert created",
            extra={
                "cve_id": cve.cve_id,
                "severity": cve.severity.value,
                "cvss_score": cve.cvss_score,
            },
        )

        await self._persist_alert(alert)
        await self._emit_alert_created(alert)

        if cve.severity.value == "critical":
            await emit_cve_event(
                CVEHunterEvents.CRITICAL_DISCOVERY,
                {
                    "cve_id": cve.cve_id,
                    "title": cve.title,
                    "severity": cve.severity.value,
                    "cwe_ids": cve.cwe_ids,
                    "cvss_score": cve.cvss_score,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return alert

    async def _persist_alert(self, alert: VulnerabilityAlert) -> None:
        """Persist alert to analytics DB."""
        try:
            from ...persistence import CVEHunterDAO

            await CVEHunterDAO.save_alert(alert)
        except Exception as e:
            logger.error(f"Failed to persist alert {alert.alert_id}: {e}")

    def _update_agent_status(
        self,
        agent_id: str,
        status: AgentTaskStatus,
        task: Optional[str] = None,
    ) -> None:
        """Update agent status."""
        if agent_id in self._agent_statuses:
            self._agent_statuses[agent_id].status = status
            self._agent_statuses[agent_id].current_task = task
            self._agent_statuses[agent_id].last_active = datetime.now(timezone.utc)
