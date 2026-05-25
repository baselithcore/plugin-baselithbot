"""Adversary-emulation result models."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EmulationOutcome(str, enum.Enum):
    """Per-step execution outcome reported by the daemon."""

    EXECUTED = "executed"
    """The Atomic command ran and exited; says nothing about whether
    a defender alerted on it. Detection coverage analysis happens
    out-of-band against the SIEM."""

    PRECONDITION_FAILED = "precondition_failed"
    """Required input/host state was missing — the test self-skipped
    rather than running."""

    BLOCKED = "blocked"
    """A defender blocked execution (EDR kill, AppLocker deny). This
    *is* the success case from a purple-team perspective."""

    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EmulationResult(BaseModel):
    """One step's execution result, returned by the daemon executor."""

    plan_id: UUID
    step_index: int
    technique_id: str
    agent_id: str = Field(description="Endpoint daemon that executed the step.")
    outcome: EmulationOutcome
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: datetime = Field(default_factory=_utcnow)
    duration_seconds: float = 0.0
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    artifacts: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Files produced by the test (event log snippet, dropped "
            "artefact path, OAST callback id). Keys are descriptive; "
            "values are bounded — anything large is uploaded to the "
            "audit object store and referenced by URL here."
        ),
    )
    extra: dict[str, Any] = Field(default_factory=dict)


class EmulationRunSummary(BaseModel):
    """Aggregate view of one plan execution.

    Computed once all steps have settled. Carries the per-outcome
    histogram so the UI can render a glance card without scanning
    the per-step list.
    """

    id: UUID = Field(default_factory=uuid4)
    plan_id: UUID
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: datetime | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    results: list[EmulationResult] = Field(default_factory=list)

    def add(self, result: EmulationResult) -> None:
        """Append a step result and update the histogram in place."""

        self.results.append(result)
        key = result.outcome.value
        self.counts[key] = self.counts.get(key, 0) + 1

    def techniques_blocked(self) -> list[str]:
        """Return ATT&CK technique ids that defenders blocked."""

        return sorted(
            {
                r.technique_id
                for r in self.results
                if r.outcome == EmulationOutcome.BLOCKED
            }
        )

    def techniques_unblocked(self) -> list[str]:
        """Return ids that executed end-to-end without being blocked."""

        return sorted(
            {
                r.technique_id
                for r in self.results
                if r.outcome == EmulationOutcome.EXECUTED
            }
        )
