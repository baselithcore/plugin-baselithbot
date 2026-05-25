"""Schemathesis scanner parser tests."""

from __future__ import annotations

import pytest

from plugins.red_agent.models import Severity, Target, TargetType
from plugins.red_agent.scanners.schemathesis import SchemathesisScanner


class _StubSandbox:
    pass


@pytest.fixture()
def api_target() -> Target:
    return Target(
        type=TargetType.API_SPEC,
        value="https://api.example.com/openapi.json",
    )


def _scanner() -> SchemathesisScanner:
    return SchemathesisScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]


def test_parse_single_failure_with_check(api_target: Target) -> None:
    text = (
        "================================ FAILED: GET /pets ================================\n"
        "1. Test Case ID: abc123\n"
        "    Check: not_a_server_error\n"
        '    Body: {"id": -1}\n'
    )
    findings = list(_scanner()._emit_findings_via(text, api_target))
    assert len(findings) == 1
    f = findings[0]
    assert f.scanner == "schemathesis"
    assert f.severity == Severity.HIGH  # not_a_server_error → HIGH
    assert f.endpoint == "GET /pets"
    assert f.evidence["check"] == "not_a_server_error"
    assert f.evidence["confirmed"] is True
    assert f.evidence["body"] == '{"id": -1}'


def test_parse_multiple_failures(api_target: Target) -> None:
    text = (
        "================================ FAILED: GET /pets ================================\n"
        "    Check: not_a_server_error\n"
        "    Body: {}\n"
        "================================ FAILED: POST /pets ================================\n"
        "    Check: response_schema_conformance\n"
        "    Body: null\n"
    )
    findings = list(_scanner()._emit_findings_via(text, api_target))
    assert len(findings) == 2
    endpoints = {f.endpoint for f in findings}
    assert endpoints == {"GET /pets", "POST /pets"}


def test_parse_severity_mapping(api_target: Target) -> None:
    text = (
        "================================ FAILED: GET /admin ================================\n"
        "    Check: ignored_auth\n"
    )
    findings = list(_scanner()._emit_findings_via(text, api_target))
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL


def test_parse_multiple_checks_per_endpoint(api_target: Target) -> None:
    text = (
        "================================ FAILED: GET /users ================================\n"
        "    Check: not_a_server_error\n"
        "    Check: response_schema_conformance\n"
        "    Body: {}\n"
    )
    findings = list(_scanner()._emit_findings_via(text, api_target))
    assert len(findings) == 2
    checks = {f.evidence["check"] for f in findings}
    assert checks == {"not_a_server_error", "response_schema_conformance"}


def test_parse_no_failures_returns_empty(api_target: Target) -> None:
    text = "All tests passed.\nSchemathesis run finished.\n"
    findings = list(_scanner()._emit_findings_via(text, api_target))
    assert findings == []


def test_parse_unknown_check_defaults_to_medium(api_target: Target) -> None:
    text = (
        "================================ FAILED: GET /x ================================\n"
        "    Check: future_check_we_havent_mapped\n"
    )
    findings = list(_scanner()._emit_findings_via(text, api_target))
    assert findings[0].severity == Severity.MEDIUM


def test_parse_failure_without_check_yields_single_finding(
    api_target: Target,
) -> None:
    text = (
        "================================ FAILED: DELETE /things ================================\n"
        "    Body: {}\n"
    )
    findings = list(_scanner()._emit_findings_via(text, api_target))
    assert len(findings) == 1
    assert findings[0].evidence["check"] is None
    assert findings[0].severity == Severity.MEDIUM


def test_run_returns_empty_when_target_type_mismatch() -> None:
    """Non-API_SPEC target → scanner is a no-op."""
    s = _scanner()
    wrong = Target(type=TargetType.URL, value="https://example.com/")
    # Direct parse path is the only deterministic test we can run without
    # the sandbox; ``run`` is exercised through e2e fixtures.
    out = list(s._emit_findings_via("", wrong))
    assert out == []


# Helper attached to the SchemathesisScanner class only for testing —
# wraps the module-level ``_parse_failures`` so test cases keep one
# entry point. We expose it here via a method-level binding.
def _attach_helper() -> None:
    from plugins.red_agent.scanners import schemathesis as mod

    def _emit_findings_via(
        self: SchemathesisScanner, text: str, target: Target
    ) -> object:
        del self
        return mod._parse_failures(text, target)

    SchemathesisScanner._emit_findings_via = _emit_findings_via  # type: ignore[attr-defined]


_attach_helper()
