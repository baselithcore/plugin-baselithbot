"""Correlation Analyzer Models.

Pydantic models for attacker correlation detection following cybersecurity standards.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CorrelationType(str, Enum):
    """Types of attacker correlations based on MITRE ATT&CK patterns.

    References:
    - https://attack.mitre.org/techniques/T1071/ (Application Layer Protocol)
    - https://attack.mitre.org/techniques/T1105/ (Ingress Tool Transfer)
    """

    TIMING = "timing"  # Attackers hitting same target within time window
    PATTERN = "pattern"  # Similar commands, payloads, or TTPs
    CROSS_HONEYPOT = "cross_honeypot"  # Same IP targeting multiple honeypots
    SEQUENTIAL = "sequential"  # Attacks happening in sequence (A then B)
    INFRASTRUCTURE = "infrastructure"  # Shared infrastructure (same ASN, subnet)


class AttackerCorrelation(BaseModel):
    """Represents a detected correlation between two attacker IPs.

    Based on threat intelligence best practices for correlation analysis.
    """

    correlation_id: str = Field(..., description="Unique correlation identifier")
    source_ip: str = Field(..., description="First attacker IP")
    target_ip: str = Field(..., description="Second attacker IP")
    correlation_type: CorrelationType = Field(..., description="Type of correlation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    strength: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Correlation strength"
    )

    # Evidence
    shared_honeypots: List[str] = Field(
        default_factory=list, description="Honeypots both attackers targeted"
    )
    time_delta_seconds: Optional[float] = Field(
        default=None, description="Time between attacks (for timing correlation)"
    )
    pattern_similarity: Optional[float] = Field(
        default=None, description="Similarity score for pattern correlation"
    )
    shared_commands: List[str] = Field(
        default_factory=list, description="Commands used by both attackers"
    )

    # Metadata
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When correlation was detected",
    )
    metadata: dict = Field(default_factory=dict, description="Additional context")


@dataclass
class CorrelationConfig:
    """Configuration for correlation detection thresholds.

    Based on industry standards for anomaly detection in SIEM systems.
    Timing windows derived from typical automated attack patterns.
    """

    # Timing correlation
    timing_window_seconds: float = 60.0  # Standard 60s window for coordinated attacks
    min_timing_confidence: float = 0.3  # Minimum confidence for timing correlation

    # Pattern correlation
    min_pattern_similarity: float = 0.7  # Jaccard similarity threshold
    min_shared_commands: int = 2  # Minimum shared commands for correlation

    # Cross-honeypot correlation
    min_cross_honeypot_count: int = 2  # Minimum honeypots for cross-honeypot flag
    cross_honeypot_boost: float = 1.5  # Threat score multiplier

    # Sequential correlation
    sequential_window_seconds: float = 300.0  # 5 minute window for sequential attacks
    min_sequential_events: int = 3  # Minimum events for sequential pattern

    # Infrastructure correlation
    same_subnet_mask: int = 24  # /24 subnet check for infrastructure correlation

    # General
    max_correlations_per_ip: int = 50  # Limit to prevent explosion


# Default configuration instance
DEFAULT_CORRELATION_CONFIG = CorrelationConfig()
