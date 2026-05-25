"""Adversary-emulation plan models.

A plan describes the *intent* of an emulation run before any code
executes on the target endpoint:

- which ATT&CK techniques will fire,
- in what order,
- with what input parameters,
- against which authorized hosts,
- under whose attestation.

The plan must round-trip cleanly through the existing signed
policy-bundle pipeline: an operator authors it, a reviewer signs
it, the daemon verifies the signature before invoking its local
executor. The classes below capture the wire shape; signing /
verification reuses :mod:`plugins.red_agent.crypto`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PlanLoadError(ValueError):
    """Raised when a YAML plan or Atomic test cannot be parsed."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AtomicTest(BaseModel):
    """A single Atomic Red Team test definition.

    Mirrors the upstream YAML shape under
    ``atomics/T<id>/T<id>.yaml`` minus the human-readable prose; the
    fields below are exactly what the daemon executor needs to run
    the test and surface a structured result.
    """

    name: str = Field(description="Test name from the Atomic YAML.")
    auto_generated_guid: str | None = Field(
        default=None,
        description="Stable upstream GUID; preferred selector when set.",
    )
    description: str = ""
    supported_platforms: list[str] = Field(default_factory=list)
    executor: str = Field(
        description=(
            "Atomic executor identifier — ``command_prompt``, "
            "``powershell``, ``sh``, ``bash``, ``manual``."
        ),
    )
    command: str = Field(description="Command line template.")
    cleanup_command: str | None = None
    input_arguments: dict[str, Any] = Field(default_factory=dict)
    elevation_required: bool = False


class EmulationStep(BaseModel):
    """One technique invocation inside an :class:`EmulationPlan`."""

    technique_id: str = Field(
        description="ATT&CK technique ID (e.g. ``T1059.001``).",
    )
    technique_name: str = ""
    test: AtomicTest = Field(
        description="Atomic test selected for this technique.",
    )
    input_overrides: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Operator-supplied substitutions for the Atomic test's "
            "input arguments. Validated server-side before signing."
        ),
    )
    timeout_seconds: int = Field(
        default=120,
        description="Wall-clock cap for this step on the daemon.",
    )
    require_cleanup: bool = Field(
        default=True,
        description=(
            "Run the test's ``cleanup_command`` after execution. Off "
            "only when the operator explicitly wants the post-state "
            "preserved for forensic capture."
        ),
    )


class EmulationPlan(BaseModel):
    """Authorized adversary-emulation plan."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    target_agent_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Endpoint daemon UUIDs the plan is authorized against. "
            "An empty list means *no* hosts; the daemon executor "
            "rejects unbound plans by construction."
        ),
    )
    engagement_id: UUID | None = Field(
        default=None,
        description=(
            "Engagement this plan rolls up to. Inherits the autonomy "
            "level + intrusive gate from the engagement."
        ),
    )
    steps: list[EmulationStep] = Field(default_factory=list)
    authored_by: str = Field(description="Operator who composed the plan.")
    reviewed_by: str | None = Field(
        default=None,
        description=(
            "Second-operator reviewer for the dual-control "
            "requirement. Populated by the approval workflow."
        ),
    )
    created_at: datetime = Field(default_factory=_utcnow)

    def techniques(self) -> list[str]:
        """Convenience: ordered list of unique technique IDs."""

        seen: list[str] = []
        for step in self.steps:
            if step.technique_id not in seen:
                seen.append(step.technique_id)
        return seen

    def is_dual_controlled(self) -> bool:
        """``True`` when the plan was reviewed by a different operator."""

        return bool(self.reviewed_by) and self.reviewed_by != self.authored_by
