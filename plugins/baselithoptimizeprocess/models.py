"""Domain models for the BaselithOptimizeProcess (BOP) plugin.

These Pydantic models are the plugin's ubiquitous language: a business process
is a directed execution graph, its health is measured by *user-defined* KPIs,
and optimization is expressed as human-in-the-loop proposals. No metric, target,
or business rule is hard-coded here — every efficiency dimension is supplied by
the caller at runtime via :class:`KpiDefinition`.

The models are deliberately transport-agnostic (no FastAPI/HTTP concerns) so the
service, agent, and store layers can all share them without coupling to the API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp (testable seam, no naive clocks)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class KpiDirection(str, Enum):
    """Optimization direction for a KPI.

    ``MINIMIZE`` for cost/latency/error-style metrics, ``MAXIMIZE`` for
    throughput/quality-style metrics. Used to decide whether an observed value
    breaches its target and to orient the optimizer's reasoning.
    """

    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class NodeKind(str, Enum):
    """Coarse classification of a process step.

    Kept intentionally generic so any domain (manufacturing, support, finance)
    can map onto it without the core needing domain knowledge.
    """

    START = "start"
    TASK = "task"
    DECISION = "decision"
    PARALLEL = "parallel"
    END = "end"


class Severity(str, Enum):
    """Severity ranking for a detected bottleneck."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProposalStatus(str, Enum):
    """Lifecycle of an optimization proposal under human-in-the-loop control.

    Proposals are never auto-applied: they start ``PROPOSED`` and only a human
    decision moves them to ``APPROVED``/``REJECTED``; ``APPLIED`` records that an
    approved change was rolled out by an external actor.
    """

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


# ---------------------------------------------------------------------------
# KPI definitions (user-supplied, never hard-coded)
# ---------------------------------------------------------------------------


class KpiDefinition(BaseModel):
    """A single user-defined efficiency metric attached to a process.

    The caller decides *what* matters for their use case (cycle time, cost,
    throughput, SLA breach rate, …). BOP only needs the metric's identity, unit,
    optimization direction, and optional target to monitor and reason about it.
    """

    id: str = Field(..., description="Stable KPI identifier, unique per process.")
    name: str = Field(..., description="Human-readable KPI name.")
    unit: str = Field(
        default="", description="Unit of measure, e.g. 'seconds', 'USD', '%'."
    )
    direction: KpiDirection = Field(
        default=KpiDirection.MINIMIZE, description="Whether lower or higher is better."
    )
    target: float | None = Field(
        default=None,
        description="Optional target/threshold value for breach detection.",
    )
    description: str = Field(default="", description="What this KPI measures and why.")


# ---------------------------------------------------------------------------
# Process graph
# ---------------------------------------------------------------------------


class NodeCost(BaseModel):
    """Optional cost economics for a process step (drives ROI estimation).

    All fields default to zero so costing is strictly opt-in: a process mapped
    without cost data behaves exactly as before. Per-case cost of the step is
    ``(avg_handling_seconds/3600 * labor_cost_per_hour + fixed_cost)`` inflated
    by ``rework_rate`` (the share of executions that must be redone).
    """

    labor_cost_per_hour: float = Field(
        default=0.0, ge=0.0, description="Fully-loaded labour rate for this step."
    )
    avg_handling_seconds: float = Field(
        default=0.0, ge=0.0, description="Mean hands-on time per execution."
    )
    rework_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Fraction of executions redone."
    )
    fixed_cost: float = Field(
        default=0.0, ge=0.0, description="Per-execution fixed cost (tools, fees)."
    )


class ProcessNode(BaseModel):
    """A single step in a business process execution graph."""

    id: str = Field(..., description="Node identifier, unique within the process.")
    name: str = Field(..., description="Human-readable step name.")
    kind: NodeKind = Field(
        default=NodeKind.TASK, description="Coarse step classification."
    )
    role: str = Field(default="", description="Owning team/role/system for this step.")
    resource_id: str | None = Field(
        default=None,
        description="Assigned resource id; its rate/role materialize onto this step.",
    )
    cost: NodeCost | None = Field(
        default=None, description="Optional cost economics for ROI estimation."
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Free-form domain attributes."
    )


class ProcessEdge(BaseModel):
    """A directed transition between two process steps."""

    source: str = Field(..., description="Source node id.")
    target: str = Field(..., description="Target node id.")
    condition: str = Field(
        default="", description="Optional guard/condition label for the transition."
    )


