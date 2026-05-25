"""Honeypot Suggestion Models.

Pydantic models for representing honeypot suggestions generated
from attack pattern analysis.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SuggestionType(str, Enum):
    """Types of honeypot suggestions."""

    ZERODAY_PATTERN = "zeroday_pattern"
    BEHAVIORAL_CLUSTER = "behavioral_cluster"
    PROTOCOL_ANOMALY = "protocol_anomaly"
    EXPLOIT_TECHNIQUE = "exploit_technique"
    COMMAND_PATTERN = "command_pattern"


class SuggestionPriority(str, Enum):
    """Priority levels for suggestions."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SuggestedProtocol(str, Enum):
    """Suggested honeypot protocol types."""

    HTTP = "http"
    SSH = "ssh"
    TCP = "tcp"


class HoneypotSuggestion(BaseModel):
    """A suggested honeypot configuration based on attack analysis.

    Generated from patterns detected by ZeroDayDetector, behavioral
    clusters, or protocol anomalies.
    """

    id: str = Field(..., description="Unique suggestion identifier")
    suggestion_type: SuggestionType = Field(
        ..., description="Type of analysis that generated this suggestion"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    priority: SuggestionPriority = Field(
        ..., description="Priority for implementing this honeypot"
    )

    # Display information
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Detailed description")
    rationale: str = Field(
        ..., description="Explanation of why this honeypot would be useful"
    )

    # Suggested configuration
    suggested_protocol: SuggestedProtocol = Field(
        ..., description="Recommended protocol type"
    )
    suggested_port: int = Field(..., ge=1, le=65535, description="Recommended port")
    suggested_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Partial HoneypotDefinition configuration",
    )
    detection_patterns: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Suggested detection patterns to include",
    )
    tags: List[str] = Field(
        default_factory=list, description="Suggested tags for the honeypot"
    )

    # Source tracking
    source_anomaly_ids: List[str] = Field(
        default_factory=list,
        description="IDs of anomalies that triggered this suggestion",
    )
    source_patterns: List[str] = Field(
        default_factory=list,
        description="Fingerprints of patterns that triggered this",
    )
    source_ips: List[str] = Field(
        default_factory=list,
        description="Sample IPs associated with the pattern",
    )

    # Metrics
    estimated_catch_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Estimated percentage of similar attacks it would catch",
    )
    occurrence_count: int = Field(
        default=0, description="Number of times this pattern was observed"
    )

    # Relevance and quality indicators
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Investigation value score (0-1)",
    )
    sophistication_level: str = Field(
        default="basic",
        description="Attack complexity: basic, intermediate, or advanced",
    )
    investigation_rationale: str = Field(
        default="",
        description="Why this pattern is worth investigating",
    )
    merged_from_count: int = Field(
        default=1,
        ge=1,
        description="Number of similar patterns merged into this suggestion",
    )

    # Status
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When suggestion was created",
    )
    dismissed: bool = Field(
        default=False, description="Whether user dismissed this suggestion"
    )
    applied: bool = Field(
        default=False, description="Whether user created honeypot from this"
    )
    applied_honeypot_id: Optional[str] = Field(
        default=None, description="ID of honeypot created from this suggestion"
    )

    def to_yaml_config(self) -> Dict[str, Any]:
        """Generate a complete honeypot YAML configuration.

        Returns:
            Dict ready to be serialized as YAML.
        """
        config = {
            "id": self._generate_honeypot_id(),
            "name": self.title,
            "description": self.description,
            "protocol": self.suggested_protocol.value,
            "port": self.suggested_port,
            "bind_address": "0.0.0.0",  # nosec B104
            "handler_type": "auto",
            "enabled": True,
            "priority": 5,
            "tags": self.tags,
            "detection": {
                "log_all_requests": True,
                "custom_patterns": self.detection_patterns,
            },
            "response_mode": "static",
        }

        # Merge with suggested config overrides
        config.update(self.suggested_config)

        return config

    def _generate_honeypot_id(self) -> str:
        """Generate a honeypot ID from the suggestion."""
        # Convert title to slug format
        slug = self.title.lower()
        slug = slug.replace(" ", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        slug = slug[:50]  # Limit length
        return f"suggested-{slug}"


class SuggestionSummary(BaseModel):
    """Summary of all honeypot suggestions."""

    total_suggestions: int = Field(default=0, description="Total number of suggestions")
    active_suggestions: int = Field(
        default=0, description="Suggestions not dismissed or applied"
    )
    by_priority: Dict[str, int] = Field(
        default_factory=dict, description="Count by priority level"
    )
    by_type: Dict[str, int] = Field(
        default_factory=dict, description="Count by suggestion type"
    )
    top_suggestions: List[HoneypotSuggestion] = Field(
        default_factory=list, description="Highest priority suggestions"
    )
    last_analysis: Optional[datetime] = Field(
        default=None, description="When suggestions were last generated"
    )


class SuggestionListResponse(BaseModel):
    """API response for listing suggestions."""

    suggestions: List[HoneypotSuggestion] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    summary: SuggestionSummary = Field(default_factory=SuggestionSummary)
