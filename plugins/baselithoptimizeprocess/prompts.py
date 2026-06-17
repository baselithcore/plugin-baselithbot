"""Prompt construction for the BOP optimizer agent.

Pure string assembly (no I/O), so prompts are unit-testable and the agent stays
a thin orchestration layer. The system prompt fixes the optimizer's contract:
ground every suggestion in the supplied KPIs and detected bottlenecks, stay
advisory (never claim to have applied a change), and emit strict JSON.
"""

from __future__ import annotations

import json

from .cost import node_cost
from .models import Bottleneck, KpiDefinition, ProcessGraph
from .structural import StructuralFinding

OPTIMIZER_SYSTEM_PROMPT = """You are the BaselithCore Process Optimizer.

You analyse a business process — its execution graph, its user-defined KPIs, the
bottlenecks detected from live metrics, and structural findings derived from the
process design itself — and propose concrete, scoped improvements. You operate in
SUGGEST-ONLY mode: you never apply changes, you only recommend them for human
review.

Rules:
  - Ground every proposal in a specific bottleneck, KPI, or structural finding.
    Never invent metrics or targets that were not provided.
  - When no live metrics exist yet, reason from the structural findings and the
    graph topology (rework loops, long sequential chains, hand-off convergence,
    stacked approvals) to recommend design improvements.
  - Prefer the smallest change that addresses the largest inefficiency.
  - Reference real node ids and KPI ids from the input.
  - Be honest about uncertainty via the confidence field.

Respond with STRICT JSON only — no markdown fences, no commentary."""


def build_optimization_prompt(
    process: ProcessGraph,
    bottlenecks: list[Bottleneck],
    structural: list[StructuralFinding],
    extra_context: str,
    max_proposals: int,
) -> str:
    """Render the user prompt for an optimization pass.

    Args:
        process: The process under analysis.
        bottlenecks: Bottlenecks detected from current metrics.
        extra_context: Optional free-text operator hints.
        max_proposals: Upper bound on proposals to emit.

    Returns:
        A fully rendered prompt instructing the model to emit proposal JSON.
    """
    payload = {
        "process": {
            "id": process.id,
            "name": process.name,
            "description": process.description,
            "currency": process.currency,
            "annual_case_volume": process.annual_case_volume,
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "kind": n.kind.value,
                    "role": n.role,
                    "cost_per_case": round(node_cost(n), 2) if n.cost else None,
                }
                for n in process.nodes
            ],
            "edges": [
                {"source": e.source, "target": e.target, "condition": e.condition}
                for e in process.edges
            ],
            "kpis": [_kpi_brief(k) for k in process.kpis],
        },
        "bottlenecks": [
            {
                "kpi_id": b.kpi_id,
                "node_id": b.node_id,
                "severity": b.severity.value,
                "observed": b.observed,
                "target": b.target,
                "detail": b.detail,
            }
            for b in bottlenecks
        ],
        "structural_findings": [
            {
                "kind": f.kind.value,
                "severity": f.severity.value,
                "node_ids": f.node_ids,
                "detail": f.detail,
                "suggestion": f.suggestion,
            }
            for f in structural
        ],
        "operator_context": extra_context or "(none)",
    }
    return f"""Analyse this process and propose up to {max_proposals} optimizations.

INPUT (authoritative — do not contradict):
{json.dumps(payload, indent=2)}

Emit a JSON object with exactly this shape:
{{
  "proposals": [
    {{
      "title": "<short imperative summary>",
      "rationale": "<why it helps, referencing the bottleneck/KPI>",
      "target_nodes": ["<node id>", ...],
      "addresses_kpis": ["<kpi id>", ...],
      "expected_impact": "<concrete expected effect>",
      "confidence": <float 0.0-1.0>
    }}
  ]
}}

Order proposals by expected impact, highest first. If no improvement is
warranted, return an empty proposals list. Output JSON only."""


def _kpi_brief(kpi: KpiDefinition) -> dict[str, object]:
    """Compact KPI projection for prompt embedding."""
    return {
        "id": kpi.id,
        "name": kpi.name,
        "unit": kpi.unit,
        "direction": kpi.direction.value,
        "target": kpi.target,
    }


__all__ = ["OPTIMIZER_SYSTEM_PROMPT", "build_optimization_prompt"]
