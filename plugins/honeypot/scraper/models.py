"""Data models for OSINT enrichment results.

Defines immutable dataclasses for IP reputation, domain intelligence,
URL analysis, and aggregated enrichment results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ThreatLevel(str, Enum):
    """Threat level classification."""

    UNKNOWN = "unknown"
    CLEAN = "clean"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MalwareType(str, Enum):
    """Malware type classification."""

    UNKNOWN = "unknown"
    BOTNET = "botnet"
    RANSOMWARE = "ransomware"
    TROJAN = "trojan"
    MINER = "miner"
    DROPPER = "dropper"
    RAT = "rat"
    STEALER = "stealer"
    LOADER = "loader"
    OTHER = "other"


@dataclass
class IPReputation:
    """IP address reputation data from OSINT sources."""

    ip: str
    threat_level: ThreatLevel = ThreatLevel.UNKNOWN
    abuse_score: float = 0.0  # 0-100
    is_known_attacker: bool = False
    is_tor_exit: bool = False
    is_vpn: bool = False
    is_proxy: bool = False
    is_datacenter: bool = False
    tags: List[str] = field(default_factory=list)
    reports_count: int = 0
    last_reported: Optional[datetime] = None
    country: Optional[str] = None
    asn: Optional[str] = None
    org: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)

    @property
    def is_suspicious(self) -> bool:
        """Check if IP is suspicious based on combined signals."""
        return (
            self.abuse_score >= 25
            or self.is_known_attacker
            or self.threat_level
            in (ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL)
        )


@dataclass
class DomainIntel:
    """Domain intelligence data from OSINT sources."""

    domain: str
    threat_level: ThreatLevel = ThreatLevel.UNKNOWN
    is_malicious: bool = False
    is_dga: bool = False
    is_newly_registered: bool = False
    registration_date: Optional[datetime] = None
    registrar: Optional[str] = None
    associated_ips: List[str] = field(default_factory=list)
    malware_families: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)


@dataclass
class URLAnalysis:
    """URL analysis data from OSINT sources."""

    url: str
    threat_level: ThreatLevel = ThreatLevel.UNKNOWN
    is_malicious: bool = False
    malware_type: MalwareType = MalwareType.UNKNOWN
    malware_family: Optional[str] = None
    payload_sha256: Optional[str] = None
    payload_md5: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    reporter: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)


@dataclass
class EnrichmentResult:
    """Aggregated enrichment result from all OSINT sources."""

    # Enriched data
    ip_reputations: Dict[str, IPReputation] = field(default_factory=dict)
    domain_intel: Dict[str, DomainIntel] = field(default_factory=dict)
    url_analyses: Dict[str, URLAnalysis] = field(default_factory=dict)

    # Statistics
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    cache_hits: int = 0

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        """Calculate enrichment duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def high_risk_ips(self) -> List[str]:
        """Get list of high-risk IPs."""
        return [
            ip
            for ip, rep in self.ip_reputations.items()
            if rep.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
        ]

    @property
    def malicious_urls(self) -> List[str]:
        """Get list of confirmed malicious URLs."""
        return [
            url for url, analysis in self.url_analyses.items() if analysis.is_malicious
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "ip_reputations": {
                ip: {
                    "threat_level": rep.threat_level.value,
                    "abuse_score": rep.abuse_score,
                    "is_known_attacker": rep.is_known_attacker,
                    "tags": rep.tags,
                    "country": rep.country,
                }
                for ip, rep in self.ip_reputations.items()
            },
            "domain_intel": {
                domain: {
                    "threat_level": intel.threat_level.value,
                    "is_malicious": intel.is_malicious,
                    "malware_families": intel.malware_families,
                }
                for domain, intel in self.domain_intel.items()
            },
            "url_analyses": {
                url: {
                    "threat_level": analysis.threat_level.value,
                    "is_malicious": analysis.is_malicious,
                    "malware_type": analysis.malware_type.value,
                    "malware_family": analysis.malware_family,
                }
                for url, analysis in self.url_analyses.items()
            },
            "statistics": {
                "total_queries": self.total_queries,
                "successful_queries": self.successful_queries,
                "failed_queries": self.failed_queries,
                "cache_hits": self.cache_hits,
                "duration_seconds": self.duration_seconds,
            },
            "high_risk_ips": self.high_risk_ips,
            "malicious_urls": self.malicious_urls,
        }
