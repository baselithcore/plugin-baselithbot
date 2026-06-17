"""Executive report rendering (pure, dependency-free).

Renders a process's current state — structure, cost, predicted cycle time, KPI
snapshots, bottlenecks, and proposal pipeline — as a Markdown brief or a flat
CSV, with no third-party libraries (so it ships without extra wheels and can be
scheduled later via core cron). Pure functions over already-fetched data.
"""

from __future__ import annotations

import csv
import io

from .cost import CostReport
from .models import Bottleneck, KpiSnapshot, OptimizationProposal, ProcessGraph
from .simulation import SimulationResult


def _fmt_secs(seconds: float) -> str:
    if seconds >= 3600:
        return f"{seconds / 3600:.1f} h"
    if seconds >= 60:
        return f"{seconds / 60:.1f} min"
    return f"{seconds:.0f} s"


def build_markdown(
    process: ProcessGraph,
    snapshots: list[KpiSnapshot],
    bottlenecks: list[Bottleneck],
    cost: CostReport,
    simulation: SimulationResult,
    proposals: list[OptimizationProposal],
) -> str:
    """Render an executive Markdown brief for a process."""
    lines: list[str] = [
        f"# Process report — {process.name}",
        "",
        f"- Process id: `{process.id}`",
        f"- Steps: {len(process.nodes)} · Transitions: {len(process.edges)} · "
        f"KPIs: {len(process.kpis)}",
        f"- Currency: {process.currency}"
        + (
            f" · Annual volume: {process.annual_case_volume:g}"
            if process.annual_case_volume
            else ""
        ),
        "",
        "## Efficiency",
        f"- Cost / case: {cost.per_case_cost} {cost.currency} "
        f"({cost.costed_nodes}/{cost.total_nodes} steps costed)",
    ]
    if cost.annual_cost is not None:
        lines.append(f"- Annual cost: {cost.annual_cost} {cost.currency}")
    if simulation.cycle_time_seconds > 0:
        lines.append(
            f"- Predicted cycle time: {_fmt_secs(simulation.cycle_time_seconds)}"
        )
    if simulation.bottleneck_node:
        lines.append(f"- Critical bottleneck step: `{simulation.bottleneck_node}`")

    lines += ["", "## KPI snapshots"]
    if snapshots:
        lines.append("| KPI | Value | Target | Breaching |")
        lines.append("|-----|-------|--------|-----------|")
        for snap in snapshots:
            target = "—" if snap.target is None else f"{snap.target:g}"
            flag = "⚠️ yes" if snap.breaching else "ok"
            lines.append(f"| {snap.kpi_id} | {snap.value:g} | {target} | {flag} |")
    else:
        lines.append("_No KPI metrics ingested yet._")

    lines += ["", "## Bottlenecks"]
    if bottlenecks:
        for b in bottlenecks:
            where = f" @ `{b.node_id}`" if b.node_id else ""
            lines.append(f"- **{b.severity.value}**{where}: {b.detail}")
    else:
        lines.append("_None detected._")

    lines += ["", "## Optimization pipeline"]
    by_status: dict[str, int] = {}
    for p in proposals:
        by_status[p.status.value] = by_status.get(p.status.value, 0) + 1
    if proposals:
        lines.append(
            "- " + " · ".join(f"{k}: {v}" for k, v in sorted(by_status.items()))
        )
        for p in proposals[:10]:
            saving = ""
            if p.estimated_savings:
                saving = (
                    f" — ~{p.estimated_savings.amount:g} "
                    f"{p.estimated_savings.currency}/{p.estimated_savings.period}"
                )
            lines.append(f"  - [{p.status.value}] {p.title}{saving}")
    else:
        lines.append("_No proposals generated._")

    lines.append("")
    return "\n".join(lines)


def build_csv(
    process: ProcessGraph,
    snapshots: list[KpiSnapshot],
    bottlenecks: list[Bottleneck],
    cost: CostReport,
    simulation: SimulationResult,
    proposals: list[OptimizationProposal],
) -> str:
    """Render a flat ``section,metric,value`` CSV for spreadsheet import."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["section", "metric", "value"])
    writer.writerow(["overview", "process_id", process.id])
    writer.writerow(["overview", "steps", len(process.nodes)])
    writer.writerow(["overview", "transitions", len(process.edges)])
    writer.writerow(["overview", "kpis", len(process.kpis)])
    writer.writerow(["cost", "per_case", cost.per_case_cost])
    writer.writerow(["cost", "annual", cost.annual_cost if cost.annual_cost else ""])
    writer.writerow(["cost", "currency", cost.currency])
    writer.writerow(["simulation", "cycle_time_seconds", simulation.cycle_time_seconds])
    writer.writerow(["simulation", "bottleneck_node", simulation.bottleneck_node or ""])
    writer.writerow(["pipeline", "proposals", len(proposals)])
    writer.writerow(["pipeline", "bottlenecks", len(bottlenecks)])
    for snap in snapshots:
        writer.writerow(["kpi", snap.kpi_id, snap.value])
        writer.writerow(["kpi_breaching", snap.kpi_id, "1" if snap.breaching else "0"])
    return buffer.getvalue()


__all__ = ["build_markdown", "build_csv"]
