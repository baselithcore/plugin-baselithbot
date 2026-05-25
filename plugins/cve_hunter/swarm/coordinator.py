"""CVE Hunter Swarm Coordinator.

Coordinates multiple CVE agents using swarm intelligence patterns
from core/swarm including auction-based task allocation.

Integrates with core framework:
- EventBus for cross-agent communication
- AgentMemory for CVE knowledge persistence
- PheromoneSystem for swarm signals
- FeedbackHandler for learning from feedback
"""

import asyncio
from core.observability.logging import get_logger
from core.context import get_current_tenant_id, set_tenant_context
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4


from core.swarm import Colony
from core.swarm.types import AgentProfile, AgentStatus

from ..agents import (
    CVEScannerAgent,
    CVEAnalyzerAgent,
    CVEDiscoveryAgent,
    CVECorrelatorAgent,
)
from ..config import CVEHunterConfig, get_cve_hunter_config
from ..events import (
    CVEHunterEvents,
    emit_cve_event,
    get_event_bus,
)
from ..memory import CVEHunterMemory, initialize_memory
from ..metrics import CVEHunterMetrics, get_cve_hunter_metrics
from ..vector_store import CVEVectorStore, get_cve_vector_store
from ..models import (
    AgentTaskStatus,
    CVEAgentStatus,
    CVERecord,
    DASTFinding,
    DASTScanResult,
    SASTFinding,
    SASTScanResult,
    ScanResult,
    VulnerabilityAlert,
)
from .handlers.events import EventsHandler
from .handlers.feedback import FeedbackHandler
from .handlers.reporting import ReportingHandler
from .handlers.sast_tools import SASTToolsHandler
from .handlers.dast_tools import DASTToolsHandler
from .handlers.findings import FindingsHandler
from .handlers.correlations import CorrelationsHandler
from .handlers.scanning import ScanningMixin
from .handlers.status import StatusMixin
from .handlers.analysis import AnalysisMixin
from ..utils.hashing import stable_finding_id

if TYPE_CHECKING:
    from core.events import EventBus

logger = get_logger(__name__)


