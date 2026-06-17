"""Models for case-level predictive monitoring.

The forward-looking lens (Apromore-style): given a *running* case and a model
learned from completed history, predict how long it has left, what it will do
next, and whether it will miss its SLA. Predictions are empirical — derived from
the distribution of historical cases that passed through the same state — so they
are explainable (every number traces back to observed cases) and need no ML
runtime. State is keyed by the case's current (most recent) activity.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._stats import Distribution


class NextActivity(BaseModel):
    """A candidate next step and how often it followed the current state."""

    activity: str
    probability: float = Field(..., ge=0.0, le=1.0, description="Empirical P(next).")


class StatePrediction(BaseModel):
    """Learned per-state statistics (the transparent "model card" row)."""

    activity: str = Field(..., description="The state (current activity).")
    observations: int = Field(..., description="Historical events seen in this state.")
    remaining: Distribution = Field(
        ..., description="Remaining-time-to-completion distribution from this state."
    )
    next_activities: list[NextActivity] = Field(default_factory=list)
    is_terminal: bool = Field(
        default=False, description="No successor ever observed (a case-end state)."
    )


class PredictorModel(BaseModel):
    """The full learned predictor over a process's history (inspectable)."""

    process_id: str
    case_count: int = Field(..., description="Completed cases the model learned from.")
    states: list[StatePrediction] = Field(default_factory=list)


class SlaPrediction(BaseModel):
    """A running case's projected outcome against one case-scoped SLA."""

    sla_id: str
    name: str
    threshold_seconds: float
    projected_seconds: float = Field(
        ..., description="Elapsed + predicted remaining (mean)."
    )
    violation_probability: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Empirical P(total > threshold) for cases in this state.",
    )
    will_breach: bool = Field(
        default=False, description="Projected total already exceeds the threshold."
    )


class CasePrediction(BaseModel):
    """The forecast for a single running case."""

    process_id: str
    case_id: str
    current_activity: str
    elapsed_seconds: float = Field(..., description="Time since the case started.")
    completed: bool = Field(
        default=False, description="Current state is terminal (nothing to predict)."
    )
    predicted_remaining_seconds: float = Field(default=0.0)
    predicted_remaining_p90_seconds: float = Field(default=0.0)
    predicted_total_seconds: float = Field(default=0.0)
    next_activities: list[NextActivity] = Field(default_factory=list)
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Support-based confidence (0..1)."
    )
    slas: list[SlaPrediction] = Field(default_factory=list)


__all__ = [
    "NextActivity",
    "StatePrediction",
    "PredictorModel",
    "SlaPrediction",
    "CasePrediction",
]
