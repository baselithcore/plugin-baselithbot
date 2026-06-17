"""HoneypotCVECorrelator core class."""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ...config import HoneypotConfig, get_honeypot_config
from ...events import (
    CVECorrelationEventData,
    HoneypotEvents,
    emit_honeypot_event,
    get_event_bus,
)
from ._constants import CWE_TO_MITRE
from ._feedback import FeedbackMixin
from ._lookup import LookupMixin

logger = get_logger(__name__)


class HoneypotCVECorrelator(LookupMixin, FeedbackMixin):
    """Correlates honeypot attacks with CVE Hunter data."""

    def __init__(self, config: Optional[HoneypotConfig] = None, cve_service=None):
        """Initialize correlator.

        Args:
            config: Honeypot configuration
            cve_service: CVE lookup service (DI)
        """
        self.config = config or get_honeypot_config()
        self._event_bus = None
        self._memory = None
        self._cve_service = cve_service  # CVE service for dynamic lookups
        self._initialized = False

        # Cache for CVE data received from CVE Hunter
        self._cve_cache: Dict[str, Dict[str, Any]] = {}
        self._correlations: List[Dict[str, Any]] = []

        # Rate limiting state
        self._last_lookup: Dict[str, datetime] = {}

        # Feedback tracking for accuracy metrics
        self._feedback: Dict[str, Dict[str, Any]] = {}
        self._accuracy_metrics = {
            "total_feedback": 0,
            "confirmed": 0,
            "rejected": 0,
            "false_positive": 0,
        }

    async def initialize(self) -> bool:
        """Initialize correlator.

        Restored EventBus integration for full plugin swarm compatibility,
        while maintaining autonomous CVE Service capability.
        """
        if self._initialized:
            return True

        self._event_bus = get_event_bus()

        if self._event_bus:
            # Re-subscribe to CVE Hunter events for integration compatibility
            # These are used to populate the cache from the event stream
            self._event_bus.on("cve_hunter.cve.scanned")(self._handle_cve_scanned)
            self._event_bus.on("cve_hunter.integration.cve_lookup_response")(
                self._handle_lookup_response
            )
            logger.info("Subscribed to CVE Hunter integration events")

        self._initialized = True
        logger.info("Honeypot CVE Correlator initialized")

        # Load persisted correlations if memory available
        if self._memory:
            loaded = self._memory.get_cve_correlations()
            if loaded:
                self._correlations.extend(loaded)
                logger.info(f"Loaded {len(loaded)} persisted correlations")

        return True

    def set_memory(self, memory: Any) -> None:
        """Set memory manager.

        Args:
            memory: HoneypotMemory instance
        """
        self._memory = memory

    def set_cve_service(self, cve_service) -> None:
        """Set CVE service.

        Args:
            cve_service: CVE lookup service instance
        """
        self._cve_service = cve_service
        logger.info("CVE service wired into correlator")

    async def _handle_cve_scanned(self, data: Dict[str, Any]) -> None:
        """Handle CVE scanned event from CVE Hunter."""
        cve_id = data.get("cve_id")
        if cve_id:
            self._cve_cache[cve_id] = {
                "cve_id": cve_id,
                "severity": data.get("severity", "unknown"),
                "cwe_ids": data.get("cwe_ids", []),
                "source": "event_stream",
            }
            logger.debug(f"Cached CVE from event: {cve_id}")

    async def _handle_lookup_response(self, data: Dict[str, Any]) -> None:
        """Handle CVE lookup response from CVE Hunter."""
        matched_cves = data.get("matched_cves", [])
        for cve in matched_cves:
            cve_id = cve.get("cve_id")
            if cve_id:
                self._cve_cache[cve_id] = {
                    "cve_id": cve_id,
                    "severity": cve.get("severity", "unknown"),
                    "cwe_ids": data.get("request_cwes", []),
                    "source": "lookup_response",
                }
                logger.debug(f"Cached CVE from lookup: {cve_id}")

    async def correlate_attack(
        self,
        event_id: str,
        category: str,
        patterns: List[str],
        source_ip: str,
        honeypot_tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Correlate an attack with known CVEs.

        Args:
            event_id: Attack event ID
            category: Attack category
            patterns: Detected patterns
            source_ip: Attacker IP
            honeypot_tags: Optional tags from honeypot config (e.g. cve-2024-xxxx)

        Returns:
            Correlation result or None
        """
        if not self.config.enable_cve_correlation:
            return None

        # 1. Direct Tag Matching (Highest Priority)
        # If the honeypot is explicitly tagged with a CVE (e.g. "cve-2024-21762"),
        # we assume *any* successful attack on it is related to that CVE.
        tag_cves = []
        if honeypot_tags:
            import re

            for tag in honeypot_tags:
                # Match cve-YYYY-NNNN format
                if re.match(r"^cve-\d{4}-\d{4,}$", tag.lower()):
                    tag_cves.append(tag.upper())

        # 2. Category/Pattern Matching (Fallback)
        # Get CWEs for this attack category
        cwes = self._get_cwes_for_category(category)

        # Get MITRE ATT&CK Techniques
        mitre_techniques = set()
        for cwe in cwes:
            techniques = CWE_TO_MITRE.get(cwe, [])
            mitre_techniques.update(techniques)

        # 3. Look for matching cached CVEs
        matched_cves = []

        # First, include any explicitly tagged CVEs
        # If we don't have them in cache, we should request them, but we can still link them
        matched_cves.extend(tag_cves)

        # Then check cache for CWE matches
        for cve_id, cve_data in self._cve_cache.items():
            if cve_id in tag_cves:
                continue  # Already added

            cve_cwes = cve_data.get("cwe_ids", [])
            if any(cwe in cve_cwes for cwe in cwes):
                matched_cves.append(cve_id)

        # If we found tags but they aren't in cache, or if we have no matches at all
        if not matched_cves and not tag_cves:
            # 1. Try Dynamic Lookup (Autonomous)
            if self._cve_service and self.config.enable_dynamic_cve_lookup:
                await self._dynamic_cve_lookup(category, cwes)
                # Check cache again
                for cve_id, cve_data in self._cve_cache.items():
                    cve_cwes = cve_data.get("cwe_ids", [])
                    if any(cwe in cve_cwes for cwe in cwes):
                        matched_cves.append(cve_id)

            # 2. Try EventBus Lookup (Integration Fallback)
            if not matched_cves:
                await self._request_cve_lookup(category, cwes, patterns)

            return None

        # If we have tag CVEs that are NOT in cache, enrich them via CVE service
        if self._cve_service and self.config.enable_dynamic_cve_lookup:
            for cve in tag_cves:
                if cve not in self._cve_cache:
                    await self._enrich_cve_from_service(cve)
        else:
            # No enrichment without CVE service - use basic metadata
            for cve in tag_cves:
                if cve not in self._cve_cache:
                    self._cve_cache[cve] = {
                        "cve_id": cve,
                        "source": "tag_only",
                        "description": "CVE tagged in honeypot config",
                    }

        # Create correlation
        correlation_id = f"corr-{uuid4().hex[:8]}"
        correlation = {
            "correlation_id": correlation_id,
            "event_id": event_id,
            "category": category,
            "request_timestamp": datetime.now(timezone.utc).isoformat(),
            "matched_cves": matched_cves,
            "matched_cwes": cwes,
            "mitre_techniques": list(mitre_techniques),
            "confidence": self._calculate_confidence(
                matched_cves, patterns, cwes, bool(tag_cves)
            ),
            "source_ip": source_ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._correlations.append(correlation)

        # Emit correlation event
        await emit_honeypot_event(
            HoneypotEvents.CVE_CORRELATION_FOUND,
            CVECorrelationEventData(
                correlation_id=correlation_id,
                event_id=event_id,
                attack_pattern=category,
                matched_cves=matched_cves[:10],
                matched_cwes=cwes,
                confidence=correlation["confidence"],
            ).to_dict(),
        )

        logger.info(
            f"Correlation found: {correlation_id} -> {len(matched_cves)} CVEs (Tags: {tag_cves})"
        )

        # Persist correlation
        if self._memory:
            await self._memory.store_cve_correlation(correlation)

        return correlation

    def _get_cwes_for_category(self, category: str) -> List[str]:
        """Get CWE IDs for attack category."""
        category_cwe_map = {
            "sql_injection": ["CWE-89", "CWE-564"],
            "command_injection": ["CWE-78", "CWE-77"],
            "path_traversal": ["CWE-22", "CWE-23"],
            "xss": ["CWE-79", "CWE-80"],
            "brute_force": ["CWE-307", "CWE-521"],
            "reconnaissance": ["CWE-200"],
            "credential_harvesting": ["CWE-522", "CWE-523"],
            "malware_delivery": ["CWE-94", "CWE-829"],
            "exploit_attempt": [
                "CWE-94",
                "CWE-787",
                "CWE-119",
                "CWE-20",
            ],  # Generic exploit CWEs
        }
        return category_cwe_map.get(category, [])

    def _calculate_confidence(
        self,
        matched_cves: List[Dict[str, Any]],
        patterns: List[str],
        matched_cwes: List[str],
        has_explicit_tags: bool = False,
    ) -> float:
        """Calculate correlation confidence score."""
        base = 0.5
        cve_count = len(matched_cves)

        # explicit tags imply high confidence
        if has_explicit_tags:
            return 0.95

        # More CVE matches = higher confidence
        if cve_count >= 5:
            base += 0.3
        elif cve_count >= 2:
            base += 0.2
        elif cve_count >= 1:
            base += 0.1

        # More patterns = higher confidence
        if len(patterns) >= 3:
            base += 0.2
        elif len(patterns) >= 1:
            base += 0.1

        # CWE Specificity boost
        if "CWE-89" in matched_cwes or "CWE-78" in matched_cwes:
            base += 0.1  # High confidence signatures

        return min(base, 1.0)

    def get_correlations(
        self,
        limit: int = 50,
        min_confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Get recent correlations.

        Args:
            limit: Maximum results
            min_confidence: Minimum confidence threshold

        Returns:
            List of correlation records
        """
        filtered = [
            c for c in self._correlations if c.get("confidence", 0) >= min_confidence
        ]
        return filtered[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get correlation statistics."""
        return {
            "total_correlations": len(self._correlations),
            "cached_cves": len(self._cve_cache),
            "high_confidence": len(
                [c for c in self._correlations if c.get("confidence", 0) >= 0.7]
            ),
            "accuracy": self.get_accuracy_stats(),
        }
