"""
Attack planner protocol — pluggable strategy that decides what to run
next given the current state of a scan and the findings observed so far.

The default `DeterministicPlanner` runs the operator-supplied scanner
list once. The intended upgrade is `LLMReasoningPlanner` (injected via
DI): given the partial attack-surface graph + new findings, an LLM
returns the next scanners to run and (optionally) narrows their target
list to discovered endpoints.

By making this a Protocol, callers can swap planners without touching
the orchestrator. Multi-step attack chains emerge naturally: the
orchestrator loops `plan_next_step → run scanners → ingest findings`
until the planner returns an empty list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from plugins.red_agent.models import Finding, ScanIntensity, Target


@dataclass
class PlannerStep:
    """A single step in an attack chain."""

    scanners: list[str]
    target: Target
    intensity: ScanIntensity
    rationale: str = ""
    derived_from: list[str] = field(default_factory=list)


@dataclass
class PlannerState:
    """Mutable state carried across planning iterations."""

    initial_target: Target
    intensity: ScanIntensity
    requested_scanners: list[str]
    iterations: int = 0
    seen_endpoints: set[str] = field(default_factory=set)
    seen_services: set[str] = field(default_factory=set)
    seen_findings: list[Finding] = field(default_factory=list)
    scan_id: UUID | None = None
    autonomy_max_intensity: ScanIntensity | None = None


class AttackPlanner(Protocol):
    """Decide the next step (or stop). Stateless across instances."""

    async def plan(
        self, state: PlannerState, new_findings: list[Finding]
    ) -> PlannerStep | None: ...


class DeterministicPlanner:
    """Runs the operator-supplied scanner list once, then stops.

    Backwards-compatible default. Multi-step chaining only kicks in when
    a smarter planner (LLM-driven, graph-aware) replaces this.
    """

    async def plan(
        self, state: PlannerState, new_findings: list[Finding]
    ) -> PlannerStep | None:
        del new_findings
        if state.iterations >= 1:
            return None
        return PlannerStep(
            scanners=list(state.requested_scanners),
            target=state.initial_target,
            intensity=state.intensity,
            rationale="initial scanner list (deterministic planner)",
        )


class ChainingPlanner:
    """Run the full requested scanner set on the initial target, then
    re-run DAST scanners against any new endpoints discovered, up to
    ``max_iterations``.

    Step 1: run **all** requested scanners on the initial target — recon
            and DAST — so the operator's intent is honored on iter 0
            even when recon yields no fresh endpoints (PASSIVE nmap is
            a ping sweep that produces no URL endpoints to chain on).
    Step 2: collect new endpoints from iter 0 findings.
    Step 3: re-run DAST scanners against each newly discovered endpoint.
    Step 4: stop after ``max_iterations`` or when no new endpoints surface.

    This is still rule-driven, not LLM-driven, but it produces real
    multi-step chains and lays the groundwork for the reasoning planner
    to slot in: the orchestrator loop is unchanged, only the ``.plan()``
    body differs.
    """

    def __init__(self, max_iterations: int = 3) -> None:
        self.max_iterations = max_iterations

    async def plan(
        self, state: PlannerState, new_findings: list[Finding]
    ) -> PlannerStep | None:
        if state.iterations >= self.max_iterations:
            return None

        dast_set = {"nuclei", "zap"}
        if state.iterations == 0:
            scanners = list(state.requested_scanners) or ["nmap"]
            return PlannerStep(
                scanners=scanners,
                target=state.initial_target,
                intensity=state.intensity,
                rationale="iteration 0: full requested scanner set",
            )

        # Subsequent iterations — collect new endpoints from new_findings,
        # then queue DAST scanners against each.
        new_endpoints = sorted(
            {
                f.endpoint
                for f in new_findings
                if f.endpoint and f.endpoint not in state.seen_endpoints
            }
        )
        if not new_endpoints:
            return None

        dast_in_request = [s for s in state.requested_scanners if s in dast_set]
        if not dast_in_request:
            return None

        # Aim DAST at the first newly-discovered endpoint each iteration to
        # keep the chain bounded; remaining endpoints get picked up in the
        # next iteration (until max_iterations).
        target_url = new_endpoints[0]
        from plugins.red_agent.models import TargetType

        return PlannerStep(
            scanners=dast_in_request,
            target=Target(type=TargetType.URL, value=target_url),
            intensity=state.intensity,
            rationale=f"iteration {state.iterations}: DAST on discovered {target_url}",
            derived_from=[str(f.id) for f in new_findings if f.endpoint == target_url],
        )
