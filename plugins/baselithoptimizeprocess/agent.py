"""The BOP optimizer agent.

Turns observed bottlenecks into human-in-the-loop optimization proposals. The
agent is LLM-driven but *defensive*: any provider/parse failure degrades to a
deterministic heuristic so the plugin keeps working offline or on a weak model —
it never raises into the request path. It implements the framework's agent
contract (``execute``) plus a typed :meth:`propose` entry point used by the
service layer.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from core.observability.logging import get_logger

from .models import (
    Bottleneck,
    OptimizationProposal,
    ProcessGraph,
    ProposalStatus,
)
from .cost import estimate_savings
from .prompts import OPTIMIZER_SYSTEM_PROMPT, build_optimization_prompt
from .structural import StructuralFinding, analyze_structure

logger = get_logger(__name__)


class BopOptimizerAgent:
    """Generates scoped, advisory optimization proposals for a process.

    Args:
        service: Optional LLM service exposing
            ``async generate_response(prompt, *, json, system_prompt) -> str``.
            When None, the agent lazily resolves the core LLM service and, if
            that is unavailable, falls back to heuristic proposals.
    """

    name = "bop-optimizer-agent"

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def execute(self, input: str, context: dict[str, Any] | None = None) -> str:
        """Agent-contract entry point: summarise an optimization pass as text.

        Args:
            input: Free-text operator instruction/context for the pass.
            context: Must carry ``process`` (a :class:`ProcessGraph`) and
                ``bottlenecks`` (list of :class:`Bottleneck`); without them the
                agent has nothing to reason over and returns a notice.

        Returns:
            A short human-readable summary of the generated proposals.
        """
        context = context or {}
        process = context.get("process")
        bottlenecks = context.get("bottlenecks", [])
        if not isinstance(process, ProcessGraph):
            return "No process supplied; nothing to optimize."
        proposals = await self.propose(process, bottlenecks, input, max_proposals=5)
        if not proposals:
            return f"Process '{process.name}' is within target; no proposals."
        lines = [f"{len(proposals)} proposal(s) for '{process.name}':"]
        lines += [f"  - {p.title} (confidence {p.confidence:.2f})" for p in proposals]
        return "\n".join(lines)

    async def propose(
        self,
        process: ProcessGraph,
        bottlenecks: list[Bottleneck],
        extra_context: str = "",
        max_proposals: int = 5,
    ) -> list[OptimizationProposal]:
        """Produce optimization proposals for a process.

        Considers both metric-driven bottlenecks and metric-free structural
        findings (rework loops, long chains, stacked approvals, …) derived from
        the process graph — so a freshly mapped process with no ingested metrics
        still yields useful proposals. Tries the LLM first; on any failure (no
        provider, bad JSON) it degrades to a deterministic heuristic. All
        proposals come back in ``PROPOSED`` status — never auto-applied.
        """
        structural = analyze_structure(process)
        prompt = build_optimization_prompt(
            process, bottlenecks, structural, extra_context, max_proposals
        )
        raw = await self._generate(prompt)
        if raw is not None:
            parsed = self._parse(raw, process.id, max_proposals)
            if parsed:
                return parsed
        return self._heuristic(process, bottlenecks, structural, max_proposals)

    async def _generate(self, prompt: str) -> str | None:
        """Call the LLM service, returning raw text or None on any failure."""
        service = self._service or self._resolve_service()
        if service is None:
            return None
        try:
            return await service.generate_response(
                prompt, json=True, system_prompt=OPTIMIZER_SYSTEM_PROMPT
            )
        except Exception as exc:  # noqa: BLE001 - degrade, never crash the request
            logger.warning("bop_llm_unavailable", error=str(exc))
            return None

    def _resolve_service(self) -> Any:
        """Lazily resolve and cache the core LLM service; None if unavailable."""
        try:
            from core.services.llm import get_llm_service

            self._service = get_llm_service()
        except Exception as exc:  # noqa: BLE001 - optional dependency / config
            logger.info("bop_llm_resolve_failed", error=str(exc))
            self._service = None
        return self._service

    def _parse(
        self, raw: str, process_id: str, max_proposals: int
    ) -> list[OptimizationProposal] | None:
        """Parse model JSON into proposals; None on malformed output."""
        try:
            block = raw[raw.index("{") : raw.rindex("}") + 1]
            data = json.loads(block)
        except (ValueError, json.JSONDecodeError):
            return None
        items = data.get("proposals")
        if not isinstance(items, list):
            return None
        proposals: list[OptimizationProposal] = []
        for item in items[:max_proposals]:
            proposal = self._coerce(item, process_id)
            if proposal is not None:
                proposals.append(proposal)
        return proposals

    def _coerce(self, item: Any, process_id: str) -> OptimizationProposal | None:
        """Best-effort map one model object onto a validated proposal."""
        if not isinstance(item, dict) or not item.get("title"):
            return None
        confidence = item.get("confidence", 0.5)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.5
        return OptimizationProposal(
            id=uuid.uuid4().hex,
            process_id=process_id,
            title=str(item["title"]),
            rationale=str(item.get("rationale", "")),
            target_nodes=[str(n) for n in item.get("target_nodes", []) or []],
            addresses_kpis=[str(k) for k in item.get("addresses_kpis", []) or []],
            expected_impact=str(item.get("expected_impact", "")),
            confidence=confidence,
            status=ProposalStatus.PROPOSED,
        )

    def _heuristic(
        self,
        process: ProcessGraph,
        bottlenecks: list[Bottleneck],
        structural: list[StructuralFinding],
        max_proposals: int,
    ) -> list[OptimizationProposal]:
        """Deterministic fallback used when no LLM is available.

        Metric-driven bottleneck proposals come first (higher confidence), then
        structural-finding proposals fill the remaining slots, so the optimizer
        is useful both with and without ingested metrics. All ordered by
        severity, capped at ``max_proposals``.
        """
        ranked = sorted(
            bottlenecks,
            key=lambda b: _SEVERITY_RANK.get(b.severity.value, 0),
            reverse=True,
        )
        proposals: list[OptimizationProposal] = []
        for bottleneck in ranked:
            where = bottleneck.node_id or "the affected stage"
            proposals.append(
                OptimizationProposal(
                    id=uuid.uuid4().hex,
                    process_id=process.id,
                    title=f"Relieve {bottleneck.severity.value} bottleneck at {where}",
                    rationale=bottleneck.detail
                    or f"KPI '{bottleneck.kpi_id}' is breaching its target.",
                    target_nodes=[bottleneck.node_id] if bottleneck.node_id else [],
                    addresses_kpis=[bottleneck.kpi_id],
                    expected_impact="Reduce the observed breach toward target.",
                    confidence=0.35,
                    status=ProposalStatus.PROPOSED,
                )
            )
        for finding in structural:
            if len(proposals) >= max_proposals:
                break
            savings = estimate_savings(process, finding)
            impact = (
                finding.suggestion or "Improve process structure to cut cycle time."
            )
            if savings is not None:
                impact = (
                    f"~{savings.amount:g} {savings.currency}/{savings.period} "
                    f"({savings.basis})"
                )
            proposals.append(
                OptimizationProposal(
                    id=uuid.uuid4().hex,
                    process_id=process.id,
                    title=finding.title,
                    rationale=finding.detail,
                    target_nodes=list(finding.node_ids),
                    addresses_kpis=[],
                    expected_impact=impact,
                    confidence=0.3,
                    estimated_savings=savings,
                    status=ProposalStatus.PROPOSED,
                )
            )
        return proposals[:max_proposals]


_SEVERITY_RANK: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


__all__ = ["BopOptimizerAgent"]
