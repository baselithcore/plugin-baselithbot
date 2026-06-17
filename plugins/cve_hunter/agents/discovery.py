"""CVE Discovery Agent.

Agent responsible for detecting potential new vulnerabilities
through pattern analysis and anomaly detection.

Enhanced with:
- Memory for storing successful discovery patterns
- Event emission for cross-agent coordination

Online scanning logic is extracted to _online.py to keep this file
under the 500 LOC cap.
"""

from core.observability.logging import get_logger
import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

from core.context import (
    get_current_tenant_id,
    reset_tenant_context,
    set_tenant_context,
)
from core.di import ServiceRegistry
from core.interfaces import LLMServiceProtocol

try:
    from ..config import CVEHunterConfig, get_cve_hunter_config
    from ..events import (
        CVEHunterEvents,
        DiscoveryEventData,
        LearningEventData,
        emit_cve_event,
    )
    from ..memory import CVEHunterMemory, get_cve_hunter_memory
    from ..models import (
        CVERecord,
        CVESource,
        VulnerabilityAlert,
    )
    from ..utils.patterns import (
        VULNERABILITY_PATTERNS,
        extract_context,
        is_code_file,
        pattern_to_cwe,
        pattern_to_severity,
    )
    from ._online import scan_online_sources as _scan_online_sources
except ImportError:
    from config import CVEHunterConfig, get_cve_hunter_config  # type: ignore[no-redef]
    from events import (  # type: ignore[no-redef]
        CVEHunterEvents,
        DiscoveryEventData,
        LearningEventData,
        emit_cve_event,
    )
    from memory import CVEHunterMemory, get_cve_hunter_memory  # type: ignore[no-redef]
    from models import CVERecord, CVESource, VulnerabilityAlert  # type: ignore[no-redef]
    from utils.patterns import (  # type: ignore[no-redef]
        VULNERABILITY_PATTERNS,
        extract_context,
        is_code_file,
        pattern_to_cwe,
        pattern_to_severity,
    )
    from _online import scan_online_sources as _scan_online_sources  # type: ignore[no-redef]

logger = get_logger(__name__)


