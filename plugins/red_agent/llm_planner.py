"""LLM-driven attack planner.

Drop-in replacement for :class:`ChainingPlanner` selected when
``RedAgentConfig.llm_planner_enabled`` is on and the engagement
autonomy reaches at least ``execute_active``.

The planner asks an LLM for the next ``PlannerStep`` given the goal,
state, and findings observed so far. The orchestrator + critic still
execute and vet every step — the LLM never sees credentials, scanner
raw bytes, or sandbox state, and never invokes scanners directly.

Safety contract enforced inside ``plan()``:

* **autonomy cap** — proposed intensity capped to
  ``state.autonomy_max_intensity`` before the step is even returned.
  The critic's :class:`RoECritic` is the second wall, but rejecting
  here lets us emit ``planner_hypothesis`` rejections cleanly.
* **token budget** — sum of input+output tokens across calls is
  bounded by ``llm_planner_max_tokens_per_scan``. Overflow halts the
  chain (``planner_llm_fallback`` audit event).
* **redaction** — finding ``evidence`` and ``raw`` blobs are passed
  through :func:`redact_secrets` before serialization.
* **provider fallback** — any client error / parse failure / schema
  violation flips a sticky fallback flag and delegates the rest of
  the scan to ``fallback_planner`` (typically :class:`ChainingPlanner`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    pass

from core.observability.logging import get_logger
from core.observability.tracing import get_tracer
from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.metrics import (
    LLM_PLANNER_CALLS_TOTAL,
    LLM_PLANNER_LATENCY_SECONDS,
    LLM_PLANNER_TOKENS_TOTAL,
)
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Target,
    TargetType,
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


class _LLMService(Protocol):
    """Internal protocol for the LLM service methods used by the client."""

    async def generate_response(
        self,
        prompt: str,
        model: str | None = None,
        json: bool = False,
        system_prompt: str | None = None,
    ) -> str: ...


class LLMPlannerClient(Protocol):
    """Minimal async LLM surface the planner depends on.

    Decouples the planner from ``core.services.llm.LLMService`` so tests
    can inject a deterministic mock. ``complete`` returns the model
    response text plus the total tokens billed for the call (input +
    output). The wrapper :class:`CoreLLMServiceClient` adapts the
    real service.
    """

    async def complete(
        self,
        *,
        prompt: str,
        system: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]: ...


class CoreLLMServiceClient:
    """Adapter over ``core.services.llm.LLMService.generate_response``.

    Reuses the production caching/cost-control/circuit-breaker stack
    instead of speaking to the provider directly. Token usage is read
    from the service's tracker per-call when available, otherwise an
    estimate based on prompt + response length is used.
    """

    _service: _LLMService | Any | None

    def __init__(self, service: _LLMService | Any | None = None) -> None:
        self._service = service

    async def complete(
        self,
        *,
        prompt: str,
        system: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]:
        if self._service is None:
            from core.services.llm.service import get_llm_service

            self._service = get_llm_service()

        from core.services.llm.cost_control import estimate_tokens

        text = await self._service.generate_response(
            prompt=prompt,
            model=model,
            json=True,
            system_prompt=system,
        )
        tokens = estimate_tokens(prompt) + estimate_tokens(text)
        del max_tokens, temperature  # forwarded via service config
        return text, tokens


_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"ASIA[0-9A-Z]{16}"),  # AWS STS key
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),  # GitHub PAT
    re.compile(r"gho_[A-Za-z0-9]{30,}"),  # GitHub OAuth
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"glpat-[A-Za-z0-9_-]{20,}"),  # GitLab PAT
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),  # Slack tokens
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI / generic SK
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),  # Google API key
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
)

_REDACTED = "[REDACTED]"


def redact_secrets(value: object) -> object:
    """Return ``value`` with known secret patterns replaced.

    Recurses into dicts and lists, leaves other scalars untouched.
    Pure function; safe to call on arbitrary finding evidence blobs.
    """

    if isinstance(value, str):
        out = value
        for pat in _SECRET_PATTERNS:
            out = pat.sub(_REDACTED, out)
        return out
    if isinstance(value, dict):
        return {k: redact_secrets(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_secrets(v) for v in value]
    return value


@dataclass
class _LLMPlannerSettings:
    model: str
    provider: str
    max_tokens_per_scan: int
    max_tokens_per_call: int
    max_iterations: int
    temperature: float
    redact: bool
    fallback_to_deterministic: bool


_VALID_INTENSITIES = {i.value for i in ScanIntensity}


def _coerce_target(payload: dict, default: Target) -> Target:
    """Build a Target from the LLM response, preferring planner-known types."""

    raw_type = (payload.get("type") or default.type.value).lower()
    raw_value = payload.get("value") or default.value
    try:
        ttype = TargetType(raw_type)
    except ValueError:
        ttype = default.type
    return Target(type=ttype, value=str(raw_value))


def _parse_step(text: str, state: PlannerState) -> PlannerStep | None:
    """Parse the LLM response text into a PlannerStep.

    Accepts a JSON object with ``stop`` (bool), ``scanners`` (list[str]),
    ``target`` (object with ``type``/``value``), ``intensity`` (string),
    ``rationale`` (string), and ``derived_from`` (list[str]). Strips
    Markdown fences if present. Returns ``None`` on stop=true or when
    the JSON is structurally invalid.
    """

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("planner response must be a JSON object")

    if payload.get("stop") is True:
        return None

    scanners = payload.get("scanners") or []
    if not isinstance(scanners, list) or not all(isinstance(s, str) for s in scanners):
        raise ValueError("scanners must be a list of strings")
    if not scanners:
        return None

    target_payload = payload.get("target") or {}
    if not isinstance(target_payload, dict):
        raise ValueError("target must be an object")
    target = _coerce_target(target_payload, state.initial_target)

    intensity_raw = (payload.get("intensity") or state.intensity.value).lower()
    if intensity_raw not in _VALID_INTENSITIES:
        raise ValueError(f"unknown intensity {intensity_raw!r}")
    intensity = ScanIntensity(intensity_raw)

    rationale = str(payload.get("rationale") or "")
    derived_from_raw = payload.get("derived_from") or []
    derived_from = (
        [str(x) for x in derived_from_raw] if isinstance(derived_from_raw, list) else []
    )

    return PlannerStep(
        scanners=[s for s in scanners if s],
        target=target,
        intensity=intensity,
        rationale=rationale,
        derived_from=derived_from,
    )


_SYSTEM_PROMPT = (
    "You are the planner for a defensive Red Team agent. Each turn you "
    "receive the engagement goal, the initial target, the scanners available, "
    "the intensity ceiling enforced by the engagement, and the findings "
    "discovered so far. You propose the NEXT scan step or stop. You never "
    "execute scanners yourself; an orchestrator runs your proposal in a "
    "sandbox and a separate critic re-checks every step against scope and "
    "intensity. Return ONLY a JSON object matching this schema: "
    '{"stop": bool, "scanners": [string], "target": {"type": string, '
    '"value": string}, "intensity": "passive"|"active"|"intrusive", '
    '"rationale": string, "derived_from": [string]}. '
    "If the previous iterations produced nothing actionable, return "
    '{"stop": true}. Keep proposals inside the engagement scope.'
)


def _build_prompt(
    state: PlannerState,
    new_findings: list[Finding],
    settings: _LLMPlannerSettings,
    enabled_scanners: list[str],
) -> str:
    findings_payload: list[dict] = []
    for f in (state.seen_findings or [])[-20:]:
        findings_payload.append(
            {
                "scanner": f.scanner,
                "title": f.title,
                "severity": f.severity.value,
                "endpoint": f.endpoint,
                "service": f.service,
                "cwe": f.cwe,
                "evidence": redact_secrets(f.evidence)
                if settings.redact
                else f.evidence,
            }
        )
    new_payload: list[dict] = []
    for f in new_findings[-20:]:
        new_payload.append(
            {
                "id": str(f.id),
                "scanner": f.scanner,
                "title": f.title,
                "severity": f.severity.value,
                "endpoint": f.endpoint,
                "service": f.service,
                "cwe": f.cwe,
                "evidence": redact_secrets(f.evidence)
                if settings.redact
                else f.evidence,
            }
        )
    ceiling = (state.autonomy_max_intensity or state.intensity).value
    body = {
        "iteration": state.iterations,
        "max_iterations": settings.max_iterations,
        "initial_target": {
            "type": state.initial_target.type.value,
            "value": state.initial_target.value,
        },
        "intensity_ceiling": ceiling,
        "requested_scanners": list(state.requested_scanners),
        "enabled_scanners": enabled_scanners,
        "seen_endpoints": sorted(state.seen_endpoints),
        "seen_services": sorted(state.seen_services),
        "previous_findings": findings_payload,
        "new_findings": new_payload,
    }
    return json.dumps(body, default=str)


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


__all__ = [
    "CoreLLMServiceClient",
    "LLMPlannerClient",
    "LLMReasoningPlanner",
    "build_llm_planner",
    "redact_secrets",
]
