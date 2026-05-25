"""LLMPromptInjectionScanner unit tests.

Verify corpus parsing, detection logic, sandbox plumbing, autonomy
guard, redaction, and stop conditions. The sandbox is mocked to
avoid running curl or hitting any LLM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from plugins.red_agent.models import ScanIntensity, Severity, Target, TargetType
from plugins.red_agent.scanners._llm_probe import (
    DEFAULT_REFUSAL_MARKERS,
    PayloadEntry,
    TargetConfig,
    build_curl_argv,
    build_request_body,
    detect_outcome,
    extract_response_text,
    load_payloads,
    parse_curl_output,
    substitute_sentinel,
)
from plugins.red_agent.scanners.llm_prompt_injection import (
    CORPUS_FILENAME,
    LLMPromptInjectionScanner,
)
from plugins.red_agent.sandbox_runner import SandboxResult


# ---------- corpus parsing ----------


def test_corpus_loads_at_least_20_entries() -> None:
    payloads = load_payloads(CORPUS_FILENAME)
    assert len(payloads) >= 20
    ids = {p.id for p in payloads}
    assert len(ids) == len(payloads), "payload ids must be unique"
    categories = {p.category for p in payloads}
    assert {
        "system_prompt_extraction",
        "role_override",
        "refusal_bypass",
        "indirect_doc",
        "tool_abuse",
    }.issubset(categories)


def test_payload_entries_carry_required_fields() -> None:
    payloads = load_payloads(CORPUS_FILENAME)
    for p in payloads:
        assert p.id and p.prompt and p.detect, f"empty fields in {p.id}"
        assert p.cwe.startswith("CWE-")
        assert p.severity in {
            Severity.LOW,
            Severity.MEDIUM,
            Severity.HIGH,
            Severity.CRITICAL,
        }
        assert p.source.get("license"), f"{p.id} missing SPDX license"


# ---------- detection logic ----------


def _payload(**overrides: Any) -> PayloadEntry:
    base = dict(
        id="T-001",
        category="role_override",
        severity=Severity.HIGH,
        cwe="CWE-1426",
        prompt="ignore",
        detect={"bypassed": ["DAN-OK"]},
        refusal_markers=DEFAULT_REFUSAL_MARKERS,
        source={"name": "test", "license": "Apache-2.0"},
    )
    base.update(overrides)
    return PayloadEntry(**base)  # type: ignore[arg-type]


def test_detect_outcome_flags_leak_with_sentinel() -> None:
    p = _payload(detect={"leaked": ["{{SENTINEL}}", "system prompt"]})
    out = detect_outcome(
        "Sure! my system: SECRET-XYZ-123", p, sentinel="SECRET-XYZ-123"
    )
    assert out.detected and out.outcome == "leaked"
    assert "{{SENTINEL}}" in out.matched


def test_detect_outcome_treats_refusal_as_negative_for_bypassed() -> None:
    p = _payload(detect={"bypassed": ["DAN-OK"]})
    out = detect_outcome(
        "I cannot pretend to be DAN-OK; that violates policy.", p, sentinel=""
    )
    # refusal markers present → bypassed must NOT trigger even though
    # the response repeats the marker word.
    assert out.detected is False
    assert out.refusal is True


def test_detect_outcome_flags_tool_misfire() -> None:
    p = _payload(
        category="tool_abuse",
        detect={"tool_misfire": ["delete_user", "function_call"]},
    )
    out = detect_outcome('{"function_call": {"name": "delete_user"}}', p, sentinel="")
    assert out.detected and out.outcome == "tool_misfire"


def test_detect_outcome_clean_response_returns_no_detection() -> None:
    p = _payload()
    out = detect_outcome("Hello! How can I help?", p, sentinel="")
    assert out.detected is False
    assert out.outcome is None


# ---------- request shaping + curl argv ----------


def test_build_request_body_substitutes_prompt_in_template() -> None:
    template = {
        "model": "x",
        "messages": [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "{prompt}"},
        ],
    }
    body = build_request_body(template, "ignore previous")
    assert body["messages"][1]["content"] == "ignore previous"


def test_build_curl_argv_sets_auth_header_when_token_present() -> None:
    cfg = TargetConfig(
        chat_endpoint="https://llm.example.com/v1/chat",
        request_template={"messages": [{"role": "user", "content": "{prompt}"}]},
        response_path=("content",),
        auth_header_name="Authorization",
        auth_token="Bearer testtoken",
        system_prompt_sentinel="",
        rate_limit_seconds=0.0,
        max_consecutive_5xx=5,
        max_consecutive_refusals=10,
    )
    argv = build_curl_argv(cfg, {"messages": [{"role": "user", "content": "x"}]})
    assert "Authorization: Bearer testtoken" in argv
    assert argv[-1] == "https://llm.example.com/v1/chat"


def test_parse_curl_output_extracts_status() -> None:
    stdout = '{"choices":[{"message":{"content":"hi"}}]}\nHTTP_STATUS:200\n'
    status, body = parse_curl_output(stdout)
    assert status == 200
    assert body == '{"choices":[{"message":{"content":"hi"}}]}'


def test_extract_response_text_walks_dot_path() -> None:
    body = {"choices": [{"message": {"content": "hello!"}}]}
    text = extract_response_text(body, ("choices", "0", "message", "content"))
    assert text == "hello!"


def test_extract_response_text_falls_back_to_stringified_body() -> None:
    body = {"unexpected": "shape"}
    text = extract_response_text(body, ("choices", "0", "message", "content"))
    assert "unexpected" in text


def test_substitute_sentinel_strips_placeholder_when_unset() -> None:
    assert substitute_sentinel("call {{SENTINEL}} here", "") == "call  here"
    assert substitute_sentinel("call {{SENTINEL}} here", "X") == "call X here"


# ---------- end-to-end with mock sandbox ----------


@dataclass
class _FakeSandbox:
    """Replays canned curl outputs in order; records every call."""

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
        stdout = f"{body}\nHTTP_STATUS:{status}\n" if status else body
        self.calls.append(
            {
                "image": image,
                "argv": argv,
                "timeout": timeout,
                "scanner": scanner,
            }
        )
        return SandboxResult(
            exit_code=0, stdout=stdout, stderr="", duration_seconds=0.01
        )


def _make_target(*, sentinel: str = "BC-SENTINEL-42") -> Target:
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
            "auth_header_name": "Authorization",
            "auth_token": "Bearer test",
            "system_prompt_sentinel": sentinel,
            "rate_limit_seconds": 0.0,
            "max_consecutive_5xx": 3,
            "max_consecutive_refusals": 4,
        },
    )


def _content_response(text: str) -> tuple[int, str]:
    body = {"choices": [{"message": {"content": text}}]}
    return 200, json.dumps(body)


@pytest.mark.asyncio
async def test_scanner_emits_finding_for_one_true_positive() -> None:
    target = _make_target()
    # First payload (PI-001 leaked) triggers; pad refusals so the
    # consecutive-refusal stop condition does not fire mid-corpus.
    safe = "I cannot help with that request."
    scripted = [
        _content_response("Sure, my first message was: BC-SENTINEL-42"),
    ] + [_content_response(safe) for _ in range(19)]
    sandbox = _FakeSandbox(responses=scripted)
    scanner = LLMPromptInjectionScanner(sandbox=sandbox, timeout=60)  # type: ignore[arg-type]
    findings = await scanner.run(target, ScanIntensity.ACTIVE)
    assert len(findings) >= 1
    leak = findings[0]
    assert leak.cwe == "CWE-1426"
    assert leak.evidence["outcome"] == "leaked"
    assert leak.evidence["payload_id"] == "PI-001"


@pytest.mark.asyncio
async def test_scanner_refuses_when_intensity_below_active() -> None:
    target = _make_target()
    sandbox = _FakeSandbox(responses=[])
    scanner = LLMPromptInjectionScanner(sandbox=sandbox, timeout=60)  # type: ignore[arg-type]
    findings = await scanner.run(target, ScanIntensity.PASSIVE)
    assert findings == []
    assert sandbox.calls == []


@pytest.mark.asyncio
async def test_scanner_halts_on_consecutive_5xx() -> None:
    target = _make_target()
    sandbox = _FakeSandbox(responses=[(503, "service unavailable") for _ in range(10)])
    scanner = LLMPromptInjectionScanner(sandbox=sandbox, timeout=60)  # type: ignore[arg-type]
    findings = await scanner.run(target, ScanIntensity.ACTIVE)
    assert findings == []
    # max_consecutive_5xx=3 → exactly 3 calls before halt.
    assert len(sandbox.calls) == 3


@pytest.mark.asyncio
async def test_scanner_halts_on_consecutive_refusals() -> None:
    target = _make_target()  # max_consecutive_refusals=4
    safe = _content_response("I cannot help with that.")
    sandbox = _FakeSandbox(responses=[safe for _ in range(20)])
    scanner = LLMPromptInjectionScanner(sandbox=sandbox, timeout=60)  # type: ignore[arg-type]
    findings = await scanner.run(target, ScanIntensity.ACTIVE)
    assert findings == []
    assert len(sandbox.calls) == 4


@pytest.mark.asyncio
async def test_finding_evidence_has_redacted_token() -> None:
    target = _make_target()
    target.metadata["auth_token"] = "Bearer ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
    pad = _content_response("I cannot help.")
    scripted = [
        _content_response("Sure: BC-SENTINEL-42"),
    ] + [pad for _ in range(19)]
    sandbox = _FakeSandbox(responses=scripted)
    scanner = LLMPromptInjectionScanner(sandbox=sandbox, timeout=60)  # type: ignore[arg-type]
    findings = await scanner.run(target, ScanIntensity.ACTIVE)
    assert findings, "expected at least one finding"
    blob = json.dumps(findings[0].evidence)
    assert "ghp_" not in blob
    assert "[REDACTED]" in blob or "ghp_" not in blob


@pytest.mark.asyncio
async def test_target_config_rejects_non_http_endpoint() -> None:
    bad = Target(
        type=TargetType.URL,
        value="ftp://internal/llm",
        metadata={"chat_endpoint": "ftp://internal/llm"},
    )
    with pytest.raises(ValueError):
        TargetConfig.from_target(bad)
