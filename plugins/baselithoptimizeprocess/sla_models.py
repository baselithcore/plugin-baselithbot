"""Models for the performance & SLA layer.

Process performance is about *time*: how long cases take end-to-end and how long
each step waits, expressed as percentile distributions (P50/P90/P95/P99) rather
than misleading averages. On top of that sit user-defined Service-Level
Agreements — a target time for the whole case or a single activity — that the
engine evaluates into breach rates. SLA definitions are persisted (they are
governance artefacts); reports are computed on demand from the stored event log.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from ._stats import Distribution


def _utcnow() -> datetime:
    """Timezone-aware UTC stamp (no naive clocks)."""
    return datetime.now(timezone.utc)


class SlaScope(str, Enum):
    """What an SLA times: the whole case, or one activity's wait."""

    CASE = "case"
    ACTIVITY = "activity"


class SlaDefinition(BaseModel):
    """A user-defined service-level target attached to a process.

    ``CASE`` scope times end-to-end case duration; ``ACTIVITY`` scope times the
    wait into a named activity (per occurrence). A breach is any observation whose
    seconds exceed ``threshold_seconds`` — slower is always worse for time SLAs.
    """

    id: str = Field(..., description="Stable SLA identifier, unique per process.")
    process_id: str = Field(..., description="Owning process id.")
    name: str = Field(..., description="Human-readable SLA name.")
    scope: SlaScope = Field(default=SlaScope.CASE, description="Case or activity.")
    activity: str = Field(
        default="", description="Target activity name (required for ACTIVITY scope)."
    )
    threshold_seconds: float = Field(
        ..., gt=0.0, description="Maximum allowed seconds before a breach."
    )
    created_at: datetime = Field(default_factory=_utcnow)


class SlaResult(BaseModel):
    """Evaluation of one SLA against the observed event log."""

    sla_id: str
    name: str
    scope: SlaScope
    activity: str = ""
    threshold_seconds: float
    observations: int = Field(default=0, description="Timed observations evaluated.")
    breaches: int = Field(default=0, description="Observations over the threshold.")
    breach_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Fraction breaching (0..1)."
    )
    worst_value: float = Field(default=0.0, description="Slowest observed seconds.")
    p90_value: float = Field(default=0.0, description="90th-percentile seconds.")


class ActivityPerformance(BaseModel):
    """Per-activity waiting-time performance."""

    activity: str
    occurrences: int = Field(..., description="Times this activity was executed.")
    wait: Distribution = Field(..., description="Wait-into-activity distribution.")


class PerformanceReport(BaseModel):
    """End-to-end throughput + per-activity waits + SLA evaluation."""

    process_id: str
    case_count: int = Field(..., description="Distinct cases analysed.")
    cycle_time: Distribution = Field(
        ..., description="End-to-end case-duration distribution."
    )
    activities: list[ActivityPerformance] = Field(default_factory=list)
    slas: list[SlaResult] = Field(default_factory=list)


__all__ = [
    "SlaScope",
    "SlaDefinition",
    "SlaResult",
    "ActivityPerformance",
    "PerformanceReport",
]
