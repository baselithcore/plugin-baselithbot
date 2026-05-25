"""Unit tests for the Sigma detection-hint enricher."""

from __future__ import annotations

from plugins.red_agent.enrichers.sigma_hints import SigmaHintEnricher
from plugins.red_agent.models import Finding, Severity


def _finding(cwe: str | None) -> Finding:
    return Finding(
        scanner="nuclei",
        title="t",
        description="d",
        severity=Severity.HIGH,
        target="https://example.com",
        cwe=cwe,
    )


def test_known_cwe_gets_detection_guidance() -> None:
    f = _finding("CWE-89")
    SigmaHintEnricher().enrich([f])
    guidance = f.evidence["detection_guidance"]
    assert guidance["logsource"] == {"product": "webserver", "category": "webserver"}
    assert "UNION SELECT" in guidance["detection"]
    assert "Parameterized queries / prepared statements" in guidance["mitigations"]


def test_unknown_cwe_left_alone() -> None:
    f = _finding("CWE-99999")
    SigmaHintEnricher().enrich([f])
    assert "detection_guidance" not in f.evidence


def test_no_cwe_left_alone() -> None:
    f = _finding(None)
    SigmaHintEnricher().enrich([f])
    assert "detection_guidance" not in f.evidence


def test_disabled_enricher_is_noop() -> None:
    f = _finding("CWE-89")
    SigmaHintEnricher(enabled=False).enrich([f])
    assert "detection_guidance" not in f.evidence


def test_case_insensitive_cwe() -> None:
    f = _finding("cwe-89")
    SigmaHintEnricher().enrich([f])
    assert "detection_guidance" in f.evidence


def test_multiple_findings_independent() -> None:
    a = _finding("CWE-89")
    b = _finding("CWE-918")
    c = _finding(None)
    SigmaHintEnricher().enrich([a, b, c])
    assert "UNION SELECT" in a.evidence["detection_guidance"]["detection"]
    assert "metadata" in b.evidence["detection_guidance"]["detection"]
    assert "detection_guidance" not in c.evidence
