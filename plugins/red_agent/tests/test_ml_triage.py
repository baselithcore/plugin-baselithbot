"""LLM triage service unit tests."""

from __future__ import annotations

import json
from typing import Any

import pytest

from plugins.red_agent.ml.triage import LLMTriageService
from plugins.red_agent.models import Finding, Severity, Target, TargetType


class _StubLLM:
    """Minimal stand-in for ``LLMService.generate_response``.

    Stores calls for assertions and returns a canned JSON payload so we
    can drive the parsing/apply branches without a real LLM provider.
    """

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def generate_response(
        self,
        prompt: str,
        model: str | None = None,
        json: bool = False,
        system_prompt: str | None = None,
    ) -> str:
        self.calls.append(
            {"prompt": prompt, "model": model, "json": json, "system": system_prompt}
        )
        return self.response


def _finding(**overrides: Any) -> Finding:
    base = dict(
        scanner="nuclei",
        title="example",
        description="generic banner",
        severity=Severity.MEDIUM,
        target="example.com",
        endpoint="https://example.com/login",
    )
    base.update(overrides)
    return Finding(**base)  # type: ignore[arg-type]


def _target() -> Target:
    return Target(type=TargetType.URL, value="https://example.com")


@pytest.mark.asyncio
async def test_disabled_when_llm_missing_returns_input_unchanged() -> None:
    svc = LLMTriageService(llm=None, model="x", enabled=True)
    findings = [_finding()]
    out = await svc.triage(findings, _target())
    assert out is findings
    assert svc.enabled is False


@pytest.mark.asyncio
async def test_explicit_disabled_short_circuits() -> None:
    llm = _StubLLM(response="{}")
    svc = LLMTriageService(llm=llm, model="x", enabled=False)
    findings = [_finding()]
    out = await svc.triage(findings, _target())
    assert out == findings
    assert llm.calls == []


@pytest.mark.asyncio
async def test_drops_high_confidence_false_positive() -> None:
    f = _finding()
    payload = {
        "triages": [
            {
                "finding_id": str(f.id),
                "verdict": "false_positive",
                "severity": "info",
                "confidence": 0.95,
                "rationale": "scanner template misfire",
                "remediation": "",
            }
        ]
    }
    svc = LLMTriageService(
        llm=_StubLLM(json.dumps(payload)),
        model="claude-haiku-4-5",
        enabled=True,
        drop_false_positives=True,
        min_confidence_to_override=0.8,
    )
    out = await svc.triage([f], _target())
    assert out == []


@pytest.mark.asyncio
async def test_low_confidence_false_positive_is_kept_and_annotated() -> None:
    f = _finding()
    payload = {
        "triages": [
            {
                "finding_id": str(f.id),
                "verdict": "false_positive",
                "severity": "low",
                "confidence": 0.5,
                "rationale": "uncertain",
                "remediation": "",
            }
        ]
    }
    svc = LLMTriageService(
        llm=_StubLLM(json.dumps(payload)),
        model="m",
        enabled=True,
        drop_false_positives=True,
        min_confidence_to_override=0.8,
    )
    out = await svc.triage([f], _target())
    assert len(out) == 1
    assert out[0].severity == Severity.MEDIUM  # confidence too low to override
    triage_block = out[0].evidence.get("triage_llm")
    assert triage_block is not None
    assert triage_block["verdict"] == "false_positive"
    assert triage_block["confidence"] == 0.5


@pytest.mark.asyncio
async def test_high_confidence_severity_override_records_original() -> None:
    f = _finding(severity=Severity.LOW, remediation=None)
    payload = {
        "triages": [
            {
                "finding_id": str(f.id),
                "verdict": "confirmed",
                "severity": "high",
                "confidence": 0.9,
                "rationale": "endpoint matches CVE-2024-XXXX",
                "remediation": "Patch component to v1.2.3",
            }
        ]
    }
    svc = LLMTriageService(
        llm=_StubLLM(json.dumps(payload)),
        model="m",
        enabled=True,
        min_confidence_to_override=0.8,
    )
    out = await svc.triage([f], _target())
    assert len(out) == 1
    assert out[0].severity == Severity.HIGH
    assert out[0].remediation == "Patch component to v1.2.3"
    triage_block = out[0].evidence["triage_llm"]
    assert triage_block["original_severity"] == "low"


@pytest.mark.asyncio
async def test_scanner_failure_findings_are_passed_through() -> None:
    failure = _finding(title="Scanner nmap failed", evidence={"scanner_failure": True})
    real = _finding(title="real-issue")
    payload = {
        "triages": [
            {
                "finding_id": str(real.id),
                "verdict": "confirmed",
                "severity": "high",
                "confidence": 0.95,
                "rationale": "ok",
                "remediation": "",
            }
        ]
    }
    llm = _StubLLM(json.dumps(payload))
    svc = LLMTriageService(llm=llm, model="m", enabled=True)
    out = await svc.triage([failure, real], _target())
    assert len(out) == 2
    # Failure must remain untouched
    assert any(f.id == failure.id for f in out)
    # Real finding got the LLM verdict applied
    real_after = next(f for f in out if f.id == real.id)
    assert real_after.severity == Severity.HIGH


@pytest.mark.asyncio
async def test_llm_error_returns_input_unchanged() -> None:
    class _BoomLLM:
        async def generate_response(self, *args: Any, **kwargs: Any) -> str:
            raise RuntimeError("provider down")

    f = _finding()
    svc = LLMTriageService(llm=_BoomLLM(), model="m", enabled=True)
    out = await svc.triage([f], _target())
    assert out == [f]


@pytest.mark.asyncio
async def test_malformed_json_returns_input_unchanged() -> None:
    f = _finding()
    svc = LLMTriageService(llm=_StubLLM("not-json"), model="m", enabled=True)
    out = await svc.triage([f], _target())
    assert out == [f]


@pytest.mark.asyncio
async def test_unknown_finding_id_in_response_is_ignored() -> None:
    f = _finding()
    payload = {
        "triages": [
            {
                "finding_id": "00000000-0000-0000-0000-000000000000",
                "verdict": "confirmed",
                "severity": "high",
                "confidence": 0.9,
                "rationale": "",
                "remediation": "",
            }
        ]
    }
    svc = LLMTriageService(llm=_StubLLM(json.dumps(payload)), model="m", enabled=True)
    out = await svc.triage([f], _target())
    assert out == [f]


@pytest.mark.asyncio
async def test_batch_size_drives_multiple_llm_calls() -> None:
    findings = [_finding(title=f"f{i}") for i in range(5)]
    # Each call returns an empty triage list — service preserves input.
    llm = _StubLLM(json.dumps({"triages": []}))
    svc = LLMTriageService(llm=llm, model="m", enabled=True, batch_size=2)
    await svc.triage(findings, _target())
    assert len(llm.calls) == 3  # ceil(5 / 2)
