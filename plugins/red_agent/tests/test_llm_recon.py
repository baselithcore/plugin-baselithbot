"""Parser tests for the LLM recon scanner stub."""

from __future__ import annotations

from plugins.red_agent.models import Severity, Target, TargetType
from plugins.red_agent.scanners.llm_recon import LLMReconScanner


class _StubSandbox:
    pass


def _scanner() -> LLMReconScanner:
    return LLMReconScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]


def test_no_fingerprints_emits_no_findings() -> None:
    target = Target(type=TargetType.URL, value="https://example.com")
    findings = _scanner()._parse("<html>plain site</html>", target, target.value)
    assert findings == []


def test_gradio_fingerprint_emits_finding() -> None:
    body = '<script src="/gradio_client/index.js"></script>'
    target = Target(type=TargetType.URL, value="https://chat.example.com")
    findings = _scanner()._parse(body, target, target.value)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == Severity.MEDIUM
    assert f.cwe == "CWE-200"
    assert "gradio" in f.evidence["fingerprints"]
    assert any("LLM01" in ref for ref in f.evidence["owasp_llm_top_10"])


def test_openai_proxy_path_detected() -> None:
    body = "POST /v1/chat/completions HTTP/1.1"
    target = Target(type=TargetType.URL, value="https://api.example.com")
    findings = _scanner()._parse(body, target, target.value)
    assert findings
    assert "openai_proxy" in findings[0].evidence["fingerprints"]


def test_anthropic_endpoint_detected() -> None:
    body = "anthropic-version: 2023-06-01"
    target = Target(type=TargetType.URL, value="https://api.example.com")
    findings = _scanner()._parse(body, target, target.value)
    assert findings
    assert "anthropic_proxy" in findings[0].evidence["fingerprints"]


def test_target_to_url_handles_hostname() -> None:
    s = _scanner()
    assert s._target_to_url(Target(type=TargetType.HOSTNAME, value="x.test")) == (
        "https://x.test/"
    )


def test_target_to_url_returns_none_for_unsupported_kinds() -> None:
    s = _scanner()
    assert s._target_to_url(Target(type=TargetType.REPO, value="/work")) is None
