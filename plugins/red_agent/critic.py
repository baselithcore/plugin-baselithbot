"""Step critic — guards every planner-proposed scan step.

The planner proposes the next ``PlannerStep`` (which scanners to run on
which target). The critic is the second voice in the loop: it inspects
the proposal against the active engagement's RoE and the chain history
and either approves it, rewrites it, or vetoes it. Veto stops the
chain — approval lets the orchestrator execute the step.

Why a separate object: keeping scope/exclusion/redundancy enforcement
inside the planner couples planning strategy to safety policy. As we
add LLM-driven planners, the same critic must vet *any* proposed step
without trusting the planner. Defense in depth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol
from urllib.parse import urlparse

from core.observability.logging import get_logger
from plugins.red_agent.models import (
    ScanIntensity,
    Target,
    TargetType,
    intensity_rank,
)
from plugins.red_agent.planner import PlannerStep
from plugins.red_agent.rules_of_engagement import _matches_any

logger = get_logger(__name__)


@dataclass
class CriticContext:
    """Per-scan view that critics consult on every step.

    ``extra_scope``/``excluded_targets`` come from the active
    engagement; ``max_intensity`` is the post-RoE ceiling; ``executed``
    is the set of (scanner, target_value) pairs already run in this
    chain — used to suppress redundant re-runs when the planner re-
    proposes the same combo.
    """

    extra_scope: list[str] = field(default_factory=list)
    excluded_targets: list[str] = field(default_factory=list)
    max_intensity: ScanIntensity = ScanIntensity.INTRUSIVE
    executed: set[tuple[str, str]] = field(default_factory=set)
    bug_bounty_mode: bool = False
    global_scope: list[str] = field(default_factory=list)


@dataclass
class StepReview:
    """Outcome of a critic call.

    ``approved=False`` halts the chain. ``amended_step`` lets the
    critic rewrite a proposal in-place — for example, to drop scanners
    that were already executed against the same target without aborting
    the rest of the step.
    """

    approved: bool
    reason: str = ""
    amended_step: PlannerStep | None = None


class StepCritic(Protocol):
    def review(self, step: PlannerStep, ctx: CriticContext) -> StepReview: ...


class RoECritic:
    """Reject steps that would break the active engagement RoE.

    The engagement evaluation already capped the *initial* request, but
    multi-step planners derive new targets from findings (e.g. DAST
    against a discovered endpoint). Those derived targets must be re-
    checked here against scope, exclusions, and the intensity ceiling.
    """

    def review(self, step: PlannerStep, ctx: CriticContext) -> StepReview:
        host = _extract_host(step.target)
        if host is None:
            return StepReview(False, reason="step target has no resolvable host")

        if ctx.excluded_targets and _matches_any(host, ctx.excluded_targets):
            return StepReview(
                False,
                reason=f"derived target {host!r} is in engagement.excluded_targets",
            )

        if not _allowed_in_scope(
            host,
            extra_scope=ctx.extra_scope,
            global_scope=ctx.global_scope,
            bug_bounty_mode=ctx.bug_bounty_mode,
        ):
            return StepReview(
                False,
                reason=f"derived target {host!r} not in any active scope_allowlist",
            )

        if intensity_rank(step.intensity) > intensity_rank(ctx.max_intensity):
            return StepReview(
                False,
                reason=(
                    f"step intensity {step.intensity.value} exceeds "
                    f"ceiling {ctx.max_intensity.value}"
                ),
            )
        return StepReview(True)


class RedundancyCritic:
    """Drop scanners that already ran against the same target value.

    Lets the chain keep advancing on novel work even when the planner
    re-proposes a partial overlap, instead of stopping the entire chain
    because of a single duplicate. Returns a veto only when *every*
    scanner in the step is a repeat.
    """

    def review(self, step: PlannerStep, ctx: CriticContext) -> StepReview:
        target_value = step.target.value
        novel = [
            scanner
            for scanner in step.scanners
            if (scanner, target_value) not in ctx.executed
        ]
        if not novel:
            return StepReview(
                False,
                reason=(
                    f"all scanners {step.scanners} already executed against "
                    f"{target_value!r}"
                ),
            )
        if novel == list(step.scanners):
            return StepReview(True)
        amended = PlannerStep(
            scanners=novel,
            target=step.target,
            intensity=step.intensity,
            rationale=step.rationale + " (redundant scanners pruned)",
            derived_from=list(step.derived_from),
        )
        return StepReview(
            True, reason="redundant scanners dropped", amended_step=amended
        )


class CompositeCritic:
    """Run critics in order; first veto wins, amendments compose."""

    def __init__(self, critics: Iterable[StepCritic]) -> None:
        self.critics = list(critics)

    def review(self, step: PlannerStep, ctx: CriticContext) -> StepReview:
        current = step
        amendments: list[str] = []
        for critic in self.critics:
            review = critic.review(current, ctx)
            if not review.approved:
                return review
            if review.amended_step is not None:
                current = review.amended_step
                if review.reason:
                    amendments.append(review.reason)
        if current is step:
            return StepReview(True)
        return StepReview(
            True,
            reason="; ".join(amendments) if amendments else "amended",
            amended_step=current,
        )


def default_critic() -> CompositeCritic:
    """Critic stack the agent installs by default."""
    return CompositeCritic([RoECritic(), RedundancyCritic()])


def _extract_host(target: Target) -> str | None:
    if target.type == TargetType.URL:
        return urlparse(target.value).hostname
    return target.value


def _allowed_in_scope(
    host: str,
    *,
    extra_scope: Iterable[str],
    global_scope: Iterable[str],
    bug_bounty_mode: bool,
) -> bool:
    if bug_bounty_mode:
        return True
    candidates = [*extra_scope, *global_scope]
    if not candidates:
        # No engagement-specific scope and no global scope means
        # the original guardrails would already have rejected; but
        # since RoE may have been silent (no engagement), we don't
        # second-guess here — reject only when there *is* a scope
        # to compare against.
        return True
    return _matches_any(host, list(candidates))


__all__ = [
    "CompositeCritic",
    "CriticContext",
    "RedundancyCritic",
    "RoECritic",
    "StepCritic",
    "StepReview",
    "default_critic",
]
