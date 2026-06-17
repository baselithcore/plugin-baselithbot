"""Event-log, process-mining, and conformance models for BOP's DataOps layer.

These types power the Celonis-style capabilities: discovering a process from raw
event data, analysing path variants, and checking how faithfully a mapped model
reflects what actually happens. Kept transport-agnostic (no HTTP/FastAPI) so the
mining and conformance engines stay pure and unit-testable.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Event(BaseModel):
    """A single event-log record: one activity executed for one case."""

    case_id: str = Field(..., description="Process-instance (case) identifier.")
    activity: str = Field(..., description="Activity/step name that occurred.")
    timestamp: datetime = Field(..., description="When the activity completed.")
    resource: str = Field(default="", description="Actor/system that performed it.")


class ActivityStat(BaseModel):
    """Aggregate statistics for a single discovered activity."""

    activity: str
    occurrences: int = Field(..., description="Total events for this activity.")
    avg_wait_seconds: float = Field(
        default=0.0, description="Mean time from the previous step into this one."
    )
    rework_count: int = Field(
        default=0,
        description="Repeat executions of this activity within a case (rework).",
    )


class Variant(BaseModel):
    """A distinct end-to-end path through the process and how often it occurs."""

    sequence: list[str] = Field(..., description="Ordered activity names.")
    count: int = Field(..., description="Number of cases following this path.")
    avg_duration_seconds: float = Field(
        default=0.0, description="Mean case duration for this variant."
    )


class MiningResult(BaseModel):
    """Output of mining an event log: a discovered model plus analytics."""

    process_id: str
    case_count: int = Field(..., description="Distinct cases in the log.")
    activity_stats: list[ActivityStat] = Field(default_factory=list)
    variants: list[Variant] = Field(default_factory=list)
    avg_case_duration_seconds: float = Field(default=0.0)
    rework_cases: int = Field(
        default=0, description="Cases where some activity executed more than once."
    )
    rework_rate: float = Field(
        default=0.0, description="Fraction of cases exhibiting rework (0..1)."
    )
    self_loops: list[str] = Field(
        default_factory=list, description="Activities that directly follow themselves."
    )
    concurrent_activities: list[list[str]] = Field(
        default_factory=list,
        description="Activity pairs observed in both orders (likely parallel).",
    )


class TransitionDeviation(BaseModel):
    """A directly-follows transition seen in the log but absent from the model."""

    source: str
    target: str
    count: int


class ConformanceReport(BaseModel):
    """How well a mapped model conforms to an observed event log."""

    process_id: str
    fitness: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of observed transitions in model."
    )
    alignment_fitness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Replay/alignment fitness: 1 − cost/max-cost (start/end aware).",
    )
    avg_case_fitness: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean per-case alignment fitness."
    )
    conforming_cases: int = Field(default=0)
    deviating_cases: int = Field(default=0)
    undesired_transitions: list[TransitionDeviation] = Field(default_factory=list)
    unseen_activities: list[str] = Field(
        default_factory=list, description="Model steps never observed in the log."
    )
    deviation_cost: float = Field(
        default=0.0,
        description="Monetary cost of deviating executions (model node costs).",
    )
    currency: str = Field(default="EUR", description="Currency for deviation_cost.")


__all__ = [
    "Event",
    "ActivityStat",
    "Variant",
    "MiningResult",
    "TransitionDeviation",
    "ConformanceReport",
]
