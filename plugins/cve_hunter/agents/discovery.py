"""CVE Discovery Agent.

Agent responsible for detecting potential new vulnerabilities
through pattern analysis and anomaly detection.

Enhanced with:
- Memory for storing successful discovery patterns
- Event emission for cross-agent coordination
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

# Support both relative imports (when installed) and absolute imports
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

            # Handle lazy loading factory
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

        # Pattern matching
        for pattern in VULNERABILITY_PATTERNS:
            if pattern in text_lower:
                findings.append(
                    {
                        "pattern": pattern,
                        "source": source,
                        "confidence": 0.5,  # Base confidence
                        "context": extract_context(text, pattern),
                    }
                )

        # If patterns found, use LLM for deeper analysis
        if findings and self.config.enable_discovery:
            findings = await self._llm_analyze_findings(findings, text)

        # Apply memory bias to reduce false positives and boost proven patterns
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

            full_prompt = f"System: You are a security researcher analyzing potential vulnerabilities.\n\nUser: {prompt}"

            # Background tasks may run outside any HTTP request, so we
            # ensure a tenant context is established before the LLM call;
            # without it `strict_tenant_isolation=True` raises in core.
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

            # Update confidence based on LLM analysis
            # In production, parse JSON response properly
            for finding in findings:
                # Simple confidence boost if LLM confirms
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

        # Create a placeholder CVE record for discovered issue
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
            priority=2,  # High priority for discoveries
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
            # Skip non-code files
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
            # Check if pattern appears in CVE
            if pattern in cve.description.lower():
                related.append(cve)
            # Check CWE correlation
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
        # Sources to scan (RSS/JSON feeds)
        sources = [
            # Real feeds would go here - using reliable public ones or simulation
            {
                "name": "Hacker News",
                "url": "https://feeds.feedburner.com/TheHackersNews",
                "type": "rss",
            },
            {
                "name": "Exploit-DB",
                "url": "https://www.exploit-db.com/rss.xml",
                "type": "rss",
            },
            {
                "name": "Reddit NetSec",
                "url": "https://www.reddit.com/r/netsec/.json",
                "type": "json",
            },
            {
                "name": "Full Disclosure",
                "url": "http://seclists.org/rss/fulldisclosure.rss",
                "type": "rss",
            },
        ]

        import httpx
        import defusedxml.ElementTree as ET

        async with httpx.AsyncClient(timeout=10.0) as client:
            for source in sources:
                yield {
                    "type": "log",
                    "message": f"DISCOVERY: Connecting to {source['name']}...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                try:
                    # Simulate processing time for "hacking" effect
                    import asyncio

                    await asyncio.sleep(1.0)

                    response = await client.get(source["url"])
                    content = response.text

                    yield {
                        "type": "log",
                        "message": f"DISCOVERY: Processing {len(content)} bytes from {source['name']}...",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    # Basic content extraction
                    items = []
                    if source["type"] == "json":
                        data = response.json()
                        if "data" in data and "children" in data["data"]:
                            for child in data["data"]["children"][:5]:
                                items.append(child["data"].get("title", ""))
                                items.append(child["data"].get("selftext", ""))
                    else:
                        # Simple RSS XML parsing
                        try:
                            root = ET.fromstring(content)
                            for item in root.findall(".//item")[:5]:
                                title = item.find("title")
                                desc = item.find("description")
                                if title is not None:
                                    items.append(title.text)
                                if desc is not None:
                                    items.append(desc.text)
                        except Exception:
                            pass  # nosec B110

                    # Analyze items
                    for item_text in items:
                        if not item_text:
                            continue

                        yield {
                            "type": "log",
                            "message": f"DISCOVERY: Inspecting item '{item_text[:30]}...'...",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }

                        findings = await self.analyze_text_for_vulnerabilities(
                            item_text, source=source["name"]
                        )

                        for finding in findings:
                            yield {
                                "type": "finding",
                                "data": finding,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }

                except Exception as e:
                    yield {
                        "type": "error",
                        "message": f"DISCOVERY: Failed to scan {source['name']}: {str(e)}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

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

                # Emit learning event
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
