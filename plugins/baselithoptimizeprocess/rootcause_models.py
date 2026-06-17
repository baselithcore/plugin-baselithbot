"""Models for root-cause analysis of slow / out-of-SLA cases.

Process mining's "why" layer: instead of only reporting *that* cases are slow,
correlate the bad outcome against case attributes (the resource that handled it,
which activities it touched, which variant it followed, whether it reworked) and
rank the factors by how much excess slowness each explains. Lift > 1 means the
factor co-occurs with the bad outcome more than the baseline rate.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FactorDimension(str, Enum):
    """The kind of case attribute a root-cause factor describes."""

    RESOURCE = "resource"
    ACTIVITY = "activity"
    VARIANT = "variant"
    PATTERN = "pattern"


class RootCauseFactor(BaseModel):
    """One correlated factor and how strongly it explains the bad outcome."""

    dimension: FactorDimension
    factor: str = Field(..., description="The attribute value, e.g. 'resource=Alice'.")
    cases_with_factor: int = Field(..., description="Cases exhibiting the factor.")
    bad_with_factor: int = Field(
        ..., description="Bad-outcome cases exhibiting the factor."
    )
    factor_breach_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Bad rate among cases with the factor."
    )
    baseline_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Bad rate across all cases."
    )
    lift: float = Field(
        default=0.0,
        description="factor_breach_rate / baseline_rate (>1 = over-represented).",
    )
    impact_score: float = Field(
        default=0.0,
        description="Excess bad cases attributable to the factor (rate delta × support).",
    )


class RootCauseReport(BaseModel):
    """Ranked factors explaining why a process's cases miss their time target."""

    process_id: str
    outcome: str = Field(
        default="slow_cases", description="Outcome analysed (e.g. 'slow_cases')."
    )
    threshold_seconds: float = Field(
        default=0.0, description="Case-duration cutoff above which a case is 'bad'."
    )
    total_cases: int = Field(..., description="Cases analysed.")
    bad_cases: int = Field(..., description="Cases meeting the bad-outcome condition.")
    baseline_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Bad-outcome rate across all cases."
    )
    factors: list[RootCauseFactor] = Field(default_factory=list)


__all__ = ["FactorDimension", "RootCauseFactor", "RootCauseReport"]
