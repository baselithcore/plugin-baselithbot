"""LLM-driven planner core: :class:`LLMReasoningPlanner` and its factory."""

from __future__ import annotations

import json

from core.observability.logging import get_logger
from core.observability.tracing import get_tracer
from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.llm_planner._client import (
    CoreLLMServiceClient,
    LLMPlannerClient,
)
from plugins.red_agent.llm_planner._prompt import (
    _LLMPlannerSettings,
    _SYSTEM_PROMPT,
    _build_prompt,
    _parse_step,
)
from plugins.red_agent.metrics import (
    LLM_PLANNER_CALLS_TOTAL,
    LLM_PLANNER_LATENCY_SECONDS,
    LLM_PLANNER_TOKENS_TOTAL,
)
from plugins.red_agent.models import (
    Finding,
    intensity_rank,
)
from plugins.red_agent.planner import (
    AttackPlanner,
    ChainingPlanner,
    PlannerState,
    PlannerStep,
)

_tracer = get_tracer("red_agent.planner")

logger = get_logger(__name__)


class LLMReasoningPlanner:
    """LLM-driven planner with sticky fallback to a deterministic chain.

    The planner enforces autonomy/intensity caps and a per-scan token
    budget locally; the critic still vets every returned step for
    scope, exclusions, and redundancy. On any failure (provider error,
    JSON parse, schema violation, budget exhaustion) the planner
    delegates the rest of the current scan to ``fallback_planner``.
    """

    def __init__(
        self,
        client: LLMPlannerClient,
        settings: _LLMPlannerSettings,
        audit: AuditLogger,
        enabled_scanners: list[str],
        fallback_planner: AttackPlanner | None = None,
    ) -> None:
        self.client = client
        self.settings = settings
        self.audit = audit
        self.enabled_scanners = list(enabled_scanners)
        self.fallback_planner: AttackPlanner = fallback_planner or ChainingPlanner(
            max_iterations=settings.max_iterations
        )
        self.tokens_used = 0
        self._fallback_active = False
        self._fallback_reason: str | None = None

    async def plan(
        self, state: PlannerState, new_findings: list[Finding]
    ) -> PlannerStep | None:
        if state.iterations >= self.settings.max_iterations:
            return None
        if self._fallback_active:
            return await self.fallback_planner.plan(state, new_findings)

        prompt = _build_prompt(
            state, new_findings, self.settings, self.enabled_scanners
        )
        provider = self.settings.provider
        model = self.settings.model
        with _tracer.start_span(
            "red_agent.planner.llm_call",
            attributes={
                "planner.provider": provider,
                "planner.model": model,
                "planner.iteration": state.iterations,
                "planner.scan_id": str(state.scan_id) if state.scan_id else "",
            },
        ) as span:
            import time

            t0 = time.perf_counter()
            try:
                text, tokens = await self.client.complete(
                    prompt=prompt,
                    system=_SYSTEM_PROMPT,
                    model=model,
                    max_tokens=self.settings.max_tokens_per_call,
                    temperature=self.settings.temperature,
                )
            except Exception as exc:  # noqa: BLE001
                LLM_PLANNER_CALLS_TOTAL.labels(provider=provider, outcome="error").inc()
                span.set_attribute("planner.error", str(exc))
                return await self._activate_fallback(
                    state, new_findings, reason=f"llm_call_error: {exc}"
                )
            LLM_PLANNER_LATENCY_SECONDS.labels(provider=provider).observe(
                time.perf_counter() - t0
            )
            LLM_PLANNER_CALLS_TOTAL.labels(provider=provider, outcome="ok").inc()
            LLM_PLANNER_TOKENS_TOTAL.labels(provider=provider, model=model).inc(
                int(tokens)
            )
            span.set_attribute("planner.tokens", int(tokens))

        self.tokens_used += int(tokens)
        await self._record_call(state, tokens=tokens, prompt_len=len(prompt))

        if self.tokens_used > self.settings.max_tokens_per_scan:
            return await self._activate_fallback(
                state,
                new_findings,
                reason=(
                    f"token_budget_exhausted "
                    f"({self.tokens_used}/{self.settings.max_tokens_per_scan})"
                ),
            )

        try:
            step = _parse_step(text, state)
        except (json.JSONDecodeError, ValueError) as exc:
            return await self._activate_fallback(
                state, new_findings, reason=f"parse_error: {exc}"
            )

        if step is None:
            await self._record_hypothesis(state, rationale="planner_stop", step=None)
            return None

        cap = state.autonomy_max_intensity
        if cap is not None and intensity_rank(step.intensity) > intensity_rank(cap):
            await self._record_hypothesis(
                state,
                rationale=(
                    f"self_rejected: intensity {step.intensity.value} "
                    f"exceeds autonomy cap {cap.value}"
                ),
                step=step,
            )
            return None

        await self._record_hypothesis(state, rationale=step.rationale, step=step)
        return step

    async def _activate_fallback(
        self,
        state: PlannerState,
        new_findings: list[Finding],
        *,
        reason: str,
    ) -> PlannerStep | None:
        self._fallback_active = True
        self._fallback_reason = reason
        LLM_PLANNER_CALLS_TOTAL.labels(
            provider=self.settings.provider, outcome="fallback"
        ).inc()
        await self.audit.record(
            scan_id=state.scan_id,
            actor="red_agent",
            event="scan.planner_llm_fallback",
            payload={
                "reason": reason,
                "fallback_planner": type(self.fallback_planner).__name__,
                "tokens_used": self.tokens_used,
                "iteration": state.iterations,
            },
        )
        if not self.settings.fallback_to_deterministic:
            return None
        return await self.fallback_planner.plan(state, new_findings)

    async def _record_call(
        self, state: PlannerState, *, tokens: int, prompt_len: int
    ) -> None:
        await self.audit.record(
            scan_id=state.scan_id,
            actor="red_agent",
            event="scan.planner_llm_call",
            payload={
                "provider": self.settings.provider,
                "model": self.settings.model,
                "tokens": int(tokens),
                "tokens_total": self.tokens_used,
                "prompt_chars": prompt_len,
                "iteration": state.iterations,
            },
        )

    async def _record_hypothesis(
        self,
        state: PlannerState,
        *,
        rationale: str,
        step: PlannerStep | None,
    ) -> None:
        payload: dict[str, object] = {
            "iteration": state.iterations,
            "rationale": rationale,
        }
        if step is not None:
            payload.update(
                {
                    "scanners": list(step.scanners),
                    "target": step.target.value,
                    "intensity": step.intensity.value,
                    "derived_from": list(step.derived_from),
                }
            )
        await self.audit.record(
            scan_id=state.scan_id,
            actor="red_agent",
            event="scan.planner_hypothesis",
            payload=payload,
        )


