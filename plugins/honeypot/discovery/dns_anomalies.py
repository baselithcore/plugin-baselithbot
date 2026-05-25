"""DNS Anomalies Engine.

Analyzes DNS traffic for malicious patterns such as DGA (Domain Generation Algorithms),
Fast Flux networks, and Tunneling/Beaconing behavior.
"""

from core.observability.logging import get_logger
import math
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List

# Optional: Import tldextract if available for better domain parsing
try:
    import tldextract
except ImportError:
    tldextract = None

logger = get_logger(__name__)


@dataclass
class DNSAnomalies:
    """Detected DNS anomalies."""

    is_dga: bool = False
    is_fast_flux: bool = False
    is_nxdomain_burst: bool = False
    entropy: float = 0.0
    bigram_score: float = 0.0
    ttl_variance: float = 0.0
    confidence: float = 0.0
    tags: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_dga": self.is_dga,
            "is_fast_flux": self.is_fast_flux,
            "is_nxdomain_burst": self.is_nxdomain_burst,
            "entropy": round(self.entropy, 3),
            "confidence": round(self.confidence, 3),
            "tags": self.tags or [],
        }


class DNSAnomaliesEngine:
    """Core engine for DNS anomaly detection."""

    # DGA Constants
    ENTROPY_THRESHOLD = 3.8
    BIGRAM_THRESHOLD = 0.4  # Lower is more random/rare

    # Fast Flux Constants
    MIN_IP_DIVERSITY = 3  # Min IPs resolved for a domain to even check
    FAST_FLUX_TTL_THRESHOLD = 300  # Seconds (Low TTL)

    # NXDOMAIN Constants
    NXDOMAIN_WINDOW_SEC = 60
    NXDOMAIN_BURST_THRESHOLD = 10

    def __init__(self):
        self._history: Dict[str, List[Any]] = defaultdict(list)
        self._nxdomain_counters: Dict[str, List[float]] = defaultdict(list)

        # Load English bigram stats (simplified) if needed,
        # or use simple vowel/consonant ratio for randomness.

    def analyze_query(
        self,
        domain: str,
        record_type: str = "A",
        resolved_ips: List[str] = None,
        ttl: int = None,
        is_nxdomain: bool = False,
        source_ip: str = "",
    ) -> DNSAnomalies:
        """
        Analyze a single DNS query/response.

        Args:
            domain: The queried domain name
            record_type: DNS record type (A, AAAA, MX, etc.)
            resolved_ips: List of IPs returned (if any)
            ttl: Time To Live of the record
            is_nxdomain: True if response was NXDOMAIN
            source_ip: Requestor IP (for NXDOMAIN rate limiting)

        Returns:
            DNSAnomalies object
        """
        anomalies = DNSAnomalies(tags=[])

        # 1. DGA Analysis (Entropy & Structure)
        # Strip TLD for analysis if possible
        effective_domain = self._get_effective_domain(domain)

        entropy = self._calculate_shannon_entropy(effective_domain)
        anomalies.entropy = entropy

        # Simple heuristic: High entropy + length > 10 usually DGA
        if entropy > self.ENTROPY_THRESHOLD and len(effective_domain) > 10:
            anomalies.is_dga = True
            anomalies.tags.append("dga_entropy")
            anomalies.confidence += 0.6

        # 2. Fast Flux Analysis
        if resolved_ips and len(resolved_ips) >= self.MIN_IP_DIVERSITY:
            if ttl is not None and ttl < self.FAST_FLUX_TTL_THRESHOLD:
                anomalies.is_fast_flux = True
                anomalies.tags.append("fast_flux")
                anomalies.confidence += 0.5

        # 3. NXDOMAIN Burst Analysis (Botnet Beaconing)
        if is_nxdomain and source_ip:
            is_burst = self._check_nxdomain_burst(source_ip)
            if is_burst:
                anomalies.is_nxdomain_burst = True
                anomalies.tags.append("nxdomain_burst")
                anomalies.confidence += 0.4

        return anomalies

    def _get_effective_domain(self, domain: str) -> str:
        """Extract the main part of the domain (SLD)."""
        if not domain:
            return ""

        # Remove trailing dot
        domain = domain.rstrip(".")

        if tldextract:
            extracted = tldextract.extract(domain)
            return extracted.domain

        # Fallback: simple split
        parts = domain.split(".")
        if len(parts) >= 2:
            return parts[-2]  # Better fallback (SLD)
        return domain

    def _calculate_shannon_entropy(self, data: str) -> float:
        """Calculate Shannon entropy."""
        if not data:
            return 0.0

        entropy = 0.0
        length = len(data)
        freq = {}
        for char in data:
            freq[char] = freq.get(char, 0) + 1

        for count in freq.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy

    def _check_nxdomain_burst(self, source_ip: str) -> bool:
        """Check if source_ip has exceeded NXDOMAIN burst threshold."""
        now = time.time()
        timestamps = self._nxdomain_counters[source_ip]

        # Clean old timestamps
        timestamps = [t for t in timestamps if now - t < self.NXDOMAIN_WINDOW_SEC]
        timestamps.append(now)
        self._nxdomain_counters[source_ip] = timestamps

        return len(timestamps) > self.NXDOMAIN_BURST_THRESHOLD
