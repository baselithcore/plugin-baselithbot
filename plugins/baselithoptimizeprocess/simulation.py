"""What-if simulation of a process graph (analytical, metric-free).

Predicts a process's expected **cycle time** and **cost per case** straight from
its topology + per-step economics, so an operator can compare a proposed redesign
against the live model *before* applying anything — the difference between an
advisory tool and a true efficiency tool.

The model is deliberately simple, deterministic, and explainable (every result
carries an ``assumptions`` note):

* effective step time = ``avg_handling_seconds × (1 + rework_rate)`` (rework
  inflates time, mirroring the cost model);
* **cycle time** = the critical path (longest path by effective time) over the
  graph's DAG — parallel branches overlap, so the slowest branch dominates;
* **cost per case** = Σ ``node_cost(n) × reach_probability(n)`` where DECISION
  steps split probability equally across their branches and all other steps pass
  full probability to each successor (parallel branches both incur cost).

Cycles (rework loops) are handled by dropping back-edges for path/probability
computation; their cost/time effect is already captured by ``rework_rate``.
Everything here is pure and side-effect-free.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .cost import node_cost
from .models import NodeKind, ProcessGraph, ProcessNode


class SimulationResult(BaseModel):
    """Predicted economics of a single process graph."""

    process_id: str
    cycle_time_seconds: float = 0.0
    cost_per_case: float = 0.0
    currency: str = "EUR"
    annual_cost: float | None = None
    bottleneck_node: str | None = None
    critical_path: list[str] = Field(default_factory=list)
    assumptions: str = ""


class SimulationComparison(BaseModel):
    """Baseline-vs-variant what-if comparison with signed deltas.

    Deltas are ``variant - baseline``: negative means the variant is cheaper /
    faster (an improvement).
    """

    baseline: SimulationResult
    variant: SimulationResult
    cycle_time_delta_seconds: float = 0.0
    cost_per_case_delta: float = 0.0
    annual_cost_delta: float | None = None
    cycle_time_pct: float = 0.0
    cost_pct: float = 0.0


def _effective_time(node: ProcessNode) -> float:
    """Rework-inflated handling time of a step (seconds)."""
    cost = node.cost
    if cost is None:
        return 0.0
    return cost.avg_handling_seconds * (1.0 + cost.rework_rate)


def _dag_order(
    node_ids: list[str], out_adj: dict[str, list[str]]
) -> tuple[list[str], set[tuple[str, str]]]:
    """Return a topological order and the set of back-edges (cycle breakers)."""
    white, grey, black = 0, 1, 2
    color = {n: white for n in node_ids}
    order: list[str] = []
    back: set[tuple[str, str]] = set()

    def visit(root: str) -> None:
        stack = [(root, iter(out_adj[root]))]
        color[root] = grey
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color[nxt] == grey:
                    back.add((node, nxt))
                elif color[nxt] == white:
                    color[nxt] = grey
                    stack.append((nxt, iter(out_adj[nxt])))
                    advanced = True
                    break
            if not advanced:
                color[node] = black
                order.append(node)
                stack.pop()

    for n in node_ids:
        if color[n] == white:
            visit(n)
    order.reverse()
    return order, back


def simulate(graph: ProcessGraph) -> SimulationResult:
    """Predict cycle time and cost-per-case for a process graph."""
    nodes = graph.nodes
    if not nodes:
        return SimulationResult(process_id=graph.id, currency=graph.currency)

    node_ids = [n.id for n in nodes]
    by_id = {n.id: n for n in nodes}
    out_adj: dict[str, list[str]] = {n: [] for n in node_ids}
    for edge in graph.edges:
        if edge.source in out_adj and edge.target in by_id:
            out_adj[edge.source].append(edge.target)

    order, back = _dag_order(node_ids, out_adj)
    fwd_out = {n: [t for t in out_adj[n] if (n, t) not in back] for n in node_ids}
    fwd_in: dict[str, list[str]] = {n: [] for n in node_ids}
    for src in node_ids:
        for tgt in fwd_out[src]:
            fwd_in[tgt].append(src)

    eff = {n: _effective_time(by_id[n]) for n in node_ids}
    prob = _reach_probability(order, by_id, fwd_in, fwd_out)
    finish, crit_end = _critical_path(order, eff, fwd_in)

    cost_per_case = round(sum(node_cost(by_id[n]) * prob[n] for n in node_ids), 4)
    cycle = round(finish.get(crit_end, 0.0), 2) if crit_end else 0.0
    path = _trace_path(crit_end, finish, fwd_in)
    bottleneck = max(path, key=lambda n: eff[n], default=None) if path else None
    annual = (
        round(cost_per_case * graph.annual_case_volume, 2)
        if graph.annual_case_volume
        else None
    )
    return SimulationResult(
        process_id=graph.id,
        cycle_time_seconds=cycle,
        cost_per_case=cost_per_case,
        currency=graph.currency,
        annual_cost=annual,
        bottleneck_node=bottleneck,
        critical_path=path,
        assumptions=(
            "critical-path cycle time (parallel overlaps); cost is "
            "probability-weighted (decisions split equally); rework inflates "
            "step time/cost"
        ),
    )


def _reach_probability(
    order: list[str],
    by_id: dict[str, ProcessNode],
    fwd_in: dict[str, list[str]],
    fwd_out: dict[str, list[str]],
) -> dict[str, float]:
    """Probability a case reaches each node, propagated start→end."""
    starts = [n for n in order if not fwd_in[n]]
    prob = {n: 0.0 for n in order}
    seed = 1.0 / len(starts) if starts else 0.0
    for s in starts:
        prob[s] = seed
    for node in order:
        # Cap at 1: a step executes at most once per case, so a parallel join
        # that accumulates probability from several branches is counted once.
        prob[node] = min(1.0, prob[node])
        succ = fwd_out[node]
        if not succ:
            continue
        is_decision = by_id[node].kind is NodeKind.DECISION
        share = prob[node] / len(succ) if is_decision else prob[node]
        for nxt in succ:
            prob[nxt] += share
    return prob


def _critical_path(
    order: list[str], eff: dict[str, float], fwd_in: dict[str, list[str]]
) -> tuple[dict[str, float], str | None]:
    """Longest-path finish times; return them plus the latest-finishing node."""
    finish: dict[str, float] = {}
    for node in order:
        preds = fwd_in[node]
        base = max((finish[p] for p in preds), default=0.0)
        finish[node] = base + eff[node]
    crit_end = max(finish, key=lambda n: finish[n]) if finish else None
    return finish, crit_end


def _trace_path(
    end: str | None,
    finish: dict[str, float],
    fwd_in: dict[str, list[str]],
) -> list[str]:
    """Reconstruct the critical path backwards from the latest node."""
    if end is None:
        return []
    path = [end]
    cur = end
    while fwd_in[cur]:
        prev = max(fwd_in[cur], key=lambda p: finish.get(p, 0.0))
        path.append(prev)
        cur = prev
    path.reverse()
    return path


def compare(baseline: ProcessGraph, variant: ProcessGraph) -> SimulationComparison:
    """Run both graphs and return signed deltas (variant − baseline)."""
    base = simulate(baseline)
    var = simulate(variant)
    return SimulationComparison(
        baseline=base,
        variant=var,
        cycle_time_delta_seconds=round(
            var.cycle_time_seconds - base.cycle_time_seconds, 2
        ),
        cost_per_case_delta=round(var.cost_per_case - base.cost_per_case, 4),
        annual_cost_delta=_opt_delta(var.annual_cost, base.annual_cost),
        cycle_time_pct=_pct(base.cycle_time_seconds, var.cycle_time_seconds),
        cost_pct=_pct(base.cost_per_case, var.cost_per_case),
    )


def _opt_delta(variant: float | None, baseline: float | None) -> float | None:
    """Delta of two optional amounts, or None when either is missing."""
    if variant is None or baseline is None:
        return None
    return round(variant - baseline, 2)


def _pct(baseline: float, variant: float) -> float:
    """Signed percentage change from baseline to variant (0 when no baseline)."""
    if baseline <= 0:
        return 0.0
    return round((variant - baseline) / baseline * 100.0, 1)


__all__ = ["SimulationResult", "SimulationComparison", "simulate", "compare"]
