"""Resource pool domain model + pure cost materialization.

A :class:`Resource` is a reusable, tenant-scoped actor that performs process
steps — a role with a known hourly rate and capabilities (a person, a team, a
machine, a system account). Assigning a resource to a :class:`ProcessNode` makes
the resource the *source of truth* for that step's labour economics: the node's
``cost.labor_cost_per_hour`` (and, when set, its ``role``) are derived from the
resource so cost rollups, ROI estimation, and simulation speak in real numbers
instead of hand-typed guesses.

:func:`apply_resource_costs` is the single, pure place that derivation happens:
given a graph and the tenant's resource map it rewrites the assigned nodes in
place. The service calls it on every save path (register, apply) and whenever a
resource's rate changes, so the pure cost layer (``cost.py``/``simulation.py``)
keeps operating on a plain :class:`ProcessGraph` with no resource lookups — no
regression to the existing economics, just more accurate inputs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .models import NodeCost, ProcessGraph


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp (testable seam, no naive clocks)."""
    return datetime.now(timezone.utc)


class Resource(BaseModel):
    """A reusable actor (person/team/machine) assignable to process steps.

    Tenant-scoped and process-independent: one pool of resources can be assigned
    across every process a tenant maps. ``cost_per_hour`` is the fully-loaded
    labour rate that flows onto an assigned step's :class:`NodeCost`.
    """

    id: str = Field(..., description="Stable resource identifier, unique per tenant.")
    name: str = Field(..., description="Human-readable resource name.")
    role: str = Field(
        default="", description="Role/title; copied onto an assigned step's owner."
    )
    cost_per_hour: float = Field(
        default=0.0, ge=0.0, description="Fully-loaded hourly labour rate."
    )
    currency: str = Field(default="EUR", description="ISO currency of the rate.")
    capacity_hours_per_week: float | None = Field(
        default=None, ge=0.0, description="Optional weekly availability for planning."
    )
    skills: list[str] = Field(
        default_factory=list, description="Capabilities/skills this resource offers."
    )
    active: bool = Field(
        default=True, description="Whether the resource is currently assignable."
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Free-form attributes (department, contact…)."
    )
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


def resource_map(resources: list[Resource]) -> dict[str, Resource]:
    """Index a list of resources by id for O(1) assignment lookups."""
    return {r.id: r for r in resources}


def apply_resource_costs(
    graph: ProcessGraph, resources: dict[str, Resource]
) -> ProcessGraph:
    """Materialize each assigned resource's rate/role onto its node (in place).

    For every node carrying a ``resource_id`` that resolves in ``resources``, the
    node's ``cost.labor_cost_per_hour`` is set from the resource (preserving the
    node's own step-specific handling time, rework, and fixed cost) and its
    ``role`` is set from the resource when the resource declares one. Nodes with
    no/unknown resource are left untouched, so costing stays strictly opt-in.

    Returns the same graph object for convenient chaining.
    """
    for node in graph.nodes:
        resource = resources.get(node.resource_id or "")
        if resource is None:
            continue
        base = node.cost or NodeCost()
        node.cost = base.model_copy(
            update={"labor_cost_per_hour": resource.cost_per_hour}
        )
        if resource.role:
            node.role = resource.role
    return graph


__all__ = ["Resource", "resource_map", "apply_resource_costs"]
