"""Cost rollup and ROI estimation for a process (pure, metric-free).

Turns the optional :class:`NodeCost` economics on a process graph into a
per-case / annual :class:`CostReport`, and translates a structural finding into a
quantified :class:`MoneyImpact` so optimization proposals can speak in euros, not
just "lower KPI". Everything here is deterministic and side-effect-free.

Savings heuristics are deliberately conservative and *transparent* (each impact
carries a ``basis`` string): the tool never fabricates a number when no cost data
exists — it returns ``None`` instead.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .models import MoneyImpact, ProcessGraph, ProcessNode
from .structural import StructuralFinding, StructuralFindingKind

# Conservative share of rework cost assumed removable when a loop is fixed.
_REWORK_REMOVAL_FACTOR = 0.5


class CostReport(BaseModel):
    """Per-case and annual cost rollup for a process."""

    process_id: str
    currency: str = "EUR"
    per_case_cost: float = 0.0
    annual_cost: float | None = None
    node_costs: dict[str, float] = Field(default_factory=dict)
    costed_nodes: int = 0
    total_nodes: int = 0


def node_cost(node: ProcessNode) -> float:
    """Per-execution cost of a single step, or 0 when it carries no cost data."""
    cost = node.cost
    if cost is None:
        return 0.0
    base = (cost.avg_handling_seconds / 3600.0) * cost.labor_cost_per_hour
    return (base + cost.fixed_cost) * (1.0 + cost.rework_rate)


def process_cost(graph: ProcessGraph) -> CostReport:
    """Roll a process's node costs into per-case and annual totals."""
    node_costs = {n.id: round(node_cost(n), 4) for n in graph.nodes}
    per_case = round(sum(node_costs.values()), 4)
    annual = (
        round(per_case * graph.annual_case_volume, 2)
        if graph.annual_case_volume
        else None
    )
    return CostReport(
        process_id=graph.id,
        currency=graph.currency,
        per_case_cost=per_case,
        annual_cost=annual,
        node_costs=node_costs,
        costed_nodes=sum(1 for n in graph.nodes if n.cost is not None),
        total_nodes=len(graph.nodes),
    )


def estimate_savings(
    graph: ProcessGraph, finding: StructuralFinding
) -> MoneyImpact | None:
    """Quantify the cost saving a finding's fix would yield, or None.

    Returns ``None`` when no cost data backs the affected nodes, so a proposal
    never claims savings it cannot justify.
    """
    by_id = {n.id: n for n in graph.nodes}
    nodes = [by_id[nid] for nid in finding.node_ids if nid in by_id]
    if not nodes:
        return None

    per_case, basis = _saving_per_case(finding.kind, nodes)
    if per_case <= 0:
        return None
    return _to_impact(graph, per_case, basis)


def _saving_per_case(
    kind: StructuralFindingKind, nodes: list[ProcessNode]
) -> tuple[float, str]:
    """Compute the per-case saving and a human-readable basis for a finding."""
    if kind is StructuralFindingKind.SEQUENTIAL_APPROVALS:
        costs = sorted((node_cost(n) for n in nodes), reverse=True)
        # Consolidate to a single approval: the cheapest N-1 steps are removed.
        return sum(costs[1:]), "consolidating stacked approvals to one step"
    if kind is StructuralFindingKind.REWORK_LOOP:
        removable = 0.0
        for n in nodes:
            if n.cost is None:
                continue
            base = (n.cost.avg_handling_seconds / 3600.0) * n.cost.labor_cost_per_hour
            removable += (base + n.cost.fixed_cost) * n.cost.rework_rate
        return removable * _REWORK_REMOVAL_FACTOR, "halving rework on the loop"
    # Other kinds (long chains, convergence, orphans) save time, not cost.
    return 0.0, ""


def _to_impact(graph: ProcessGraph, per_case: float, basis: str) -> MoneyImpact:
    """Scale a per-case saving to annual when case volume is known."""
    if graph.annual_case_volume:
        return MoneyImpact(
            amount=round(per_case * graph.annual_case_volume, 2),
            currency=graph.currency,
            period="annual",
            basis=f"{basis}; × {graph.annual_case_volume:g} cases/yr",
        )
    return MoneyImpact(
        amount=round(per_case, 2),
        currency=graph.currency,
        period="per_case",
        basis=basis,
    )


__all__ = ["CostReport", "node_cost", "process_cost", "estimate_savings"]