class ProcessGraph(BaseModel):
    """A mapped business process: nodes, transitions, and the KPIs that grade it."""

    id: str = Field(..., description="Process identifier, unique per deployment.")
    name: str = Field(..., description="Human-readable process name.")
    description: str = Field(default="", description="What the process accomplishes.")
    nodes: list[ProcessNode] = Field(default_factory=list)
    edges: list[ProcessEdge] = Field(default_factory=list)
    kpis: list[KpiDefinition] = Field(
        default_factory=list, description="User-defined metrics for this process."
    )
    currency: str = Field(default="EUR", description="ISO currency for cost rollups.")
    annual_case_volume: float | None = Field(
        default=None,
        ge=0.0,
        description="Cases processed per year; scales per-case cost to annual.",
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def node_ids(self) -> set[str]:
        """Return the set of declared node ids (for edge/sample validation)."""
        return {node.id for node in self.nodes}

    def kpi_ids(self) -> set[str]:
        """Return the set of declared KPI ids."""
        return {kpi.id for kpi in self.kpis}


# ---------------------------------------------------------------------------
# Metrics & monitoring
# ---------------------------------------------------------------------------


class MetricSample(BaseModel):
    """A single observed measurement of a KPI, optionally scoped to one node."""

    process_id: str = Field(..., description="Owning process id.")
    kpi_id: str = Field(..., description="KPI this sample measures.")
    value: float = Field(..., description="Observed numeric value.")
    node_id: str | None = Field(
        default=None, description="Optional step the sample is attributed to."
    )
    timestamp: datetime = Field(default_factory=_utcnow)


class KpiSnapshot(BaseModel):
    """A point-in-time aggregate of a KPI, derived from recent samples."""

    process_id: str
    kpi_id: str
    value: float = Field(..., description="Current aggregated KPI value.")
    target: float | None = Field(
        default=None, description="Target carried from definition."
    )
    direction: KpiDirection = KpiDirection.MINIMIZE
    breaching: bool = Field(
        default=False, description="True if value violates the target."
    )
    sample_count: int = Field(
        default=0, description="Samples contributing to this value."
    )
    timestamp: datetime = Field(default_factory=_utcnow)


class Bottleneck(BaseModel):
    """A detected inefficiency: a KPI breach localized to a process region."""

    process_id: str
    kpi_id: str
    node_id: str | None = Field(
        default=None, description="Step the bottleneck localizes to."
    )
    severity: Severity = Severity.MEDIUM
    observed: float = Field(..., description="Observed KPI value.")
    target: float | None = Field(default=None, description="Target it deviates from.")
    detail: str = Field(default="", description="Human-readable explanation.")
    detected_at: datetime = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Optimization (human-in-the-loop)
# ---------------------------------------------------------------------------


class MoneyImpact(BaseModel):
    """A quantified monetary effect attached to a proposal."""

    amount: float = Field(..., description="Estimated amount (positive = saving).")
    currency: str = Field(default="EUR", description="ISO currency code.")
    period: str = Field(default="annual", description="Basis: 'per_case' or 'annual'.")
    basis: str = Field(
        default="", description="How the estimate was derived (transparency)."
    )


class OptimizationProposal(BaseModel):
    """A suggested process change, awaiting human approval before any rollout.

    Proposals are advisory by design (suggest-only autonomy): the agent grounds
    each one in observed bottlenecks and KPI targets, but a human decides.
    """

    id: str = Field(..., description="Proposal identifier.")
    process_id: str = Field(..., description="Process the proposal targets.")
    title: str = Field(..., description="Short summary of the change.")
    rationale: str = Field(..., description="Why this change should help.")
    target_nodes: list[str] = Field(
        default_factory=list, description="Steps the change affects."
    )
    addresses_kpis: list[str] = Field(
        default_factory=list, description="KPI ids the change aims to improve."
    )
    expected_impact: str = Field(
        default="", description="Qualitative/quantitative expected effect."
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Agent confidence in the proposal."
    )
    estimated_savings: MoneyImpact | None = Field(
        default=None, description="Quantified ROI when cost data is available."
    )
    status: ProposalStatus = Field(default=ProposalStatus.PROPOSED)
    created_at: datetime = Field(default_factory=_utcnow)
    decided_at: datetime | None = Field(
        default=None, description="When a human approved/rejected the proposal."
    )


__all__ = [
    "KpiDirection",
    "NodeKind",
    "Severity",
    "ProposalStatus",
    "KpiDefinition",
    "NodeCost",
    "ProcessNode",
    "ProcessEdge",
    "ProcessGraph",
    "MetricSample",
    "KpiSnapshot",
    "Bottleneck",
    "MoneyImpact",
    "OptimizationProposal",
]
