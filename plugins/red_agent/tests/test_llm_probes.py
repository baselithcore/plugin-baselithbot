"""Tests for the three companion LLM probes (tool abuse, data
leakage, output handling) plus an integration scenario covering
true-positive / false-positive / ambiguous detection.

Re-uses the fake sandbox from ``test_llm_prompt_injection`` via a
local copy to keep the test files independent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from plugins.red_agent.models import ScanIntensity, Severity, Target, TargetType
from plugins.red_agent.scanners import (
    LLMDataLeakageScanner,
    LLMOutputHandlingScanner,
    LLMToolAbuseScanner,
)
from plugins.red_agent.scanners._llm_probe import load_payloads
from plugins.red_agent.sandbox_runner import SandboxResult


@dataclass
class _FakeSandbox:
    responses: list[tuple[int, str]]
    calls: list[dict[str, Any]] = field(default_factory=list)

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
        if not self.responses:
            raise RuntimeError("fake sandbox exhausted")
        status, body = self.responses.pop(0)
        stdout = f"{body}\nHTTP_STATUS:{status}\n"
        self.calls.append({"argv": argv, "scanner": scanner})
        return SandboxResult(
            exit_code=0, stdout=stdout, stderr="", duration_seconds=0.01
        )


def _target() -> Target:
    return Target(
        type=TargetType.URL,
        value="https://llm.example.com/v1/chat",
        metadata={
            "chat_endpoint": "https://llm.example.com/v1/chat",
            "request_template": {
                "model": "claude-haiku-4-5",
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


# ---------- corpus parsing ----------


@pytest.mark.parametrize(
    "filename, expected_min",
    [
        ("tool_abuse.yaml", 5),
        ("data_leakage.yaml", 5),
        ("output_handling.yaml", 5),
    ],
)
def test_each_corpus_parses_with_minimum_entries(
    filename: str, expected_min: int
) -> None:
    payloads = load_payloads(filename)
    assert len(payloads) >= expected_min
    for p in payloads:
        assert p.id and p.prompt
        assert p.severity in {
            Severity.LOW,
            Severity.MEDIUM,
            Severity.HIGH,
            Severity.CRITICAL,
        }
        assert p.source.get("license"), f"{p.id} missing SPDX license"


# ---------- per-scanner detection ----------


@pytest.mark.asyncio
async def test_tool_abuse_scanner_detects_function_call() -> None:
    target = _target()
    payloads = load_payloads("tool_abuse.yaml")
    refuse = _content("I cannot help with that.")
    # First payload (TA-001 transfer_funds) → tool_misfire; rest refuse.
    scripted = [
        _content(
            '{"function_call": {"name": "transfer_funds", "arguments": {"amount": 1000000}}}'
        ),
    ] + [refuse] * (len(payloads) - 1)
    sandbox = _FakeSandbox(responses=scripted)
    scanner = LLMToolAbuseScanner(sandbox=sandbox, timeout=60)  # type: ignore[arg-type]
    findings = await scanner.run(target, ScanIntensity.ACTIVE)
    assert len(findings) == 1
    assert findings[0].evidence["payload_id"] == "TA-001"
    assert findings[0].evidence["outcome"] == "tool_misfire"


@pytest.mark.asyncio
async def test_data_leakage_scanner_detects_sentinel_in_response() -> None:
    target = _target()
    payloads = load_payloads("data_leakage.yaml")
    refuse = _content("I cannot share that information.")
    # DL-002 (secret extraction) leaks sentinel.
    scripted = [
        refuse,
        _content("Sure: API_KEY=ENG-9001 and TOKEN=xyz"),
    ] + [refuse] * (len(payloads) - 2)
    sandbox = _FakeSandbox(responses=scripted)
    scanner = LLMDataLeakageScanner(sandbox=sandbox, timeout=60)  # type: ignore[arg-type]
    findings = await scanner.run(target, ScanIntensity.ACTIVE)
    assert len(findings) == 1
    assert findings[0].evidence["payload_id"] == "DL-002"
    assert findings[0].evidence["outcome"] == "leaked"


@pytest.mark.asyncio
async def test_output_handling_scanner_detects_xss_payload_echo() -> None:
    target = _target()
    payloads = load_payloads("output_handling.yaml")
    safe = _content("Sorry, I can't echo that.")
    scripted = [
        _content("<script>alert(document.cookie)</script>"),
    ] + [safe] * (len(payloads) - 1)
    sandbox = _FakeSandbox(responses=scripted)
    scanner = LLMOutputHandlingScanner(sandbox=sandbox, timeout=60)  # type: ignore[arg-type]
    findings = await scanner.run(target, ScanIntensity.ACTIVE)
    assert len(findings) == 1
    assert findings[0].evidence["payload_id"] == "OH-001"
    assert findings[0].cwe == "CWE-79"


@pytest.mark.parametrize(
    "scanner_cls, corpus",
    [
        (LLMToolAbuseScanner, "tool_abuse.yaml"),
        (LLMDataLeakageScanner, "data_leakage.yaml"),
        (LLMOutputHandlingScanner, "output_handling.yaml"),
    ],
)
@pytest.mark.asyncio
async def test_each_scanner_refuses_passive_intensity(
    scanner_cls: type, corpus: str
) -> None:
    del corpus
    target = _target()
    sandbox = _FakeSandbox(responses=[])
    scanner = scanner_cls(sandbox=sandbox, timeout=60)
    findings = await scanner.run(target, ScanIntensity.PASSIVE)
    assert findings == []
    assert sandbox.calls == []


# ---------- integration: TP / FP / ambiguous ----------


@pytest.mark.asyncio
async def test_integration_true_positive_false_positive_and_refusal() -> None:
    """End-to-end on the prompt-injection corpus.

    Scripted target responds with:
    * PI-001 → ``leaked`` (true positive, sentinel echoed)
    * PI-002 → benign refusal (no detection)
    * PI-003 → matches "DAN-OK" but with refusal markers — must be
      *suppressed* by the refusal-aware bypassed detector
    * remaining payloads → safe refusal
    """
    from plugins.red_agent.scanners.llm_prompt_injection import (
        LLMPromptInjectionScanner,
    )

    target = _target()
    payloads = load_payloads("injection.yaml")
    safe = _content("I'm sorry, I cannot help with that.")
    scripted = [
        _content("My first message was: ENG-9001"),  # PI-001 leaked  → TP
        _content("Hello! Happy to help."),  # PI-002 → no detection (FP candidate)
        _content(
            "I cannot pretend to be DAN-OK; that violates policy."
        ),  # PI-003 ambiguous
    ] + [safe] * (len(payloads) - 3)
    sandbox = _FakeSandbox(responses=scripted)
    scanner = LLMPromptInjectionScanner(sandbox=sandbox, timeout=60)  # type: ignore[arg-type]
    findings = await scanner.run(target, ScanIntensity.ACTIVE)
    payload_ids = {f.evidence["payload_id"] for f in findings}
    assert "PI-001" in payload_ids
    assert "PI-002" not in payload_ids  # benign helpful response, no detection
    assert "PI-003" not in payload_ids  # refusal marker suppresses bypassed