class CVEHunterSwarm(ScanningMixin, StatusMixin, AnalysisMixin):
    """Swarm coordinator for CVE hunting agents.

    Manages a colony of specialized agents (Scanner, Analyzer, Discovery)
    using auction-based task allocation and pheromone coordination.

    Example:
        ```python
        swarm = CVEHunterSwarm()
        await swarm.start()
        status = swarm.get_status()
        ```
    """

    def __init__(
        self,
        config: Optional[CVEHunterConfig] = None,
        colony: Optional[Colony] = None,
        memory: Optional[CVEHunterMemory] = None,
        event_bus: Optional["EventBus"] = None,
        metrics: Optional[CVEHunterMetrics] = None,
        vector_store: Optional[CVEVectorStore] = None,
    ):
        """Initialize CVE Hunter swarm.

        Args:
            config: CVE Hunter configuration
            colony: Optional Colony instance (creates new if not provided)
            memory: Optional CVEHunterMemory instance (for DI/testing)
            event_bus: Optional EventBus instance (for DI/testing)
            metrics: Optional metrics collector (defaults to module singleton)
            vector_store: Optional vector store (defaults to module singleton)
        """
        self.config = config or get_cve_hunter_config()
        self._colony = colony or Colony()

        # Core framework integration
        self._memory = memory
        self._event_bus = event_bus
        self.metrics: CVEHunterMetrics = metrics or get_cve_hunter_metrics()
        self.vector_store: CVEVectorStore = vector_store or get_cve_vector_store()
        self._cache_lock = asyncio.Lock()

        # CVE-specific agents
        self._scanner = CVEScannerAgent(config=self.config)
        self._analyzer = CVEAnalyzerAgent(config=self.config)
        self._discovery = CVEDiscoveryAgent(config=self.config)
        self._correlator = CVECorrelatorAgent(config=self.config)

        # State
        self._cve_cache: Dict[str, CVERecord] = {}
        self._alerts: List[VulnerabilityAlert] = []
        self._scan_results: List[ScanResult] = []
        self._discovery_logs: List[Dict[str, Any]] = []  # Live hunt logs
        self._findings: List[Dict[str, Any]] = []  # Live hunt logs
        self._sast_findings: List[SASTFinding] = []
        self._sast_scan_results: List[SASTScanResult] = []
        self._dast_findings: List[DASTFinding] = []
        self._dast_scan_results: List[DASTScanResult] = []

        # Handlers
        self.feedback_handler = FeedbackHandler(self._memory, self._discovery)
        self.events_handler: Optional[EventsHandler] = None
        self.reporting_handler = ReportingHandler(
            self._analyzer, self._update_agent_status, self._add_discovery_log
        )
        # New modular handlers
        self.sast_tools_handler = SASTToolsHandler(
            self.config, log_callback=self._add_discovery_log
        )
        self.dast_tools_handler = DASTToolsHandler(
            self.config, log_callback=self._add_discovery_log
        )
        self.findings_handler = FindingsHandler(
            self.config, log_callback=self._add_discovery_log
        )
        # Correlations handler initialized after _correlator is available
        self._is_running = False
        self._scan_task: Optional[asyncio.Task[None]] = None
        self._discovery_task: Optional[asyncio.Task[None]] = None

        # Agent profiles for colony
        self._agent_profiles: Dict[str, AgentProfile] = {}
        self._agent_statuses: Dict[str, CVEAgentStatus] = {}

        # Initialize correlations handler (needs feedback_handler and _correlator)
        self.correlations_handler = CorrelationsHandler(
            feedback_handler=self.feedback_handler,
            correlator=self._correlator,
            log_callback=self._add_discovery_log,
        )

    async def start(self) -> None:
        """Start the CVE Hunter swarm."""
        if self._is_running:
            return

        # Capture tenant context so background tasks can re-establish it.
        # PEP 567 propagates contextvars into `asyncio.create_task` by
        # default, but we re-apply it inside each loop to remain correct
        # when the swarm is started from a context with no tenant set
        # (e.g. CLI scripts) and `strict_tenant_isolation` is enabled.
        try:
            self._tenant_id: Optional[str] = (
                self.config.tenant_id or get_current_tenant_id()
            )
        except Exception:
            self._tenant_id = self.config.tenant_id
        if self._tenant_id:
            logger.info(
                "Starting CVE Hunter swarm",
                extra={
                    "tenant_id": self._tenant_id,
                    "isolation_mode": self.config.isolation_mode,
                },
            )
        else:
            logger.info("Starting CVE Hunter swarm")
        self._is_running = True

        # Initialize core framework integrations
        await self._initialize_framework_integration()

        # Initialize Analytics Schema
        # Initialize Analytics Schema and Load Data
        try:
            from ..persistence import CVEHunterDAO

            await CVEHunterDAO.ensure_schema()
            logger.info("CVE Hunter analytics schema initialized")

            # Load persisted CVEs
            loaded_cves = await CVEHunterDAO.load_all_cves()
            for cve in loaded_cves:
                self._cve_cache[cve.cve_id] = cve

            logger.info(f"Loaded {len(loaded_cves)} CVEs from persistence")

        except Exception as e:
            logger.error(f"Failed to initialize analytics persistence: {e}")

        # Initialize vector store (best effort — semantic search is optional).
        try:
            await self.vector_store.initialize()
        except Exception as e:
            logger.warning(
                "Vector store initialization failed", extra={"error": str(e)}
            )

        # Register agents with colony
        await self._register_agents()
        self.metrics.set_active_agents(len(self._agent_profiles))
        self.metrics.set_cve_cache_size(len(self._cve_cache))

        # Start periodic scanning
        self._scan_task = asyncio.create_task(self._periodic_scan_loop())
        # Start continuous discovery
        self._discovery_task = asyncio.create_task(self._discovery_loop())

        logger.info("CVE Hunter swarm started")

    async def _initialize_framework_integration(self) -> None:
        """Initialize core framework integrations (memory, events)."""
        # Initialize memory system
        if self.config.enable_memory and self._memory is None:
            try:
                self._memory = await initialize_memory()
                # Update handler memory ref
                self.feedback_handler._memory = self._memory
                logger.info("CVE Hunter memory system initialized")
                await self.feedback_handler.load_from_memory()
            except Exception as e:
                logger.warning(f"Failed to initialize memory: {e}")

        # Initialize event bus
        if self.config.enable_events and self._event_bus is None:
            self._event_bus = get_event_bus()

        if self._event_bus:
            self.events_handler = EventsHandler(self._event_bus)
            self.events_handler.set_cve_cache(self._cve_cache)
            self.events_handler.set_scan_callback(self._targeted_cwe_scan)
            self.events_handler.set_log_callback(self._add_discovery_log)
            self.events_handler.set_analyzer(self._analyzer)
            self.events_handler.subscribe()
            logger.info("CVE Hunter event system initialized")

    async def _targeted_cwe_scan(self, cwes: List[str]) -> List[Dict[str, Any]]:
        """Perform targeted CVE scan for specific CWEs.

        Called by EventsHandler when Honeypot requests lookup and cache is empty.

        Args:
            cwes: List of CWE IDs to search for

        Returns:
            List of matched CVE records as dicts
        """
        self._add_discovery_log(f"SCANNER: On-demand scan triggered for CWEs: {cwes}")
        self._update_agent_status(
            "scanner-1", AgentTaskStatus.SCANNING, f"Targeted scan for {cwes}"
        )

        matched_cves: List[Dict[str, Any]] = []

        try:
            # Scan all enabled sources
            for source in self.config.enabled_sources:
                try:
                    cves = await self._scanner.scan_source(source, days_back=30)
                    for cve in cves:
                        cve_cwes = getattr(cve, "cwe_ids", []) or []
                        if any(cwe in cve_cwes for cwe in cwes):
                            async with self._cache_lock:
                                self._cve_cache[cve.cve_id] = cve

                            severity = cve.severity
                            if hasattr(severity, "value"):
                                severity = severity.value

                            matched_cves.append(
                                {
                                    "cve_id": cve.cve_id,
                                    "severity": severity,
                                    "cvss_score": cve.cvss_score,
                                    "title": cve.title,
                                    "cwe_ids": cve_cwes,
                                }
                            )
                except Exception as e:
                    logger.warning(f"Source {source} scan failed: {e}")
                    continue

            self._add_discovery_log(
                f"SCANNER: Found {len(matched_cves)} CVEs matching CWEs {cwes}"
            )

        finally:
            self._update_agent_status("scanner-1", AgentTaskStatus.IDLE)

        return matched_cves

    async def stop(self) -> None:
        """Stop the CVE Hunter swarm."""
        if not self._is_running:
            return

        logger.info("Stopping CVE Hunter swarm...")
        self._is_running = False

        if self._scan_task:
            self._scan_task.cancel()

        if self._discovery_task:
            self._discovery_task.cancel()

        # Cleanup
        await self._scanner.close()

        # Unregister agents
        for agent_id in self._agent_profiles:
            self._colony.unregister_agent(agent_id)

        logger.info("CVE Hunter swarm stopped")

    def _ensure_tenant_context(self) -> None:
        """Re-apply the captured tenant context to the current task.

        Background tasks created via `asyncio.create_task` inherit the
        contextvars copy at scheduling time, but if the swarm was started
        before the tenant was set we still want each loop to honour the
        configured tenant when `strict_tenant_isolation` is enabled.
        """
        tenant_id = getattr(self, "_tenant_id", None) or self.config.tenant_id
        if tenant_id:
            try:
                set_tenant_context(tenant_id)
            except Exception as exc:
                logger.debug(
                    "Failed to set tenant context for background loop",
                    extra={"error": str(exc), "tenant_id": tenant_id},
                )

    async def _discovery_loop(self) -> None:
        """Run continuous zero-day discovery loop."""
        self._ensure_tenant_context()
        while self._is_running:
            try:
                self._update_agent_status(
                    "discovery-1", AgentTaskStatus.SCANNING, "Hunting Zero-Days"
                )

                # Scan online sources
                async for event in self._discovery.scan_online_sources():
                    if event["type"] == "log":
                        self._add_discovery_log(event["message"])
                    elif event["type"] == "finding":
                        self._findings.append(event["data"])
                        # Keep last 50 findings
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
                            # Should we log candidate findings that didn't make the cut?
                            self._add_discovery_log(
                                f"DISCOVERY: Analyzing candidate: {event['data'].get('pattern', 'unknown')}...",
                                is_alert=False,
                            )
                    elif event["type"] == "error":
                        self._add_discovery_log(event["message"], is_error=True)

            except Exception as e:
                logger.error(f"Discovery loop error: {e}")
                self._add_discovery_log(f"System Error: {str(e)}", is_error=True)

            finally:
                self._update_agent_status("discovery-1", AgentTaskStatus.IDLE)

            # Wait 2 minutes between hunts to be "continuous" but not spammy
            await asyncio.sleep(120)

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
        # Keep last 1000 logs
        if len(self._discovery_logs) > 1000:
            self._discovery_logs.pop(0)

    def get_discovery_logs(self) -> List[Dict[str, Any]]:
        """Get recent discovery logs."""
        return self._discovery_logs

    def get_findings(self) -> List[Dict[str, Any]]:
        """Get recent raw findings."""
        return self._findings

    def get_sast_findings(self) -> List[SASTFinding]:
        """Get recent SAST findings."""
        return self._sast_findings

    def get_dast_findings(self) -> List[DASTFinding]:
        """Get recent DAST findings."""
        return self._dast_findings

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

        # Index CVEs by CWE
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
                        "matched_cves": sorted(matched_cves)[:10],  # Limit
                        "match_count": len(matched_cves),
                    }
                )

        return correlations

    def _correlate_findings_with_attack_patterns(
        self, unified: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify findings that chain together into attack patterns."""
        # Simple heuristic: group findings by location/severity
        chain_candidates = []
        location_groups: Dict[str, List[Dict[str, Any]]] = {}

        for finding in unified:
            loc = finding.get("location", "unknown")
            if loc not in location_groups:
                location_groups[loc] = []
            location_groups[loc].append(finding)

        for loc, findings in location_groups.items():
            if len(findings) >= 2:
                # Multiple vulnerabilities at same location = potential chain
                chain_candidates.append(
                    {
                        "location": loc,
                        "findings": [f.get("finding_id") for f in findings],
                        "patterns": [f.get("pattern") for f in findings],
                        "combined_score": sum(f.get("score", 0) for f in findings),
                    }
                )

        # Sort by combined score
        chain_candidates.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        return chain_candidates[:20]  # Top 20

    def get_feedback_audit(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent feedback audit events."""
        return self.feedback_handler.get_audit_log(limit)

    async def record_sast_feedback(
        self, finding_id: str, outcome: str, source: str = "user"
    ) -> bool:
        """Record feedback for a SAST finding."""
        finding = next(
            (f for f in self._sast_findings if f.finding_id == finding_id), None
        )
        if not finding:
            return False

        success, msg = await self.feedback_handler.record_sast_feedback(
            finding, outcome, source
        )
        if success:
            self._add_discovery_log(msg)
        return success

    async def record_dast_feedback(
        self, finding_id: str, outcome: str, source: str = "user"
    ) -> bool:
        """Record feedback for a DAST finding."""
        finding = next(
            (f for f in self._dast_findings if f.finding_id == finding_id), None
        )
        if not finding:
            return False

        success, msg = await self.feedback_handler.record_dast_feedback(
            finding, outcome, source
        )
        if success:
            self._add_discovery_log(msg)
        return success

    async def record_unified_feedback(
        self, finding_id: str, outcome: str, source: str = "user"
    ) -> bool:
        """Record feedback for a unified finding."""
        if await self.record_sast_feedback(finding_id, outcome, source):
            return True
        if await self.record_dast_feedback(finding_id, outcome, source):
            return True

        for finding in self._findings:
            pattern = finding.get("pattern", "unknown")
            source_value = finding.get("source", "unknown")
            context = finding.get("context")
            if stable_finding_id(pattern, source_value, context) == finding_id:
                success, msg = await self.feedback_handler.record_discovery_feedback(
                    finding, finding_id, outcome, source
                )
                if success:
                    self._add_discovery_log(msg)
                return success

        return False

    async def record_finding_correlation_feedback(
        self, correlation_id: str, outcome: str, source: str = "user"
    ) -> bool:
        """Record feedback for a finding-to-CVE correlation."""
        success, msg = await self.feedback_handler.record_finding_correlation_feedback(
            correlation_id, outcome, source
        )
        if success:
            self._add_discovery_log(msg)
        return success

    async def record_attack_chain_feedback(
        self, chain_id: str, outcome: str, source: str = "user"
    ) -> bool:
        """Record feedback for an attack-chain candidate."""
        success, msg = await self.feedback_handler.record_attack_chain_feedback(
            chain_id, outcome, source
        )
        if success:
            self._add_discovery_log(msg)
        return success

    async def record_cve_correlation_feedback(
        self, correlation_id: str, outcome: str, source: str = "user"
    ) -> bool:
        """Record feedback for a CVE correlation."""
        success, msg = await self.feedback_handler.record_cve_correlation_feedback(
            correlation_id, outcome, source
        )
        if success:
            self._add_discovery_log(msg)
        return success

    async def _register_agents(self) -> None:
        """Register agents with the colony."""
        from core.swarm.types import Capability

        agents = [
            ("scanner-1", "scanner", ["nvd", "github", "scraping"]),
            ("analyzer-1", "analyzer", ["llm", "analysis", "scoring"]),
            ("discovery-1", "discovery", ["pattern", "anomaly", "detection"]),
        ]

        for agent_id, agent_type, cap_names in agents:
            # Convert string capabilities to Capability objects
            capabilities = [Capability(name=cap) for cap in cap_names]

            profile = AgentProfile(
                id=agent_id,
                name=f"CVE {agent_type.title()}",
                capabilities=capabilities,
                status=AgentStatus.IDLE,
            )
            self._agent_profiles[agent_id] = profile
            self._colony.register_agent(profile)

            self._agent_statuses[agent_id] = CVEAgentStatus(
                agent_id=agent_id,
                agent_type=agent_type,
                status=AgentTaskStatus.IDLE,
            )

    async def _periodic_scan_loop(self) -> None:
        """Run periodic CVE scans."""
        self._ensure_tenant_context()
        while self._is_running:
            try:
                await self.run_full_scan()
            except Exception as e:
                logger.error(f"Periodic scan error: {e}")

            # Wait for next interval
            await asyncio.sleep(self.config.scan_interval_minutes * 60)

    # Scanning methods (run_full_scan, run_sast_scan, run_dast_scan)
    # are inherited from ScanningMixin

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
                            from ..persistence import CVEHunterDAO

                            await CVEHunterDAO.save_cve(cve)
                        except Exception as e:
                            logger.error(
                                "Failed to persist analyzed CVE",
                                extra={"cve_id": cve.cve_id, "error": str(e)},
                            )

                        try:
                            await self.vector_store.index_cve(
                                cve_id=cve.cve_id,
                                description=cve.description or cve.title or cve.cve_id,
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

        # Persist alert
        await self._persist_alert(alert)

        # Emit standard alert event
        await self._emit_alert_created(alert)

        # Emit critical discovery event for proactive defense
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
            from ..persistence import CVEHunterDAO

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

    # Status methods (get_status, get_cves, get_alerts, get_stats)
    # are inherited from StatusMixin

    # get_attack_chains and get_correlations inherited from StatusMixin

    # Analysis and event methods (analyze_situation, analyze_cve, analyze_attack_chain,
    # _store_cves_in_memory, _emit_scan_completed, _emit_alert_created)
    # are inherited from AnalysisMixin