def build_llm_planner(
    *,
    config: object,
    audit: AuditLogger,
    enabled_scanners: list[str],
    client: LLMPlannerClient | None = None,
    fallback_planner: AttackPlanner | None = None,
) -> LLMReasoningPlanner:
    """Factory: assemble :class:`LLMReasoningPlanner` from a RedAgentConfig.

    ``config`` is typed loosely so this module does not import the full
    plugin config (which would create a cycle). Only the LLM-planner
    fields are read.
    """

    settings = _LLMPlannerSettings(
        model=getattr(config, "llm_planner_model", "claude-opus-4-7"),
        provider=getattr(config, "llm_planner_provider", "anthropic"),
        max_tokens_per_scan=getattr(config, "llm_planner_max_tokens_per_scan", 50_000),
        max_tokens_per_call=getattr(config, "llm_planner_max_tokens_per_call", 2048),
        max_iterations=getattr(config, "llm_planner_max_iterations", 8),
        temperature=getattr(config, "llm_planner_temperature", 0.2),
        redact=getattr(config, "llm_planner_redact_secrets", True),
        fallback_to_deterministic=getattr(
            config, "llm_planner_fallback_to_deterministic", True
        ),
    )
    return LLMReasoningPlanner(
        client=client or CoreLLMServiceClient(),
        settings=settings,
        audit=audit,
        enabled_scanners=enabled_scanners,
        fallback_planner=fallback_planner,
    )
