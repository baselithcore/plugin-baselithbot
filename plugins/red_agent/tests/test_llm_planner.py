"""LLMReasoningPlanner unit tests.

Mock the LLM client end-to-end so the planner exercises its parse,
validation, autonomy-cap, token-budget, and fallback paths without
touching the network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.critic import CriticContext, RoECritic
from plugins.red_agent.llm_planner import (
    LLMReasoningPlanner,
    _LLMPlannerSettings,
    redact_secrets,
)
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.planner import PlannerState


# ---------- helpers ----------


@dataclass
class _MockClient:
    """LLM client double: dispenses canned responses + records prompts."""

    responses: list[tuple[str, int]]
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def complete(
        self,
        *,
        prompt: str,
        system: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]:
        self.calls.append(
            {
                "prompt": prompt,
                "system": system,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        if not self.responses:
            raise RuntimeError("mock exhausted")
        return self.responses.pop(0)


class _RecordingAudit(AuditLogger):
    """AuditLogger that records to memory and skips DB I/O."""

    def __init__(self) -> None:
        super().__init__(dsn="")
        self.events: list[dict[str, Any]] = []

    async def record(  # type: ignore[override]
        self,
        *,
        scan_id: Any,
        actor: str,
        event: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "scan_id": str(scan_id) if scan_id else None,
                "actor": actor,
                "event": event,
                "payload": payload or {},
            }
        )


def _settings(**overrides: Any) -> _LLMPlannerSettings:
    base = dict(
        model="claude-opus-4-7",
        provider="anthropic",
        max_tokens_per_scan=10_000,
        max_tokens_per_call=2_048,
        max_iterations=5,
        temperature=0.1,
        redact=True,
        fallback_to_deterministic=True,
    )
    base.update(overrides)
    return _LLMPlannerSettings(**base)  # type: ignore[arg-type]


def _state(
    *,
    intensity: ScanIntensity = ScanIntensity.ACTIVE,
    autonomy_cap: ScanIntensity | None = ScanIntensity.ACTIVE,
    iterations: int = 0,
) -> PlannerState:
    return PlannerState(
        initial_target=Target(type=TargetType.URL, value="https://example.com"),
        intensity=intensity,
        requested_scanners=["nuclei", "zap"],
        iterations=iterations,
        scan_id=uuid4(),
        autonomy_max_intensity=autonomy_cap,
    )


def _step_json(
    *,
    scanners: list[str],
    target: str,
    intensity: str = "active",
    rationale: str = "test",
    stop: bool = False,
) -> str:
    return json.dumps(
        {
            "stop": stop,
            "scanners": scanners,
            "target": {"type": "url", "value": target},
            "intensity": intensity,
            "rationale": rationale,
            "derived_from": [],
        }
    )


# ---------- tests ----------


@pytest.mark.asyncio
async def test_planner_returns_step_and_emits_call_audit() -> None:
    client = _MockClient(
        responses=[(_step_json(scanners=["nuclei"], target="https://example.com"), 120)]
    )
    audit = _RecordingAudit()
    planner = LLMReasoningPlanner(
        client=client,
        settings=_settings(),
        audit=audit,
        enabled_scanners=["nuclei", "zap"],
    )
    step = await planner.plan(_state(), [])
    assert step is not None
    assert step.scanners == ["nuclei"]
    assert step.target.value == "https://example.com"
    events = [e["event"] for e in audit.events]
    assert "scan.planner_llm_call" in events
    assert "scan.planner_hypothesis" in events


@pytest.mark.asyncio
async def test_planner_self_rejects_when_intensity_above_autonomy_cap() -> None:
    client = _MockClient(
        responses=[
            (
                _step_json(
                    scanners=["sqlmap"],
                    target="https://example.com",
                    intensity="intrusive",
                ),
                80,
            )
        ]
    )
    audit = _RecordingAudit()
    planner = LLMReasoningPlanner(
        client=client,
        settings=_settings(),
        audit=audit,
        enabled_scanners=["nuclei", "zap", "sqlmap"],
    )
    step = await planner.plan(_state(autonomy_cap=ScanIntensity.ACTIVE), [])
    assert step is None
    rejections = [
        e
        for e in audit.events
        if e["event"] == "scan.planner_hypothesis"
        and "self_rejected" in e["payload"].get("rationale", "")
    ]
    assert rejections, "expected planner self-rejection audit event"


@pytest.mark.asyncio
async def test_out_of_scope_step_is_vetoed_by_critic() -> None:
    client = _MockClient(
        responses=[
            (_step_json(scanners=["nuclei"], target="https://attacker.evil.com"), 90)
        ]
    )
    audit = _RecordingAudit()
    planner = LLMReasoningPlanner(
        client=client,
        settings=_settings(),
        audit=audit,
        enabled_scanners=["nuclei"],
    )
    step = await planner.plan(_state(), [])
    assert step is not None  # planner returns; critic is the gate
    critic = RoECritic()
    review = critic.review(
        step,
        CriticContext(
            extra_scope=["example.com"],
            global_scope=["example.com"],
            max_intensity=ScanIntensity.ACTIVE,
        ),
    )
    assert review.approved is False
    assert "scope_allowlist" in review.reason


@pytest.mark.asyncio
async def test_provider_error_triggers_sticky_fallback() -> None:
    @dataclass
    class _BoomClient:
        async def complete(self, **kwargs: Any) -> tuple[str, int]:
            raise RuntimeError("provider down")

    @dataclass
    class _FallbackPlanner:
        called: int = 0

        async def plan(self, state: PlannerState, new_findings: list[Finding]) -> Any:
            self.called += 1
            from plugins.red_agent.planner import PlannerStep

            return PlannerStep(
                scanners=["nmap"],
                target=state.initial_target,
                intensity=state.intensity,
                rationale="fallback",
            )

    audit = _RecordingAudit()
    fallback = _FallbackPlanner()
    planner = LLMReasoningPlanner(
        client=_BoomClient(),  # type: ignore[arg-type]
        settings=_settings(),
        audit=audit,
        enabled_scanners=["nmap"],
        fallback_planner=fallback,  # type: ignore[arg-type]
    )
    step1 = await planner.plan(_state(), [])
    step2 = await planner.plan(_state(iterations=1), [])
    assert step1 is not None and step1.rationale == "fallback"
    assert step2 is not None and step2.rationale == "fallback"
    assert fallback.called == 2  # sticky: every subsequent call delegates
    assert any(e["event"] == "scan.planner_llm_fallback" for e in audit.events)


@pytest.mark.asyncio
async def test_token_budget_exhaustion_halts_or_falls_back() -> None:
    client = _MockClient(
        responses=[
            (_step_json(scanners=["nuclei"], target="https://example.com"), 9_999),
            (_step_json(scanners=["zap"], target="https://example.com"), 5_000),
        ]
    )
    audit = _RecordingAudit()
    planner = LLMReasoningPlanner(
        client=client,
        settings=_settings(max_tokens_per_scan=8_000, fallback_to_deterministic=False),
        audit=audit,
        enabled_scanners=["nuclei", "zap"],
    )
    # First call already overflows the per-scan budget → fallback triggers,
    # but disabled fallback returns None.
    step = await planner.plan(_state(), [])
    assert step is None
    fallbacks = [e for e in audit.events if e["event"] == "scan.planner_llm_fallback"]
    assert fallbacks
    assert "token_budget_exhausted" in fallbacks[0]["payload"]["reason"]


@pytest.mark.asyncio
async def test_parse_failure_triggers_fallback_event() -> None:
    client = _MockClient(responses=[("not json", 50)])
    audit = _RecordingAudit()
    planner = LLMReasoningPlanner(
        client=client,
        settings=_settings(fallback_to_deterministic=False),
        audit=audit,
        enabled_scanners=["nuclei"],
    )
    assert await planner.plan(_state(), []) is None
    assert any(
        "parse_error" in e["payload"].get("reason", "")
        for e in audit.events
        if e["event"] == "scan.planner_llm_fallback"
    )


@pytest.mark.asyncio
async def test_planner_passes_redacted_findings_to_llm() -> None:
    client = _MockClient(
        responses=[(_step_json(scanners=["nuclei"], target="https://example.com"), 80)]
    )
    audit = _RecordingAudit()
    planner = LLMReasoningPlanner(
        client=client,
        settings=_settings(),
        audit=audit,
        enabled_scanners=["nuclei"],
    )
    leaky = Finding(
        scanner="gitleaks",
        title="aws key in repo",
        description="d",
        severity=Severity.HIGH,
        target="example.com",
        evidence={
            "key": "AKIAIOSFODNN7EXAMPLE",
            "token": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
        },
    )
    state = _state()
    state.seen_findings = [leaky]
    await planner.plan(state, [leaky])
    sent_prompt = client.calls[0]["prompt"]
    assert "AKIAIOSFODNN7EXAMPLE" not in sent_prompt
    assert "ghp_" not in sent_prompt
    assert "[REDACTED]" in sent_prompt


@pytest.mark.asyncio
async def test_stop_response_returns_none_with_audit() -> None:
    client = _MockClient(responses=[(json.dumps({"stop": True}), 30)])
    audit = _RecordingAudit()
    planner = LLMReasoningPlanner(
        client=client,
        settings=_settings(),
        audit=audit,
        enabled_scanners=["nuclei"],
    )
    assert await planner.plan(_state(), []) is None
    assert any(e["event"] == "scan.planner_hypothesis" for e in audit.events)


def test_redact_secrets_handles_jwt_and_pem() -> None:
    blob = {
        "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTYifQ.signaturepart_abc",
        "key": "AKIAIOSFODNN7EXAMPLE",
        "list": ["ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345", "harmless"],
        "pem": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...",
    }
    out = redact_secrets(blob)
    assert isinstance(out, dict)
    assert out["jwt"] == "[REDACTED]"
    assert out["key"] == "[REDACTED]"
    assert "[REDACTED]" in out["list"]
    assert "harmless" in out["list"]
    assert "[REDACTED]" in out["pem"]
