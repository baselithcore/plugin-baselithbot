"""CVE Correlator Agent.

Agent responsible for correlating CVEs to detect attack chains,
common vulnerability patterns, and inter-related security issues.

Uses LLM for semantic analysis and graph-based correlation.
"""

from core.observability.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import NAMESPACE_DNS, uuid5

from core.di import ServiceRegistry
from core.interfaces import LLMServiceProtocol

try:
    from ..config import CVEHunterConfig, get_cve_hunter_config
    from ..models import CVERecord
except ImportError:
    from config import CVEHunterConfig, get_cve_hunter_config  # type: ignore[no-redef]
    from models import CVERecord  # type: ignore[no-redef]


logger = get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class CorrelationMatch:
    """Represents a correlation between CVEs."""

    correlation_id: str
    cve_ids: List[str]
    correlation_type: str  # attack_chain, common_cwe, same_product, etc.
    confidence: float
    description: str
    severity: str = "medium"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "correlation_id": self.correlation_id,
            "cve_ids": self.cve_ids,
            "correlation_type": self.correlation_type,
            "confidence": self.confidence,
            "description": self.description,
            "severity": self.severity,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AttackChain:
    """Represents a detected attack chain."""

    chain_id: str
    name: str
    stages: List[Dict[str, Any]]  # List of CVEs with stage info
    total_severity: float
    description: str
    cve_ids: List[str] = field(default_factory=list)
    ai_analysis: Optional[str] = None
    mitre_techniques: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Correlator Agent
# =============================================================================


