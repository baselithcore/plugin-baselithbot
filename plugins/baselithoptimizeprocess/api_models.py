"""HTTP request/response payloads for the BOP router.

Separated from :mod:`models` so domain objects stay free of transport concerns.
These thin DTOs validate inbound JSON and shape a few responses; everything else
reuses the domain models directly as FastAPI response schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .apply_models import ChangeGuard
from .automation_models import RuleAction, RuleTrigger
from .event_models import Event
from .models import (
    KpiDefinition,
    MetricSample,
    ProcessEdge,
    ProcessNode,
)
from .sla_models import SlaScope


class RegisterProcessRequest(BaseModel):
    """Payload to register/replace a process via the JSON DAG path."""

    id: str = Field(..., description="Desired process id (unique).")
    name: str = Field(..., description="Human-readable process name.")
    description: str = Field("", description="What the process accomplishes.")
    nodes: list[ProcessNode] = Field(default_factory=list)
    edges: list[ProcessEdge] = Field(default_factory=list)
    kpis: list[KpiDefinition] = Field(
        default_factory=list, description="User-defined metrics to monitor."
    )
    currency: str = Field(default="EUR", description="ISO currency for cost rollups.")
    annual_case_volume: float | None = Field(
        default=None, ge=0.0, description="Cases per year, to scale cost to annual."
    )


class ImportProcessRequest(BaseModel):
    """Payload to import a process from a BPMN/XML document."""

    id: str = Field(..., description="Desired process id (unique).")
    xml: str = Field(..., min_length=1, description="BPMN 2.0 / XML source.")
    kpis: list[KpiDefinition] = Field(
        default_factory=list, description="KPIs to attach to the imported process."
    )


class IngestMetricsRequest(BaseModel):
    """Batch of metric samples to ingest for a process."""

    samples: list[MetricSample] = Field(
        ..., min_length=1, description="One or more observed KPI samples."
    )


class OptimizeRequest(BaseModel):
    """Trigger an optimization pass, optionally with extra free-text context."""

    context: str = Field(
        "", description="Optional operator hints for the optimizer agent."
    )
    max_proposals: int = Field(
        5, ge=1, le=20, description="Upper bound on proposals to generate."
    )


class DecisionRequest(BaseModel):
    """Human approve/reject decision on a proposal."""

    note: str = Field("", description="Optional reviewer note.")


class HealthResponse(BaseModel):
    """Liveness payload for the plugin."""

    plugin: str
    version: str
    processes: int = Field(0, description="Number of registered processes.")


class MineRequest(BaseModel):
    """Event log to mine into a discovered process."""

    id: str = Field(..., description="Process id to assign to the discovery.")
    name: str = Field(default="", description="Optional display name.")
    events: list[Event] = Field(
        ..., min_length=1, description="Raw event-log records to mine."
    )
    min_frequency: int = Field(
        default=0,
        ge=0,
        description="Drop directly-follows transitions rarer than this (noise filter).",
    )


class ConformanceRequest(BaseModel):
    """Event log to check against an existing process model."""

    events: list[Event] = Field(
        ..., min_length=1, description="Observed events to score."
    )


class CreateRuleRequest(BaseModel):
    """Definition of a new automation rule."""

    name: str = Field(..., description="Human-readable rule name.")
    trigger: RuleTrigger = Field(default_factory=RuleTrigger)
    action: RuleAction = Field(default_factory=RuleAction)
    enabled: bool = Field(default=True)


class ConnectorTextRequest(BaseModel):
    """Ingest an event log / metric stream from inline CSV or JSON text."""

    text: str = Field(..., min_length=1, description="CSV or JSON payload.")
    kind: str = Field(
        default="events", description="'events' (mine) or 'metrics' (ingest)."
    )
    name: str = Field(default="", description="Display name for mined processes.")
    min_frequency: int = Field(
        default=0, ge=0, description="Noise filter for mined transitions."
    )


class ConnectorPullRequest(BaseModel):
    """Pull an event log / metric stream from a remote HTTP source."""

    url: str = Field(..., min_length=1, description="HTTP(S) source URL.")
    kind: str = Field(
        default="events", description="'events' (mine) or 'metrics' (ingest)."
    )
    name: str = Field(default="", description="Display name for mined processes.")
    min_frequency: int = Field(
        default=0, ge=0, description="Noise filter for mined transitions."
    )


class PredictRequest(BaseModel):
    """A running (in-flight) case to forecast against the learned model."""

    events: list[Event] = Field(
        ..., min_length=1, description="The running case's events so far."
    )


class SlaCreateRequest(BaseModel):
    """Definition of a new service-level agreement for a process."""

    name: str = Field(..., min_length=1, description="Human-readable SLA name.")
    scope: SlaScope = Field(
        default=SlaScope.CASE, description="Time the whole case or one activity."
    )
    activity: str = Field(
        default="", description="Target activity name (required for ACTIVITY scope)."
    )
    threshold_seconds: float = Field(
        ..., gt=0.0, description="Maximum allowed seconds before a breach."
    )


class ResourceCreateRequest(BaseModel):
    """Definition of a new assignable resource in the tenant pool."""

    id: str = Field(default="", description="Optional id; generated when blank.")
    name: str = Field(..., min_length=1, description="Human-readable resource name.")
    role: str = Field(default="", description="Role/title copied onto assigned steps.")
    cost_per_hour: float = Field(
        default=0.0, ge=0.0, description="Fully-loaded hourly labour rate."
    )
    currency: str = Field(default="EUR", description="ISO currency of the rate.")
    capacity_hours_per_week: float | None = Field(
        default=None, ge=0.0, description="Optional weekly availability."
    )
    skills: list[str] = Field(
        default_factory=list, description="Capabilities/skills offered."
    )
    active: bool = Field(default=True, description="Whether currently assignable.")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Free-form attributes."
    )


class ResourceUpdateRequest(BaseModel):
    """Partial update of a resource; only the supplied fields change."""

    name: str | None = Field(default=None, min_length=1)
    role: str | None = None
    cost_per_hour: float | None = Field(default=None, ge=0.0)
    currency: str | None = None
    capacity_hours_per_week: float | None = Field(default=None, ge=0.0)
    skills: list[str] | None = None
    active: bool | None = None
    metadata: dict[str, str] | None = None


class AssignResourceRequest(BaseModel):
    """Assign (or clear) the resource on a process step."""

    resource_id: str | None = Field(
        default=None, description="Resource to assign; null clears the assignment."
    )


class ApplyRequest(RegisterProcessRequest):
    """Apply a candidate redesign as a governed, reversible change.

    Carries the full variant graph (inherited) plus the originating proposal and
    an optional auto-rollback guard.
    """

    proposal_id: str = Field(default="", description="Originating proposal, if any.")
    guard: ChangeGuard | None = Field(
        default=None, description="Optional KPI auto-rollback guard."
    )


__all__ = [
    "RegisterProcessRequest",
    "ImportProcessRequest",
    "IngestMetricsRequest",
    "OptimizeRequest",
    "DecisionRequest",
    "HealthResponse",
    "MineRequest",
    "ConformanceRequest",
    "CreateRuleRequest",
    "ApplyRequest",
    "ConnectorTextRequest",
    "ConnectorPullRequest",
    "SlaCreateRequest",
    "PredictRequest",
    "ResourceCreateRequest",
    "ResourceUpdateRequest",
    "AssignResourceRequest",
]
