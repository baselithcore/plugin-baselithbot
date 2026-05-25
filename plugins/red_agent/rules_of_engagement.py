"""Rules of Engagement engine.

Enforces a per-engagement scope contract on every scan request before
the static guardrails run:

* exclusions  — targets in ``rules.excluded_targets`` are hard-rejected
  regardless of the global allowlist.
* scope merge — engagement ``scope_allowlist`` augments the global one
  for the duration of the request.
* intensity cap — request intensity is downgraded to
  ``rules.max_intensity`` and audited.
* autonomy — execution intent must fit the engagement's autonomy
  level (Observe / Plan / Recommend / Execute*).
* HITL — engagements with ``require_human_approval`` always force
  human approval, even on passive scans.

This is the missing link between the engagement record and the rest
of the pipeline: without it, ``engagement_id`` would be a pure label.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from urllib.parse import urlparse

from core.observability.logging import get_logger
from plugins.red_agent.guardrails import GuardrailViolation
from plugins.red_agent.models import (
    AutonomyLevel,
    EngagementRecord,
    RulesOfEngagement,
    ScanIntensity,
    ScanRequest,
    Target,
    TargetType,
    intensity_rank,
)
from plugins.red_agent.persistence import EngagementPersistence

logger = get_logger(__name__)


_AUTONOMY_MAX_INTENSITY: dict[AutonomyLevel, ScanIntensity | None] = {
    AutonomyLevel.OBSERVE: None,
    AutonomyLevel.PLAN: None,
    AutonomyLevel.RECOMMEND: None,
    AutonomyLevel.EXECUTE_PASSIVE: ScanIntensity.PASSIVE,
    AutonomyLevel.EXECUTE_ACTIVE: ScanIntensity.ACTIVE,
    AutonomyLevel.EXECUTE_INTRUSIVE: ScanIntensity.INTRUSIVE,
}


@dataclass
class RoEDecision:
    """Result of evaluating a scan request against an engagement.

    ``effective_request`` may have a downgraded ``intensity`` compared
    to the original. ``adjustments`` describes what changed and why so
    callers can audit the rewrite.
    """

    effective_request: ScanRequest
    autonomy_level: AutonomyLevel
    force_hitl: bool
    extra_scope: list[str] = field(default_factory=list)
    excluded_targets: list[str] = field(default_factory=list)
    adjustments: list[str] = field(default_factory=list)


class RuleOfEngagementEngine:
    """Pure-function gate consulted on every scan submission.

    The engine resolves the engagement (if ``engagement_id`` is set),
    enforces exclusions, caps intensity, and reports whether HITL must
    be forced. Returns the (possibly rewritten) request to the caller.
    """

    def __init__(self, store: EngagementPersistence) -> None:
        self.store = store

    async def evaluate(self, request: ScanRequest) -> RoEDecision:
        if request.engagement_id is None:
            return RoEDecision(
                effective_request=request,
                autonomy_level=AutonomyLevel.RECOMMEND,
                force_hitl=False,
            )
        engagement = await self.store.get(request.engagement_id)
        if engagement is None:
            raise GuardrailViolation(
                "ENGAGEMENT_NOT_FOUND",
                f"engagement {request.engagement_id} does not exist",
            )
        return self._evaluate_with_engagement(request, engagement)

    def _evaluate_with_engagement(
        self,
        request: ScanRequest,
        engagement: EngagementRecord,
    ) -> RoEDecision:
        rules = engagement.rules
        adjustments: list[str] = []

        host = _extract_host(request.target)
        if host and _matches_any(host, rules.excluded_targets):
            raise GuardrailViolation(
                "EXCLUDED_BY_ENGAGEMENT",
                f"target {host!r} is in engagement.excluded_targets",
            )

        autonomy = rules.autonomy_level
        capped_intensity = self._cap_intensity(
            request.intensity, rules.max_intensity, adjustments
        )
        capped_intensity = self._enforce_autonomy(
            capped_intensity, autonomy, adjustments
        )

        effective = (
            request
            if capped_intensity == request.intensity
            else request.model_copy(update={"intensity": capped_intensity})
        )
        effective = self._apply_llm_overrides(effective, rules, adjustments)
        return RoEDecision(
            effective_request=effective,
            autonomy_level=autonomy,
            force_hitl=rules.require_human_approval,
            extra_scope=list(rules.scope_allowlist),
            excluded_targets=list(rules.excluded_targets),
            adjustments=adjustments,
        )

    @staticmethod
    def _apply_llm_overrides(
        request: ScanRequest,
        rules: RulesOfEngagement,
        adjustments: list[str],
    ) -> ScanRequest:
        """Merge LLM-probe overrides from RoE into ``Target.metadata``.

        Rate limit + auth secret declared on the engagement supersede the
        per-request values. ``llm_require_rate_limit`` rejects the scan
        when neither side carries a rate limit — the operator opt-in keeps
        production safe by construction.
        """

        meta = dict(request.target.metadata or {})
        changed = False
        if rules.llm_probe_rate_limit_seconds is not None:
            meta["rate_limit_seconds"] = float(rules.llm_probe_rate_limit_seconds)
            adjustments.append(
                "llm_probe_rate_limit_seconds applied from engagement rules"
            )
            changed = True
        if rules.llm_auth_secret is not None:
            meta["auth_token"] = rules.llm_auth_secret.get_secret_value()
            adjustments.append("llm_auth_secret applied from engagement rules")
            changed = True
        if rules.llm_require_rate_limit and meta.get("rate_limit_seconds") is None:
            raise GuardrailViolation(
                "LLM_RATE_LIMIT_REQUIRED",
                "engagement requires an explicit LLM probe rate_limit_seconds; "
                "set rules.llm_probe_rate_limit_seconds or "
                "request.target.metadata.rate_limit_seconds",
            )
        if not changed:
            return request
        new_target = request.target.model_copy(update={"metadata": meta})
        return request.model_copy(update={"target": new_target})

    @staticmethod
    def _cap_intensity(
        requested: ScanIntensity,
        ceiling: ScanIntensity,
        adjustments: list[str],
    ) -> ScanIntensity:
        if intensity_rank(requested) <= intensity_rank(ceiling):
            return requested
        adjustments.append(
            f"intensity downgraded {requested.value}→{ceiling.value} "
            f"by engagement.max_intensity"
        )
        return ceiling

    @staticmethod
    def _enforce_autonomy(
        intensity: ScanIntensity,
        autonomy: AutonomyLevel,
        adjustments: list[str],
    ) -> ScanIntensity:
        max_intensity = _AUTONOMY_MAX_INTENSITY[autonomy]
        if max_intensity is None:
            raise GuardrailViolation(
                "AUTONOMY_INSUFFICIENT",
                f"engagement autonomy_level={autonomy.value} forbids "
                f"scanner execution; raise to execute_passive or above",
            )
        if intensity_rank(intensity) <= intensity_rank(max_intensity):
            return intensity
        adjustments.append(
            f"intensity downgraded {intensity.value}→{max_intensity.value} "
            f"by autonomy_level={autonomy.value}"
        )
        return max_intensity


def _extract_host(target: Target) -> str | None:
    if target.type == TargetType.URL:
        return urlparse(target.value).hostname
    return target.value


def _matches_any(host: str, patterns: list[str]) -> bool:
    for entry in patterns:
        if not entry:
            continue
        if entry == host or host.endswith("." + entry.lstrip(".")):
            return True
        try:
            net = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            continue
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            continue
        if ip.version == net.version and ip in net:
            return True
    return False


__all__ = [
    "RoEDecision",
    "RuleOfEngagementEngine",
]