class CVECorrelatorAgent:
    """Agent for correlating CVEs and detecting attack patterns.

    Uses multiple correlation strategies:
    - CWE-based: CVEs sharing common weakness enumerations
    - Product-based: CVEs affecting the same product/vendor
    - Temporal: CVEs disclosed in close time proximity
    - Attack chain: CVEs that can be chained for escalation

    Example:
        ```python
        correlator = CVECorrelatorAgent()
        correlations = await correlator.find_correlations(cve_list)
        chains = await correlator.detect_attack_chains(cve_list)
        ```
    """

    name = "cve-correlator"

    # Common attack chain patterns
    ATTACK_CHAIN_PATTERNS = [
        {
            "name": "Initial Access → Privilege Escalation",
            "cwes": [["CWE-287", "CWE-306"], ["CWE-269", "CWE-264"]],
            "techniques": ["T1190", "T1068"],
        },
        {
            "name": "RCE → Persistence",
            "cwes": [["CWE-78", "CWE-94"], ["CWE-502", "CWE-912"]],
            "techniques": ["T1059", "T1136"],
        },
        {
            "name": "SQLi → Data Exfiltration",
            "cwes": [["CWE-89"], ["CWE-200", "CWE-538"]],
            "techniques": ["T1190", "T1005"],
        },
    ]

    def __init__(
        self,
        config: Optional[CVEHunterConfig] = None,
        llm_service: Optional[LLMServiceProtocol] = None,
    ):
        """Initialize correlator agent.

        Args:
            config: CVE Hunter configuration
            llm_service: LLM service for semantic analysis
        """
        self.config = config or get_cve_hunter_config()
        self._llm_service = llm_service
        self._correlation_cache: Dict[str, CorrelationMatch] = {}

    async def _get_llm(self) -> LLMServiceProtocol:
        """Get LLM service from DI container."""
        if self._llm_service is None:
            self._llm_service = ServiceRegistry.get(LLMServiceProtocol)
        return self._llm_service

    # =========================================================================
    # Main Correlation Methods
    # =========================================================================

    async def find_correlations(
        self,
        cves: List[CVERecord],
        min_confidence: float = 0.6,
    ) -> List[CorrelationMatch]:
        """Find correlations between CVEs.

        Args:
            cves: List of CVE records to correlate
            min_confidence: Minimum confidence threshold

        Returns:
            List of correlation matches
        """
        correlations: List[CorrelationMatch] = []

        if len(cves) < 2:
            return correlations

        # CWE-based correlations
        cwe_correlations = self._find_cwe_correlations(cves)
        correlations.extend(cwe_correlations)

        # Product-based correlations
        product_correlations = self._find_product_correlations(cves)
        correlations.extend(product_correlations)

        # Filter by confidence
        correlations = [c for c in correlations if c.confidence >= min_confidence]

        logger.info(f"Found {len(correlations)} correlations among {len(cves)} CVEs")
        return correlations

    async def detect_attack_chains(
        self,
        cves: List[CVERecord],
    ) -> List[AttackChain]:
        """Detect potential attack chains in CVE set.

        Args:
            cves: List of CVE records

        Returns:
            List of detected attack chains
        """
        chains: List[AttackChain] = []

        if len(cves) < 2:
            return chains

        # Build CWE lookup
        cwe_to_cves: Dict[str, List[CVERecord]] = {}
        for cve in cves:
            for cwe in cve.cwe_ids:
                if cwe not in cwe_to_cves:
                    cwe_to_cves[cwe] = []
                cwe_to_cves[cwe].append(cve)

        # Check each pattern
        for pattern in self.ATTACK_CHAIN_PATTERNS:
            chain_cves = self._match_chain_pattern(pattern, cwe_to_cves)
            if chain_cves:
                # Generate deterministic ID based on content
                cve_ids_str = ",".join(sorted(c.cve_id for c in chain_cves))
                chain_content = f"{pattern['name']}:{cve_ids_str}"
                stable_id = str(uuid5(NAMESPACE_DNS, chain_content))

                chain = AttackChain(
                    chain_id=stable_id,
                    name=pattern["name"],
                    stages=[
                        {"stage": i + 1, "cve_id": cve.cve_id, "cwe": cve.cwe_ids}
                        for i, cve in enumerate(chain_cves)
                    ],
                    # Use Max CVE severity for the chain score to keep 0-10 scale
                    total_severity=max(cve.cvss_score for cve in chain_cves),
                    description=f"Detected {pattern['name']} chain with {len(chain_cves)} CVEs",
                    mitre_techniques=pattern.get("techniques", []),
                    cve_ids=[c.cve_id for c in chain_cves],
                )
                chains.append(chain)

        logger.info(f"Detected {len(chains)} attack chains")
        return chains

    async def semantic_correlation(
        self,
        cve1: CVERecord,
        cve2: CVERecord,
    ) -> Optional[CorrelationMatch]:
        """Use LLM to find semantic correlations.

        Args:
            cve1: First CVE
            cve2: Second CVE

        Returns:
            CorrelationMatch if found, None otherwise
        """
        try:
            llm = await self._get_llm()

            prompt = f"""Analyze these two CVEs for potential correlation:

CVE 1: {cve1.cve_id}
Description: {cve1.description}
CWEs: {", ".join(cve1.cwe_ids)}

CVE 2: {cve2.cve_id}
Description: {cve2.description}
CWEs: {", ".join(cve2.cwe_ids)}

Are these CVEs related? If yes, explain how (attack chain, same root cause, etc.).
Rate correlation confidence from 0.0 to 1.0.
Response format: CORRELATED: [yes/no], CONFIDENCE: [0.0-1.0], TYPE: [type], REASON: [explanation]"""

            response = await llm.generate_response(prompt=prompt)

            # Parse response
            if "CORRELATED: yes" in response.lower():
                confidence = self._extract_confidence(response)
                corr_type = self._extract_type(response)

                stable_id = str(
                    uuid5(
                        NAMESPACE_DNS,
                        f"semantic|{corr_type}|{','.join(sorted([cve1.cve_id, cve2.cve_id]))}",
                    )
                )

                return CorrelationMatch(
                    correlation_id=stable_id,
                    cve_ids=[cve1.cve_id, cve2.cve_id],
                    correlation_type=corr_type,
                    confidence=confidence,
                    description=response,
                )

        except Exception as e:
            logger.warning(f"Semantic correlation failed: {e}")

        return None

    # =========================================================================
    # Correlation Strategies
    # =========================================================================

    def _find_cwe_correlations(self, cves: List[CVERecord]) -> List[CorrelationMatch]:
        """Find CVEs with common CWEs."""
        correlations = []
        cwe_groups: Dict[str, List[str]] = {}

        for cve in cves:
            # Ensure cwe_ids is a list
            cwe_ids = cve.cwe_ids if isinstance(cve.cwe_ids, list) else []
            for cwe in cwe_ids:
                if cwe not in cwe_groups:
                    cwe_groups[cwe] = []
                # Avoid duplicates
                if cve.cve_id not in cwe_groups[cwe]:
                    cwe_groups[cwe].append(cve.cve_id)

        for cwe, cve_ids in cwe_groups.items():
            if len(cve_ids) >= 2:
                # Deterministic ID based on sorted CVEs
                sorted_cve_ids = sorted(cve_ids)
                stable_id = str(
                    uuid5(
                        NAMESPACE_DNS,
                        f"common_cwe|{cwe}|{','.join(sorted_cve_ids)}",
                    )
                )

                # Check if we already have this correlation
                if stable_id in self._correlation_cache:
                    correlations.append(self._correlation_cache[stable_id])
                    continue

                correlation = CorrelationMatch(
                    correlation_id=stable_id,
                    cve_ids=sorted_cve_ids,
                    correlation_type="common_cwe",
                    confidence=0.7 + (0.05 * min(len(cve_ids), 5)),
                    description=f"CVEs share common weakness: {cwe}",
                    metadata={"cwe": cwe},
                )
                self._correlation_cache[stable_id] = correlation
                correlations.append(correlation)

        return correlations

    def _find_product_correlations(
        self, cves: List[CVERecord]
    ) -> List[CorrelationMatch]:
        """Find CVEs affecting same product."""
        correlations = []
        product_groups: Dict[str, List[str]] = {}

        for cve in cves:
            products = (
                cve.affected_products if isinstance(cve.affected_products, list) else []
            )
            for product in products:
                key = f"{product.vendor}:{product.product}"
                if key not in product_groups:
                    product_groups[key] = []
                if cve.cve_id not in product_groups[key]:
                    product_groups[key].append(cve.cve_id)

        for product, cve_ids in product_groups.items():
            if len(cve_ids) >= 2:
                sorted_cve_ids = sorted(cve_ids)
                stable_id = str(
                    uuid5(
                        NAMESPACE_DNS,
                        f"same_product|{product}|{','.join(sorted_cve_ids)}",
                    )
                )

                if stable_id in self._correlation_cache:
                    correlations.append(self._correlation_cache[stable_id])
                    continue

                correlation = CorrelationMatch(
                    correlation_id=stable_id,
                    cve_ids=sorted_cve_ids,
                    correlation_type="same_product",
                    confidence=0.8,
                    description=f"CVEs affect same product: {product}",
                    metadata={"product": product},
                )
                self._correlation_cache[stable_id] = correlation
                correlations.append(correlation)

        return correlations

    def _match_chain_pattern(
        self,
        pattern: Dict[str, Any],
        cwe_to_cves: Dict[str, List[CVERecord]],
    ) -> List[CVERecord]:
        """Match attack chain pattern against CVE set."""
        chain: List[CVERecord] = []

        for stage_cwes in pattern["cwes"]:
            stage_cve = None
            for cwe in stage_cwes:
                if cwe in cwe_to_cves and cwe_to_cves[cwe]:
                    # Pick highest severity CVE for this stage
                    candidates = [c for c in cwe_to_cves[cwe] if c not in chain]
                    if candidates:
                        stage_cve = max(candidates, key=lambda c: c.cvss_score)
                        break

            if stage_cve:
                chain.append(stage_cve)
            else:
                return []  # Chain incomplete

        return chain if len(chain) == len(pattern["cwes"]) else []

    # =========================================================================
    # Helpers
    # =========================================================================

    def _extract_confidence(self, response: str) -> float:
        """Extract confidence from LLM response."""
        import re

        match = re.search(r"CONFIDENCE:\s*([0-9.]+)", response, re.IGNORECASE)
        if match:
            try:
                return min(1.0, max(0.0, float(match.group(1))))
            except ValueError:
                pass
        return 0.5

    def _extract_type(self, response: str) -> str:
        """Extract correlation type from LLM response."""
        import re

        match = re.search(r"TYPE:\s*(\w+)", response, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return "semantic"
