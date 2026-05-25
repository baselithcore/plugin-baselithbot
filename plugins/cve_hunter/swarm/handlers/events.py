"""Event Handler for CVE Hunter Swarm."""

import asyncio
import logging
from core.observability.logging import get_logger
from typing import Any, Callable, Coroutine, Dict, List, Optional

try:
    from core.events import EventBus
    from ...events import CVEHunterEvents, emit_cve_event
except ImportError:
    from core.events import EventBus  # type: ignore[no-redef]
    from plugins.cve_hunter.events import CVEHunterEvents, emit_cve_event  # type: ignore[no-redef]

logger = get_logger(__name__)
stdlib_logger = logging.getLogger(__name__)

# Type alias for scan callback
ScanCallback = Callable[[List[str]], Coroutine[Any, Any, List[Dict[str, Any]]]]


class EventsHandler:
    """Handles event subscriptions for CVE Hunter.

    Subscribes to:
    - Internal CVE Hunter events (discovery, analysis)
    - External Honeypot events for cross-plugin correlation

    Supports on-demand scanning when cache miss occurs during Honeypot lookup.
    """

    def __init__(self, event_bus: EventBus):
        """Initialize event handler.

        Args:
            event_bus: Event bus instance
        """
        self._event_bus = event_bus
        self._cve_cache: Dict[str, Any] = {}
        self._scan_callback: Optional[ScanCallback] = None
        self._pending_scans: Dict[str, asyncio.Task[None]] = {}
        self._log_callback: Optional[Callable[[str, bool, bool], None]] = None
        self._analyzer: Optional[Any] = None

    def set_analyzer(self, analyzer: Any) -> None:
        """Set reference to analyzer agent.

        Args:
            analyzer: CVEAnalyzerAgent instance
        """
        self._analyzer = analyzer

    def set_cve_cache(self, cache: Dict[str, Any]) -> None:
        """Set reference to swarm CVE cache for lookups.

        Args:
            cache: Reference to CVEHunterSwarm's _cve_cache
        """
        self._cve_cache = cache

    def set_scan_callback(self, callback: ScanCallback) -> None:
        """Set callback to trigger on-demand CVE scans.

        Args:
            callback: Async function that accepts CWE list and returns CVE records
        """
        self._scan_callback = callback

    @staticmethod
    def _log_with_stdlib(level: str, message: str) -> None:
        """Mirror key integration logs to stdlib logging for test capture."""
        getattr(logger, level)(message)
        getattr(stdlib_logger, level)(message)

    async def _trigger_targeted_scan(
        self, cwes: List[str], category: str
    ) -> List[Dict[str, Any]]:
        """Trigger a targeted CVE scan for specific CWEs.

        Args:
            cwes: List of CWE IDs to search for
            category: Attack category for logging

        Returns:
            List of matched CVE records
        """
        if not self._scan_callback:
            self._log_with_stdlib(
                "warning", "No scan callback configured for on-demand scans"
            )
            return []

        self._log_with_stdlib("info", f"Triggering on-demand CVE scan for CWEs: {cwes}")

        try:
            # Call the scan callback (provided by coordinator)
            matched_cves = await self._scan_callback(cwes)
            self._log_with_stdlib(
                "info",
                f"On-demand scan completed: found {len(matched_cves)} CVEs "
                f"for category {category}",
            )
            return matched_cves
        except Exception as e:
            self._log_with_stdlib("error", f"On-demand scan failed: {e}")
            return []

    def subscribe(self) -> None:
        """Subscribe to relevant events."""
        if not self._event_bus:
            return

        # =====================================================================
        # Internal CVE Hunter Events
        # =====================================================================

        @self._event_bus.on(CVEHunterEvents.DISCOVERY_POTENTIAL)
        async def on_potential_discovery(data: Dict[str, Any]) -> None:
            logger.debug(f"Potential discovery detected: {data}")
            # Could trigger additional analysis or team formation here

        @self._event_bus.on(CVEHunterEvents.CVE_ANALYZED)
        async def on_cve_analyzed(data: Dict[str, Any]) -> None:
            logger.debug(f"CVE analyzed: {data.get('cve_id')}")
            # Could store analysis in memory here

        # =====================================================================
        # Cross-Plugin: Honeypot Integration Events
        # =====================================================================

        @self._event_bus.on("honeypot.integration.attack_for_analysis")
        async def on_attack_for_analysis(data: Dict[str, Any]) -> None:
            """Handle deep analysis request from Honeypot."""
            if not self._analyzer:
                logger.warning(
                    "Received analysis request but no analyzer agent configured"
                )
                return

            payload = data.get("payload")
            context = data.get("context", {})
            request_id = data.get("request_id")

            logger.info(f"Received deep analysis request {request_id}")

            # Perform analysis
            try:
                result = await self._analyzer.analyze_attack_payload(payload, context)

                # Emit result back to Honeypot
                await emit_cve_event(
                    "honeypot.attack.analyzed",
                    {
                        "request_id": request_id,
                        "analysis": result,
                        "original_context": context,
                        "timestamp": result.get("timestamp"),
                    },
                )
                logger.info(f"Completed deep analysis for request {request_id}")
            except Exception as e:
                logger.error(f"Failed to process analysis request: {e}")

        @self._event_bus.on("honeypot.integration.request_cve_lookup")
        async def on_honeypot_cve_lookup(data: Dict[str, Any]) -> None:
            """Handle CVE lookup request from Honeypot plugin.

            When Honeypot detects an attack pattern, it may request CVE lookup
            to correlate the attack with known vulnerabilities.

            If no cached CVEs match, triggers an on-demand scan.
            """
            cwes = data.get("cwes", [])
            category = data.get("category", "unknown")
            patterns = data.get("patterns", [])

            self._log_with_stdlib(
                "info",
                f"CVE lookup requested by Honeypot: "
                f"category={category}, cwes={cwes}, patterns={patterns}",
            )

            # Search cached CVEs for matching CWEs
            matching_cves = self._search_cache_for_cwes(cwes)

            if matching_cves:
                self._log_with_stdlib(
                    "info",
                    f"Found {len(matching_cves)} CVEs in cache matching Honeypot request",
                )
                await self._emit_lookup_response(category, cwes, matching_cves)
            else:
                # No cache hit - trigger on-demand scan
                self._log_with_stdlib(
                    "info",
                    f"No cached CVEs for CWEs {cwes}, triggering on-demand scan",
                )
                scanned_cves = await self._trigger_targeted_scan(cwes, category)

                if scanned_cves:
                    await self._emit_lookup_response(category, cwes, scanned_cves)
                else:
                    # Emit empty response so Honeypot knows scan completed
                    await self._emit_lookup_response(
                        category, cwes, [], scan_triggered=True
                    )

        @self._event_bus.on("honeypot.attack.detected")
        async def on_honeypot_attack(data: Dict[str, Any]) -> None:
            """Handle attack detection notification from Honeypot.

            Useful for real-time threat intelligence correlation.
            """
            category = data.get("category", "unknown")
            severity = data.get("severity", "info")
            source_ip = data.get("source_ip", "unknown")

            self._log_with_stdlib(
                "debug",
                f"Honeypot attack detected: {category} ({severity}) from {source_ip}",
            )
            # Could trigger proactive CVE scanning based on attack patterns

        @self._event_bus.on("honeypot.attack.high_severity")
        async def on_honeypot_high_severity(data: Dict[str, Any]) -> None:
            """Handle high-severity attack notification from Honeypot."""
            category = data.get("category", "unknown")
            source_ip = data.get("source_ip", "unknown")

            logger.warning(
                f"High-severity attack from Honeypot: {category} from {source_ip}"
            )
            # Could trigger immediate CVE correlation or alerting

        @self._event_bus.on("honeypot.cve.correlation_found")
        async def on_correlation_found(data: Dict[str, Any]) -> None:
            """Handle CVE correlation found by Honeypot.

            When Honeypot correlates an attack to a CVE, record it as a finding/discovery
            in CVE Hunter so it appears in the dashboard.
            """
            correlation_id = data.get("correlation_id")
            attack_pattern = data.get("attack_pattern")
            matched_cves = data.get("matched_cves", [])
            confidence = data.get("confidence", 0.0)

            logger.info(
                f"Received correlation from Honeypot: {correlation_id}. "
                f"Attack '{attack_pattern}' matched {len(matched_cves)} CVEs."
            )

            # Create a discovery log entry
            log_message = (
                f"CORRELATOR: Linked attack '{attack_pattern}' to {len(matched_cves)} CVEs "
                f"(Confidence: {confidence:.2f})"
            )

            # Use the callback to add discovery log if available (need to add this capability)
            # For now, we'll try to use the swarm instance if accessible, or just log
            # Ideally, EventsHandler should have access to _add_discovery_log or similar

            # Note: We need to inject the log callback into EventsHandler similar to scan_callback
            if self._log_callback:
                self._log_callback(log_message, is_alert=True)

    def set_log_callback(self, callback: Callable[[str, bool, bool], None]) -> None:
        """Set callback for discovery logging."""
        self._log_callback = callback

    def _search_cache_for_cwes(self, cwes: List[str]) -> List[Dict[str, Any]]:
        """Search cached CVEs for matching CWEs.

        Args:
            cwes: List of CWE IDs to match

        Returns:
            List of matched CVE records as dicts
        """
        matching_cves = []
        for cve_id, cve_record in self._cve_cache.items():
            cve_cwes = getattr(cve_record, "cwe_ids", []) or []
            if any(cwe in cve_cwes for cwe in cwes):
                # Handle both CVERecord objects and dicts
                if hasattr(cve_record, "severity"):
                    severity = cve_record.severity
                    # Handle enum values
                    if hasattr(severity, "value"):
                        severity = severity.value
                else:
                    severity = (
                        cve_record.get("severity")
                        if isinstance(cve_record, dict)
                        else None
                    )

                matching_cves.append(
                    {
                        "cve_id": cve_id,
                        "severity": severity,
                        "cvss_score": getattr(cve_record, "cvss_score", 0.0),
                        "title": getattr(cve_record, "title", None),
                        "cwe_ids": cve_cwes,
                    }
                )
        return matching_cves

    async def _emit_lookup_response(
        self,
        category: str,
        cwes: List[str],
        matched_cves: List[Dict[str, Any]],
        scan_triggered: bool = False,
    ) -> None:
        """Emit CVE lookup response event.

        Args:
            category: Original request category
            cwes: Original request CWEs
            matched_cves: List of matched CVE records
            scan_triggered: Whether an on-demand scan was triggered
        """
        await emit_cve_event(
            "cve_hunter.integration.cve_lookup_response",
            {
                "request_category": category,
                "request_cwes": cwes,
                "matched_cves": matched_cves[:10],  # Limit results
                "total_matches": len(matched_cves),
                "on_demand_scan_triggered": scan_triggered,
            },
        )
