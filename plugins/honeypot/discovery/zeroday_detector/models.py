"""Zero-Day Detector Models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class ZeroDayCandidate:
    """Represents a potential zero-day exploit candidate."""

    id: str
    payload_hash: str
    payload_preview: str
    source_ips: List[str]
    target_services: List[str]
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
    novelty_score: float  # 0-1, higher = more novel
    severity_estimate: str  # low/medium/high/critical
    attack_vector: str  # e.g., "sql_injection", "rce", "buffer_overflow"
    confidence: float  # 0-1
    matched_cves: List[str]  # Empty if truly novel
    indicators: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "payload_hash": self.payload_hash,
            "payload_preview": self.payload_preview[:200],
            "source_ips": self.source_ips[:10],
            "target_services": self.target_services,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "occurrence_count": self.occurrence_count,
            "novelty_score": round(self.novelty_score, 3),
            "severity_estimate": self.severity_estimate,
            "attack_vector": self.attack_vector,
            "confidence": round(self.confidence, 2),
            "matched_cves": self.matched_cves,
            "indicators": self.indicators,
        }
