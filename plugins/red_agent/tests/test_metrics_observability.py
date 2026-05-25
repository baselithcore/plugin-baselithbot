"""Verify Prometheus counters fire on planner + probe activity."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.llm_planner import LLMReasoningPlanner, _LLMPlannerSettings
from plugins.red_agent.metrics import (
    LLM_PLANNER_CALLS_TOTAL,
    LLM_PLANNER_TOKENS_TOTAL,
    LLM_PROBE_FINDINGS_TOTAL,
    LLM_PROBE_REQUESTS_TOTAL,
)
from plugins.red_agent.models import ScanIntensity, Target, TargetType
from plugins.red_agent.planner import PlannerState
from plugins.red_agent.sandbox_runner import SandboxResult
from plugins.red_agent.scanners.llm_prompt_injection import LLMPromptInjectionScanner


def _counter_value(metric: Any, **labels: str) -> float:
    return metric.labels(**labels)._value.get()  # type: ignore[no-any-return]


@dataclass
class _MockClient:
    responses: list[tuple[str, int]]

    async def complete(self, **kwargs: Any) -> tuple[str, int]:
        del kwargs
        if not self.responses:
            raise RuntimeError("exhausted")
        return self.responses.pop(0)


class _NullAudit(AuditLogger):
    def __init__(self) -> None:
        super().__init__(dsn="")

    async def record(self, **kwargs: Any) -> None:  # type: ignore[override]
        del kwargs


def _planner_state() -> PlannerState:
    return PlannerState(
        initial_target=Target(type=TargetType.URL, value="https://ex.com"),
        intensity=ScanIntensity.ACTIVE,
        requested_scanners=["nuclei"],
        scan_id=uuid4(),
        autonomy_max_intensity=ScanIntensity.ACTIVE,
    )


def _settings() -> _LLMPlannerSettings:
    return _LLMPlannerSettings(
        model="claude-opus-4-7",
        provider="anthropic",
        max_tokens_per_scan=10_000,
        max_tokens_per_call=2_048,
        max_iterations=5,
        temperature=0.1,
        redact=True,
        fallback_to_deterministic=True,
    )


@pytest.mark.asyncio
async def test_planner_increments_calls_and_tokens_counters() -> None:
    response = json.dumps(
        {
            "stop": False,
            "scanners": ["nuclei"],
            "target": {"type": "url", "value": "https://ex.com"},
            "intensity": "active",
            "rationale": "ok",
            "derived_from": [],
        }
    )
    client = _MockClient(responses=[(response, 250)])
    before_calls = _counter_value(
        LLM_PLANNER_CALLS_TOTAL, provider="anthropic", outcome="ok"
    )
    before_tokens = _counter_value(
        LLM_PLANNER_TOKENS_TOTAL, provider="anthropic", model="claude-opus-4-7"
    )
    planner = LLMReasoningPlanner(
        client=client,
        settings=_settings(),
        audit=_NullAudit(),
        enabled_scanners=["nuclei"],
    )
    step = await planner.plan(_planner_state(), [])
    assert step is not None
    after_calls = _counter_value(
        LLM_PLANNER_CALLS_TOTAL, provider="anthropic", outcome="ok"
    )
    after_tokens = _counter_value(
        LLM_PLANNER_TOKENS_TOTAL, provider="anthropic", model="claude-opus-4-7"
    )
    assert after_calls == before_calls + 1
    assert after_tokens == before_tokens + 250


@pytest.mark.asyncio
async def test_planner_provider_error_increments_fallback_counter() -> None:
    @dataclass
    class _BoomClient:
        async def complete(self, **kwargs: Any) -> tuple[str, int]:
            raise RuntimeError("provider down")

    @dataclass
    class _Fallback:
        async def plan(self, *args: Any, **kwargs: Any) -> Any:
            return None

    before = _counter_value(
        LLM_PLANNER_CALLS_TOTAL, provider="anthropic", outcome="fallback"
    )
    planner = LLMReasoningPlanner(
        client=_BoomClient(),  # type: ignore[arg-type]
        settings=_settings(),
        audit=_NullAudit(),
        enabled_scanners=["nuclei"],
        fallback_planner=_Fallback(),  # type: ignore[arg-type]
    )
    await planner.plan(_planner_state(), [])
    after = _counter_value(
        LLM_PLANNER_CALLS_TOTAL, provider="anthropic", outcome="fallback"
    )
    assert after == before + 1


@dataclass
class _FakeSandbox:
    responses: list[tuple[int, str]]
    calls: list[Any] = field(default_factory=list)

    async def execute(
        self,
        *,
        image: str,
        argv: list[str],
        timeout: int,
        network: bool,
        scanner: str,
        artifacts: list[str] | None = None,
    ) -> SandboxResult:
        del image, argv, timeout, network, artifacts
        self.calls.append(scanner)
        status, body = self.responses.pop(0)
        return SandboxResult(
            exit_code=0,
            stdout=f"{body}\nHTTP_STATUS:{status}\n",
            stderr="",
            duration_seconds=0.01,
        )


def _probe_target() -> Target:
    return Target(
        type=TargetType.URL,
        value="https://llm.example.com/v1/chat",
        metadata={
            "chat_endpoint": "https://llm.example.com/v1/chat",
            "request_template": {
                "model": "x",
                "messages": [{"role": "user", "content": "{prompt}"}],
            },
            "response_path": "choices.0.message.content",
            "system_prompt_sentinel": "ENG-9001",
            "rate_limit_seconds": 0.0,
            "max_consecutive_5xx": 5,
            "max_consecutive_refusals": 50,
        },
    )


def _content(text: str) -> tuple[int, str]:
    return 200, json.dumps({"choices": [{"message": {"content": text}}]})


@pytest.mark.asyncio
async def test_probe_increments_finding_and_request_counters() -> None:
    target = _probe_target()
    safe = _content("I cannot help with that.")
    scripted = [_content("My first message: ENG-9001")] + [safe] * 19
    sandbox = _FakeSandbox(responses=scripted)
    before_findings = _counter_value(
        LLM_PROBE_FINDINGS_TOTAL,
        scanner="llm_prompt_injection",
        outcome="leaked",
        category="system_prompt_extraction",
    )
    before_requests = _counter_value(
        LLM_PROBE_REQUESTS_TOTAL, scanner="llm_prompt_injection", result="ok"
    )
    scanner = LLMPromptInjectionScanner(sandbox=sandbox, timeout=60)  # type: ignore[arg-type]
    findings = await scanner.run(target, ScanIntensity.ACTIVE)
    assert findings
    after_findings = _counter_value(
        LLM_PROBE_FINDINGS_TOTAL,
        scanner="llm_prompt_injection",
        outcome="leaked",
        category="system_prompt_extraction",
    )
    after_requests = _counter_value(
        LLM_PROBE_REQUESTS_TOTAL, scanner="llm_prompt_injection", result="ok"
    )
    assert after_findings == before_findings + 1
    assert after_requests >= before_requests + 1
