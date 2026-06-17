"""Domain models for governed change application + rollback.

Closing the optimization loop: an approved redesign can be *applied* as a new,
versioned graph; the action is tracked as an :class:`AppliedChange` so it can be
rolled back to the prior version at any time. An optional :class:`ChangeGuard`
arms an automatic rollback when a watched KPI regresses past a threshold after
the change goes live — turning "suggest-only" into safe, reversible execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp (no naive clocks)."""
    return datetime.now(timezone.utc)


class ChangeStatus(str, Enum):
    """Lifecycle of an applied change."""

    ACTIVE = "active"  # applied, no guard
    MONITORING = "monitoring"  # applied, guard armed and watching
    KEPT = "kept"  # guard cleared / change confirmed
    ROLLED_BACK = "rolled_back"  # reverted to the prior version


class ChangeGuard(BaseModel):
    """Auto-rollback condition watched after a change is applied."""

    kpi_id: str = Field(..., description="KPI to watch for regression.")
    max_regression_pct: float = Field(
        default=10.0,
        gt=0.0,
        description="Roll back if the KPI worsens by more than this percent.",
    )


class AppliedChange(BaseModel):
    """An audited, reversible application of a new process version."""

    id: str = Field(..., description="Change identifier.")
    process_id: str = Field(..., description="Process the change targets.")
    proposal_id: str = Field(default="", description="Originating proposal, if any.")
    from_version: int | None = Field(
        default=None, description="Version that was live before the change."
    )
    to_version: int = Field(..., description="Version this change introduced.")
    status: ChangeStatus = Field(default=ChangeStatus.ACTIVE)
    guard: ChangeGuard | None = Field(
        default=None, description="Optional auto-rollback guard."
    )
    baseline_value: float | None = Field(
        default=None, description="Watched KPI value captured just before apply."
    )
    applied_by: str = Field(default="anonymous", description="Principal that applied.")
    applied_at: datetime = Field(default_factory=_utcnow)
    resolved_at: datetime | None = Field(
        default=None, description="When the change was kept or rolled back."
    )
    detail: str = Field(default="", description="Human-readable context.")


__all__ = ["ChangeStatus", "ChangeGuard", "AppliedChange"]
