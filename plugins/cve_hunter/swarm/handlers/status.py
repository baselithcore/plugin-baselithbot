"""Status mixin for CVE Hunter Swarm Coordinator.

Provides status retrieval, CVE queries, alerts, and statistics methods.
"""

from __future__ import annotations

from core.observability.logging import get_logger
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol

from ...models import (
    AgentTaskStatus,
    CVEAgentStatus,
    CVERecord,
    CVEStats,
    ScanResult,
    SwarmStatus,
    VulnerabilityAlert,
)

if TYPE_CHECKING:
    from ...config import CVEHunterConfig
    from .feedback import FeedbackHandler

logger = get_logger(__name__)


class StatusProtocol(Protocol):
    """Protocol defining required attributes for StatusMixin."""

    config: CVEHunterConfig
    _colony: Any
    _cve_cache: Dict[str, CVERecord]
    _alerts: List[VulnerabilityAlert]
    _agent_statuses: Dict[str, CVEAgentStatus]
    _scan_results: List[ScanResult]
    _correlator: Any
    feedback_handler: FeedbackHandler

    def _add_discovery_log(
        self, message: str, is_alert: bool = False, is_error: bool = False
    ) -> None: ...


class StatusMixin:
    """Mixin providing status, CVE queries, and statistics methods."""

    def get_status(self: StatusProtocol) -> SwarmStatus:
        """Get current swarm status."""
        colony_stats = self._colony.get_stats()

        return SwarmStatus(
            active_agents=colony_stats.get("active_agents", 0),
            queued_tasks=colony_stats.get("pending_tasks", 0),
            completed_tasks=colony_stats.get("completed_tasks", 0),
            failed_tasks=colony_stats.get("failed_tasks", 0),
            agents=list(self._agent_statuses.values()),
            last_scan=self._scan_results[-1].completed_at
            if self._scan_results
            else None,
            is_scanning=any(
                s.status == AgentTaskStatus.SCANNING
                for s in self._agent_statuses.values()
            ),
        )

    def get_cves(
        self: StatusProtocol,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[CVERecord]:
        """Get cached CVEs with optional filtering."""
        cves = list(self._cve_cache.values())

        if severity:
            cves = [c for c in cves if c.severity.value == severity]

        cves.sort(key=lambda c: c.cvss_score, reverse=True)
        return cves[:limit]

    def get_alerts(
        self: StatusProtocol, include_acknowledged: bool = False
    ) -> List[VulnerabilityAlert]:
        """Get active alerts."""
        if include_acknowledged:
            return self._alerts
        return [a for a in self._alerts if not a.acknowledged]

    def acknowledge_alert(
        self: StatusProtocol, alert_id: str, by: str = "system"
    ) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = by
                return True
        return False

    def get_stats(self: StatusProtocol) -> CVEStats:
        """Get aggregated CVE statistics."""
        cves = list(self._cve_cache.values())

        return CVEStats(
            total_cves=len(cves),
            critical_count=sum(1 for c in cves if c.severity.value == "critical"),
            high_count=sum(1 for c in cves if c.severity.value == "high"),
            medium_count=sum(1 for c in cves if c.severity.value == "medium"),
            low_count=sum(1 for c in cves if c.severity.value == "low"),
            with_exploit=sum(1 for c in cves if c.exploit_available),
            with_patch=sum(1 for c in cves if c.patch_available),
            active_alerts=len([a for a in self._alerts if not a.acknowledged]),
            sources_active=self.config.enabled_sources,
        )

    async def get_attack_chains(self: StatusProtocol) -> List[Dict[str, Any]]:
        """Get detected attack chains from correlated CVEs."""
        cves = list(self._cve_cache.values())
        if len(cves) < 2:
            return []

        self._add_discovery_log(
            f"CORRELATOR: Analyzing correlation graph for {len(cves)} CVEs..."
        )

        try:
            chains = await self._correlator.detect_attack_chains(cves)

            if chains:
                self._add_discovery_log(
                    f"CORRELATOR: Detected {len(chains)} potential attack chains."
                )

            return [
                {
                    "chain_id": chain.chain_id,
                    "name": chain.name,
                    "cve_ids": chain.cve_ids
                    if getattr(chain, "cve_ids", None)
                    else [stage["cve_id"] for stage in chain.stages],
                    "stages": chain.stages,
                    "total_severity": chain.total_severity,
                    "description": chain.description,
                    "mitre_techniques": chain.mitre_techniques,
                    "ai_analysis": getattr(chain, "ai_analysis", None),
                }
                for chain in chains
            ]
        except Exception as e:
            logger.error(f"Failed to detect attack chains: {e}")
            self._add_discovery_log(
                f"CORRELATOR: Error analyzing chains: {str(e)}", is_error=True
            )
            return []

    async def get_correlations(self: StatusProtocol) -> List[Dict[str, Any]]:
        """Get CVE correlations (common CWE, product, etc.)."""
        cves = list(self._cve_cache.values())
        if len(cves) < 2:
            return []

        try:
            correlations = await self._correlator.find_correlations(cves)
            items = []
            for correlation in correlations:
                data = correlation.to_dict()
                data["feedback"] = self.feedback_handler.get_outcome(
                    self.feedback_handler.cve_correlation_feedback,
                    correlation.correlation_id,
                )
                items.append(data)
            return items
        except Exception as e:
            logger.error(f"Failed to find correlations: {e}")
            return []
