"""Analysis mixin for CVE Hunter Swarm Coordinator.

Provides CVE analysis, attack chain analysis, memory storage, and event emission.
"""

from __future__ import annotations

from core.observability.logging import get_logger
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol

from plugins.cve_hunter.events import (
    AlertEventData,
    CVEHunterEvents,
    ScanEventData,
    emit_cve_event,
)
from plugins.cve_hunter.models import CVERecord, ScanResult, VulnerabilityAlert

if TYPE_CHECKING:
    from ...config import CVEHunterConfig
    from ...memory.manager import CVEHunterMemory
    from .reporting import ReportingHandler

logger = get_logger(__name__)


class AnalysisProtocol(Protocol):
    """Protocol defining required attributes for AnalysisMixin."""

    config: CVEHunterConfig
    _cve_cache: Dict[str, CVERecord]
    _memory: Optional[CVEHunterMemory]
    _event_bus: Any
    reporting_handler: ReportingHandler

    def get_stats(self) -> Any: ...
    async def get_attack_chains(self) -> List[Dict[str, Any]]: ...
    def get_cves(
        self, severity: Optional[str] = None, limit: int = 100
    ) -> List[CVERecord]: ...
    def get_findings(self) -> List[Dict[str, Any]]: ...


class AnalysisMixin:
    """Mixin providing analysis, memory, and event methods."""

    async def analyze_situation(self: AnalysisProtocol) -> str:
        """Perform a strategic AI analysis of the current situation."""
        stats = self.get_stats()
        chains = await self.get_attack_chains()
        top_cves = self.get_cves(limit=10)
        findings = self.get_findings()

        return await self.reporting_handler.analyze_situation(
            stats, chains, top_cves, findings
        )

    async def analyze_cve(self: AnalysisProtocol, cve_id: str) -> Optional[CVERecord]:
        """Analyze a specific CVE on demand."""
        cve = self._cve_cache.get(cve_id)
        if not cve:
            return None

        def cache_update(cid: str, record: CVERecord) -> None:
            self._cve_cache[cid] = record

        return await self.reporting_handler.analyze_cve(cve, cache_update)

    async def analyze_attack_chain(
        self: AnalysisProtocol, chain_id: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze a specific attack chain on demand."""
        chains = await self.get_attack_chains()
        target_chain = next((c for c in chains if c["chain_id"] == chain_id), None)

        if not target_chain:
            return None

        return await self.reporting_handler.analyze_attack_chain(target_chain)

    async def _store_cves_in_memory(
        self: AnalysisProtocol, cves: List[CVERecord]
    ) -> None:
        """Store CVEs in the memory system for future recall."""
        if not self._memory:
            return

        for cve in cves[:20]:
            try:
                await self._memory.remember_cve(
                    cve_id=cve.cve_id,
                    description=cve.description,
                    severity=cve.severity.value,
                    cvss_score=cve.cvss_score,
                    source=cve.source.value if cve.source else "unknown",
                    metadata={
                        "cwe_ids": cve.cwe_ids,
                        "exploit_available": cve.exploit_available,
                        "patch_available": cve.patch_available,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to store CVE {cve.cve_id}: {e}")

    async def _emit_scan_completed(self: AnalysisProtocol, result: ScanResult) -> None:
        """Emit scan completed event."""
        if not self._event_bus or not self.config.enable_events:
            return

        try:
            event_data = ScanEventData(
                scan_id=result.scan_id,
                source=result.source.value if result.source else "unknown",
                cves_found=result.cves_found,
                new_cves=result.new_cves,
                duration_seconds=result.duration_seconds or 0.0,
                errors=result.errors,
                timestamp=result.completed_at,
            )
            await emit_cve_event(CVEHunterEvents.SCAN_COMPLETED, event_data.to_dict())
        except Exception as e:
            logger.warning(f"Failed to emit scan completed event: {e}")

    async def _emit_alert_created(
        self: AnalysisProtocol, alert: VulnerabilityAlert
    ) -> None:
        """Emit alert created event."""
        if not self._event_bus or not self.config.enable_events:
            return

        try:
            event_data = AlertEventData(
                alert_id=alert.alert_id,
                cve_id=alert.cve.cve_id,
                alert_type=alert.alert_type,
                priority=alert.priority,
                severity=alert.cve.severity.value,
                timestamp=alert.created_at,
            )
            await emit_cve_event(CVEHunterEvents.ALERT_CREATED, event_data.to_dict())
        except Exception as e:
            logger.warning(f"Failed to emit alert created event: {e}")