class CVEDiscoveryAgent:
    """Agent for discovering potential new vulnerabilities.

    Uses pattern detection and anomaly analysis to identify
    potential zero-day vulnerabilities or unreported issues.

    Example:
        ```python
        agent = CVEDiscoveryAgent()
        alerts = await agent.analyze_text_for_vulnerabilities(text_content)
        ```
    """

    name = "cve-discovery"

    def __init__(
        self,
        config: Optional[CVEHunterConfig] = None,
        llm_service: Optional[LLMServiceProtocol] = None,
        memory: Optional[CVEHunterMemory] = None,
    ):
        """Initialize discovery agent.

        Args:
            config: CVE Hunter configuration
            llm_service: LLM service for AI analysis
            memory: Optional CVEHunterMemory for pattern persistence
        """
        self.config = config or get_cve_hunter_config()
        self._llm_service = llm_service
        self._memory = memory
        self._discovered_hashes: set[str] = set()
        self._memory_initialized = False

    async def _get_llm(self) -> LLMServiceProtocol:
        """Get LLM service from DI container."""
        if self._llm_service is None:
            service_or_factory = ServiceRegistry.get(LLMServiceProtocol)

            if asyncio.iscoroutinefunction(service_or_factory) or (
                callable(service_or_factory)
                and not isinstance(service_or_factory, type)
            ):
                if asyncio.iscoroutinefunction(service_or_factory):
                    self._llm_service = await service_or_factory()
                else:
                    result = service_or_factory()
                    if asyncio.iscoroutine(result):
                        self._llm_service = await result
                    else:
                        self._llm_service = result
            else:
                self._llm_service = service_or_factory

        return self._llm_service

    def _get_memory(self) -> Optional[CVEHunterMemory]:
        """Lazy-load memory system."""
        if self._memory is None and not self._memory_initialized:
            self._memory_initialized = True
            if self.config.enable_memory:
                try:
                    self._memory = get_cve_hunter_memory()
                    logger.debug("Discovery agent connected to memory system")
                except Exception as e:
                    logger.debug(f"Memory not available: {e}")
        return self._memory

    async def analyze_text_for_vulnerabilities(
        self,
        text: str,
        source: str = "unknown",
    ) -> List[Dict[str, Any]]:
        """Analyze text content for potential vulnerabilities.

        Args:
            text: Text content to analyze
            source: Source of the text

        Returns:
            List of potential vulnerability findings
        """
        findings: List[Dict[str, Any]] = []
        text_lower = text.lower()

        for pattern in VULNERABILITY_PATTERNS:
            if pattern in text_lower:
                findings.append(
                    {
                        "pattern": pattern,
                        "source": source,
                        "confidence": 0.5,
                        "context": extract_context(text, pattern),
                    }
                )

        if findings and self.config.enable_discovery:
            findings = await self._llm_analyze_findings(findings, text)

        if findings and self.config.enable_memory:
            findings = await self._apply_memory_bias(findings)

        return findings

    async def _llm_analyze_findings(
        self,
        findings: List[Dict[str, Any]],
        original_text: str,
    ) -> List[Dict[str, Any]]:
        """Use LLM to analyze and refine findings."""
        try:
            llm = await self._get_llm()

            patterns_found = ", ".join(f["pattern"] for f in findings)
            prompt = f"""Analyze this text for genuine security vulnerabilities.

Patterns detected: {patterns_found}

Text excerpt:
{original_text[:1500]}

For each pattern found, determine:
1. Is this a genuine security concern or false positive?
2. Confidence level (0.0-1.0)
3. Potential CVE-worthiness
4. Brief description of the issue

Respond with JSON format:
{{"findings": [{{"pattern": "...", "is_genuine": true/false, "confidence": 0.X, "description": "..."}}]}}
"""

            full_prompt = (
                "System: You are a security researcher analyzing potential "
                f"vulnerabilities.\n\nUser: {prompt}"
            )

            try:
                inherited = get_current_tenant_id()
            except Exception:
                inherited = None
            tenant_id = (
                getattr(self.config, "tenant_id", None) or inherited or "default"
            )
            _token = set_tenant_context(tenant_id)
            try:
                response = await llm.generate_response(prompt=full_prompt)
            finally:
                reset_tenant_context(_token)

            for finding in findings:
                if finding["pattern"] in response.lower():
                    finding["confidence"] = min(0.85, finding["confidence"] + 0.2)
                    finding["llm_analyzed"] = True

        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")

        return findings

    async def _apply_memory_bias(
        self,
        findings: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Adjust findings confidence based on past success/false positives."""
        memory = self._get_memory()
        if not memory:
            return findings

        try:
            successful = await memory.get_successful_patterns(limit=50)
            false_positives = await memory.get_false_positive_patterns(limit=50)

            success_set = {p["pattern"].lower() for p in successful if p.get("pattern")}
            false_set = {
                p["pattern"].lower() for p in false_positives if p.get("pattern")
            }

            for finding in findings:
                pattern = finding.get("pattern", "").lower()
                confidence = float(finding.get("confidence", 0.0))
                if pattern in success_set:
                    confidence = min(1.0, confidence + 0.15)
                    finding["memory_boosted"] = True
                if pattern in false_set:
                    confidence = max(0.0, confidence - 0.2)
                    finding["memory_penalized"] = True
                finding["confidence"] = confidence
        except Exception as e:
            logger.debug(f"Memory bias failed: {e}")

        return findings

    async def generate_discovery_alert(
        self,
        finding: Dict[str, Any],
    ) -> Optional[VulnerabilityAlert]:
        """Generate an alert from a discovery finding.

        Args:
            finding: Discovery finding dict

        Returns:
            VulnerabilityAlert if confidence threshold met
        """
        if finding.get("confidence", 0) < self.config.discovery_confidence_threshold:
            return None

        cve_record = CVERecord(
            cve_id=f"DISCOVERED-{uuid4().hex[:8].upper()}",
            title=f"Potential {finding['pattern'].title()} Vulnerability",
            description=finding.get("context", "Discovered through pattern analysis"),
            severity=pattern_to_severity(finding["pattern"]),
            source=CVESource.DISCOVERED,
            published_date=datetime.now(timezone.utc),
        )

        return VulnerabilityAlert(
            alert_id=str(uuid4()),
            cve=cve_record,
            alert_type="potential_0day",
            priority=2,
            created_at=datetime.now(timezone.utc),
        )

    async def scan_code_repository(
        self,
        repo_content: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Scan code repository content for vulnerabilities.

        Args:
            repo_content: Dict mapping file paths to content

        Returns:
            List of findings
        """
        all_findings: List[Dict[str, Any]] = []

        for file_path, content in repo_content.items():
            if not is_code_file(file_path):
                continue

            findings = await self.analyze_text_for_vulnerabilities(
                content, source=file_path
            )
            all_findings.extend(findings)

        return all_findings

    async def correlate_with_known_cves(
        self,
        finding: Dict[str, Any],
        known_cves: List[CVERecord],
    ) -> List[CVERecord]:
        """Find known CVEs related to a finding.

        Args:
            finding: Discovery finding
            known_cves: List of known CVE records

        Returns:
            Related CVE records
        """
        pattern = finding.get("pattern", "").lower()
        related: List[CVERecord] = []

        for cve in known_cves:
            if pattern in cve.description.lower():
                related.append(cve)
            cwe_patterns = pattern_to_cwe(pattern)
            if any(cwe in cve.cwe_ids for cwe in cwe_patterns):
                if cve not in related:
                    related.append(cve)

        return related

    async def scan_online_sources(self) -> AsyncIterator[Dict[str, Any]]:
        """Scan online security news sources for potential zero-days.

        Yields:
            Discovery log events and findings
        """
        async for event in _scan_online_sources(self.analyze_text_for_vulnerabilities):
            yield event

    # =========================================================================
    # Event & Memory Helpers
    # =========================================================================

    async def _emit_discovery_event(
        self,
        discovery_id: str,
        pattern: str,
        confidence: float,
        source: str,
        finding_type: str = "potential",
    ) -> None:
        """Emit a discovery event for coordination.

        Args:
            discovery_id: Unique identifier for the discovery
            pattern: Vulnerability pattern detected
            confidence: Confidence score (0.0-1.0)
            source: Source of the discovery
            finding_type: Type of finding (potential, confirmed, false_positive)
        """
        try:
            event_data = DiscoveryEventData(
                discovery_id=discovery_id,
                pattern=pattern,
                confidence=confidence,
                source=source,
                finding_type=finding_type,
            )
            event_name = (
                CVEHunterEvents.DISCOVERY_CONFIRMED
                if finding_type == "confirmed"
                else (
                    CVEHunterEvents.DISCOVERY_FALSE_POSITIVE
                    if finding_type == "false_positive"
                    else CVEHunterEvents.DISCOVERY_POTENTIAL
                )
            )
            await emit_cve_event(event_name, event_data.to_dict())
        except Exception as e:
            logger.debug(f"Failed to emit discovery event: {e}")

    async def _record_discovery_pattern(
        self,
        pattern: str,
        confidence: float,
        source: str,
        was_successful: bool,
        context: Optional[str] = None,
    ) -> None:
        """Record a discovery pattern in memory for learning.

        Args:
            pattern: The vulnerability pattern
            confidence: Confidence score
            source: Source of the discovery
            was_successful: Whether it led to a valid discovery
            context: Additional context
        """
        memory = self._get_memory()
        if memory:
            try:
                await memory.remember_discovery_pattern(
                    pattern=pattern,
                    confidence=confidence,
                    source=source,
                    was_successful=was_successful,
                    context=context,
                )

                event_data = LearningEventData(
                    experience_id=str(uuid4()),
                    action="discover",
                    reward=1.0 if was_successful else -0.3,
                    success=was_successful,
                    pattern_type=pattern,
                )
                await emit_cve_event(
                    CVEHunterEvents.EXPERIENCE_RECORDED,
                    event_data.to_dict(),
                )
            except Exception as e:
                logger.debug(f"Failed to record discovery pattern: {e}")
