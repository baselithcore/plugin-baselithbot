"""Unit tests for Red Agent guardrails."""

from __future__ import annotations

import pytest

from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.guardrails import (
    GuardrailPipeline,
    GuardrailViolation,
    TargetGuardrails,
)
from plugins.red_agent.models import (
    ScanIntensity,
    ScanRequest,
    Target,
    TargetType,
)


@pytest.fixture()
def config() -> RedAgentConfig:
    return RedAgentConfig(
        scope_allowlist=["example.com", "93.184.0.0/16"],
        bug_bounty_mode=False,
        allow_internal_targets=False,
        require_hitl_for_active=True,
    )


def test_ssrf_blocks_loopback(config: RedAgentConfig) -> None:
    g = TargetGuardrails(config)
    with pytest.raises(GuardrailViolation) as exc:
        g.validate(Target(type=TargetType.URL, value="http://127.0.0.1/admin"))
    assert exc.value.code == "SSRF_BLOCKED"


def test_unsafe_scheme_blocked(config: RedAgentConfig) -> None:
    g = TargetGuardrails(config)
    with pytest.raises(GuardrailViolation) as exc:
        g.validate(Target(type=TargetType.URL, value="file:///etc/passwd"))
    assert exc.value.code == "UNSAFE_SCHEME"


def test_out_of_scope_blocked(config: RedAgentConfig) -> None:
    g = TargetGuardrails(config)
    with pytest.raises(GuardrailViolation) as exc:
        g.validate(Target(type=TargetType.URL, value="http://other.com"))
    assert exc.value.code == "OUT_OF_SCOPE"


def test_in_scope_subdomain_passes(config: RedAgentConfig, monkeypatch) -> None:
    import socket

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(0, 0, 0, "", ("93.184.216.34", 0))],
    )
    g = TargetGuardrails(config)
    g.validate(Target(type=TargetType.URL, value="http://api.example.com"))


def test_bug_bounty_bypasses_scope(monkeypatch) -> None:
    import socket

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(0, 0, 0, "", ("8.8.8.8", 0))],
    )
    cfg = RedAgentConfig(scope_allowlist=[], bug_bounty_mode=True)
    g = TargetGuardrails(cfg)
    g.validate(Target(type=TargetType.URL, value="http://random-target.com"))


def test_intensity_intrusive_requires_hitl(config: RedAgentConfig) -> None:
    pipe = GuardrailPipeline(config)
    request = ScanRequest(
        target=Target(type=TargetType.HOSTNAME, value="example.com"),
        scanners=["sqlmap"],
        intensity=ScanIntensity.INTRUSIVE,
        requested_by="test",
    )
    decision = pipe.intensity.evaluate(request)
    assert decision.needs_human_approval is True
    assert decision.allowed is True


def test_sqlmap_rejected_when_not_intrusive(config: RedAgentConfig) -> None:
    pipe = GuardrailPipeline(config)
    request = ScanRequest(
        target=Target(type=TargetType.HOSTNAME, value="example.com"),
        scanners=["sqlmap"],
        intensity=ScanIntensity.PASSIVE,
        requested_by="test",
    )
    decision = pipe.intensity.evaluate(request)
    assert "SQLMAP_REQUIRES_INTRUSIVE_INTENSITY" in decision.violations
    assert decision.allowed is False
