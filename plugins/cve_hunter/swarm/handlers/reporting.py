"""Reporting and Analysis Handler for CVE Hunter Swarm."""

from core.observability.logging import get_logger
from typing import Any, Dict, List, Optional

try:
    from ...agents.analyzer import CVEAnalyzerAgent
    from ...models import CVERecord, AgentTaskStatus
except ImportError:
    from plugins.cve_hunter.agents.analyzer import CVEAnalyzerAgent  # type: ignore[no-redef]
    from plugins.cve_hunter.models import CVERecord, AgentTaskStatus  # type: ignore[no-redef]

logger = get_logger(__name__)


class ReportingHandler:
    """Handles report generation and AI-driven analysis for CVE Hunter."""

    def __init__(
        self, analyzer: CVEAnalyzerAgent, status_callback: Any, log_callback: Any
    ):
        """Initialize reporting handler.

        Args:
            analyzer: Analyzer agent instance
            status_callback: Callback to update agent status
            log_callback: Callback to add discovery logs
        """
        self._analyzer = analyzer
        self._status_callback = status_callback
        self._log_callback = log_callback

    async def analyze_situation(
        self,
        stats: Any,
        chains: List[Dict[str, Any]],
        top_cves: List[CVERecord],
        findings: List[Dict[str, Any]],
    ) -> str:
        """Perform a strategic AI analysis of the current situation.

        Returns:
            Markdown formatted situation report
        """
        self._status_callback(
            "analyzer-1", AgentTaskStatus.ANALYZING, "Generating Strategic Report"
        )
        self._log_callback("ANALYZER: Generating tactical situation report...")

        try:
            report = await self._analyzer.analyze_strategic_situation(
                stats=stats,
                active_chains=chains,
                top_cves=top_cves,
                recent_findings=findings,
            )
            self._log_callback("ANALYZER: Strategic report generated.")
            return report
        finally:
            self._status_callback("analyzer-1", AgentTaskStatus.IDLE)

    async def analyze_cve(
        self, cve: CVERecord, cache_update_callback: Any
    ) -> Optional[CVERecord]:
        """Analyze a specific CVE on demand.

        Args:
            cve: The CVE record to analyze
            cache_update_callback: Callback to update the CVE cache

        Returns:
            Updated CVERecord if found and analyzed, None otherwise.
        """
        cve_id = cve.cve_id
        self._status_callback(
            "analyzer-1", AgentTaskStatus.ANALYZING, f"Analyzing {cve_id}"
        )
        self._log_callback(f"ANALYZER: Performing on-demand analysis for {cve_id}")

        try:
            analysis = await self._analyzer.analyze_cve(cve)
            if analysis.get("ai_summary"):
                cve.ai_summary = analysis["ai_summary"]
                cache_update_callback(cve_id, cve)
                return cve
            return cve
        except Exception as e:
            logger.error(f"On-demand analysis failed for {cve_id}: {e}")
            self._log_callback(
                f"ANALYZER: Analysis failed for {cve_id}: {e}", is_error=True
            )
            return cve
        finally:
            self._status_callback("analyzer-1", AgentTaskStatus.IDLE)

    async def analyze_attack_chain(
        self, target_chain: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze a specific attack chain on demand.

        Args:
            target_chain: Dict containing chain info

        Returns:
            Dict containing chain info and AI analysis
        """
        chain_id = target_chain.get("chain_id", "unknown")
        self._status_callback(
            "analyzer-1", AgentTaskStatus.ANALYZING, f"Analyzing Chain {chain_id}"
        )
        self._log_callback(
            f"ANALYZER: Analyzing attack chain: {target_chain.get('name', 'unknown')}"
        )

        try:
            analysis = await self._analyzer.analyze_attack_chain(target_chain)
            target_chain["ai_analysis"] = analysis
            return target_chain
        except Exception as e:
            logger.error(f"Chain analysis failed: {e}")
            target_chain["error"] = str(e)
            return target_chain
        finally:
            self._status_callback("analyzer-1", AgentTaskStatus.IDLE)
