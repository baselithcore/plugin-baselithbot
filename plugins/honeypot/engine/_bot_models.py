"""Bot detection dataclasses (signals and results)."""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class BotDetectionSignals:
    """Captured signals for bot detection."""

    # Static Signals
    user_agent_score: Optional[float] = None
    payload_pattern_score: Optional[float] = None
    ja4_fingerprint: Optional[str] = None

    # Behavioral/Temporal Signals
    inter_request_interval_ms: Optional[float] = None
    request_rate_per_minute: Optional[float] = None
    session_duration_ms: Optional[float] = None
    payload_entropy: Optional[float] = None
    pattern_repetition_score: Optional[float] = None
    timing_variance: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class BotDetectionResult:
    """Result of bot detection analysis."""

    is_bot: bool
    confidence: float
    signals: BotDetectionSignals
    classification: str  # "bot", "likely_bot", "likely_human", "human", "unknown"
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_bot": self.is_bot,
            "confidence": self.confidence,
            "signals": self.signals.to_dict(),
            "classification": self.classification,
            "reason": self.reason,
        }
