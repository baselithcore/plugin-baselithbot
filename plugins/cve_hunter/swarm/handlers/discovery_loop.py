"""CVE Hunter Discovery Loop Mixin.

Handles zero-day discovery loop, log management, unified findings,
and finding correlation logic for CVEHunterSwarm.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, TYPE_CHECKING

from core.observability.logging import get_logger

from ...models import AgentTaskStatus

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class DiscoveryLoopMixin:
    """Mixin providing discovery loop, logs, and finding correlation methods."""

    async def _discovery_loop(self) -> None:
        """Run continuous zero-day discovery loop."""
        self._ensure_tenant_context()
        while self._is_running:
            try:
                self._update_agent_status(
                    "discovery-1", AgentTaskStatus.SCANNING, "Hunting Zero-Days"
                )

                async for event in self._discovery.scan_online_sources():
                    if event["type"] == "log":
                        self._add_discovery_log(event["message"])
                    elif event["type"] == "finding":
                        self._findings.append(event["data"])
                        if len(self._findings) > 50:
                            self._findings.pop(0)

                        alert = await self._discovery.generate_discovery_alert(
                            event["data"]
                        )
                        if alert:
                            self._alerts.append(alert)
                            self._add_discovery_log(
                                f"⚠ POTENTIAL ZERO-DAY DETECTED: {alert.cve.title}",
                                is_alert=True,
                            )
                        else:
                            self._add_discovery_log(
                                f"DISCOVERY: Analyzing candidate: "
                                f"{event['data'].get('pattern', 'unknown')}...",
                                is_alert=False,
                            )
                    elif event["type"] == "error":
                        self._add_discovery_log(event["message"], is_error=True)

            except Exception as e:
                logger.error(f"Discovery loop error: {e}")
                self._add_discovery_log(f"System Error: {str(e)}", is_error=True)

            finally:
                self._update_agent_status("discovery-1", AgentTaskStatus.IDLE)

            await __import__("asyncio").sleep(120)

    def _add_discovery_log(
        self, message: str, is_alert: bool = False, is_error: bool = False
    ) -> None:
        """Add a log entry to the live hunt stream."""
        self._discovery_logs.append(
            {
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_alert": is_alert,
                "is_error": is_error,
            }
        )
        if len(self._discovery_logs) > 1000:
            self._discovery_logs.pop(0)

    def get_discovery_logs(self) -> List[Dict[str, Any]]:
        """Get recent discovery logs."""
        return self._discovery_logs

    def get_findings(self) -> List[Dict[str, Any]]:
        """Get recent raw findings."""
        return self._findings

    def get_unified_findings(self) -> List[Dict[str, Any]]:
        """Get unified findings across SAST/DAST/Discovery."""
        return self._build_unified_findings()

    def get_finding_correlations(self) -> Dict[str, Any]:
        """Correlate findings with CVEs and attack chain patterns."""
        unified = self._build_unified_findings()
        cve_correlations = self._correlate_findings_with_cves(unified)
        chain_correlations = self._correlate_findings_with_attack_patterns(unified)
        return {
            "summary": {
                "total_findings": len(unified),
                "cve_correlations": len(cve_correlations),
                "attack_chain_candidates": len(chain_correlations),
            },
            "cve_correlations": cve_correlations,
            "attack_chain_candidates": chain_correlations,
        }

    def _build_unified_findings(self) -> List[Dict[str, Any]]:
        """Build unified findings list using FindingsHandler."""
        return self.findings_handler.build_unified_findings(
            self._sast_findings,
            self._dast_findings,
            self._findings,
        )

    def _correlate_findings_with_cves(
        self, unified: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Correlate findings with known CVEs based on CWE overlap."""
        correlations = []
        cve_cwe_index: Dict[str, List[str]] = {}

        for cve in self._cve_cache.values():
            for cwe in cve.cwe_ids or []:
                if cwe not in cve_cwe_index:
                    cve_cwe_index[cwe] = []
                cve_cwe_index[cwe].append(cve.cve_id)

        for finding in unified:
            finding_cwes = finding.get("cwe_ids", [])
            matched_cves = set()
            for cwe in finding_cwes:
                matched_cves.update(cve_cwe_index.get(cwe, []))

            if matched_cves:
                correlations.append(
                    {
                        "finding_id": finding.get("finding_id"),
                        "pattern": finding.get("pattern"),
                        "matched_cves": sorted(matched_cves)[:10],
                        "match_count": len(matched_cves),
                    }
                )

        return correlations

    def _correlate_findings_with_attack_patterns(
        self, unified: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify findings that chain together into attack patterns."""
        chain_candidates = []
        location_groups: Dict[str, List[Dict[str, Any]]] = {}

        for finding in unified:
            loc = finding.get("location", "unknown")
            if loc not in location_groups:
                location_groups[loc] = []
            location_groups[loc].append(finding)

        for loc, findings in location_groups.items():
            if len(findings) >= 2:
                chain_candidates.append(
                    {
                        "location": loc,
                        "findings": [f.get("finding_id") for f in findings],
                        "patterns": [f.get("pattern") for f in findings],
                        "combined_score": sum(f.get("score", 0) for f in findings),
                    }
                )

        chain_candidates.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        return chain_candidates[:20]
