"""Tests for VPR risk scorer + compliance mapper enrichers."""

from __future__ import annotations

import pytest

from plugins.red_agent.enrichers.compliance_mapper import (
    ComplianceMapperEnricher,
    coverage_summary,
)
from plugins.red_agent.enrichers.risk_scorer import RiskScoringEnricher
from plugins.red_agent.models import Finding, Severity


def _f(**kwargs: object) -> Finding:
    base: dict[str, object] = {
        "scanner": "trivy",
        "title": "demo",
        "description": "demo",
        "severity": Severity.MEDIUM,
        "target": "example.com",
    }
    base.update(kwargs)
    return Finding(**base)  # type: ignore[arg-type]


# --- Risk scorer ------------------------------------------------------


def test_risk_scorer_disabled_passthrough() -> None:
    s = RiskScoringEnricher(enabled=False)
    f = _f(cvss_score=9.0)
    s.enrich([f])
    assert f.risk_score is None


def test_risk_scorer_uses_cvss_as_base() -> None:
    s = RiskScoringEnricher(enabled=True)
    f = _f(cvss_score=7.0)
    s.enrich([f])
    # No multipliers active → score == base
    assert f.risk_score == 7.0
    assert f.evidence["risk_band"] == "high"


def test_risk_scorer_severity_fallback_when_no_cvss() -> None:
    s = RiskScoringEnricher(enabled=True)
    f = _f(severity=Severity.HIGH)
    s.enrich([f])
    # Severity HIGH → base 7.5
    assert f.risk_score == 7.5


def test_risk_scorer_kev_multiplier() -> None:
    s = RiskScoringEnricher(enabled=True, kev_multiplier=1.5)
    f = _f(cvss_score=6.0, evidence={"kev_listed": True})
    s.enrich([f])
    assert f.risk_score == round(6.0 * 1.5, 2)
    # 9.0 lands at the critical band threshold.
    assert f.evidence["risk_band"] == "critical"


def test_risk_scorer_high_epss_multiplier() -> None:
    s = RiskScoringEnricher(enabled=True, max_epss_multiplier=1.5)
    f = _f(cvss_score=6.0, evidence={"epss_score": 1.0})
    s.enrich([f])
    assert f.risk_score == round(6.0 * 1.5, 2)


def test_risk_scorer_unreachable_lowers_score() -> None:
    s = RiskScoringEnricher(enabled=True)
    f = _f(cvss_score=6.0, evidence={"reachable": False})
    s.enrich([f])
    assert f.risk_score == round(6.0 * 0.5, 2)
    assert f.evidence["risk_band"] == "low"


def test_risk_scorer_reachable_boosts_score() -> None:
    s = RiskScoringEnricher(enabled=True)
    f = _f(cvss_score=6.0, evidence={"reachable": True})
    s.enrich([f])
    assert f.risk_score == round(6.0 * 1.2, 2)


def test_risk_scorer_asset_criticality_and_exposure() -> None:
    s = RiskScoringEnricher(enabled=True)
    f = _f(cvss_score=5.0)
    s.enrich(
        [f],
        asset_metadata={"asset_criticality": "crown_jewel", "exposure": "internet"},
    )
    expected = round(5.0 * 1.5 * 1.2, 2)
    assert f.risk_score == expected


def test_risk_scorer_clamped_to_10() -> None:
    s = RiskScoringEnricher(enabled=True)
    f = _f(
        cvss_score=10.0,
        evidence={"kev_listed": True, "epss_score": 1.0, "reachable": True},
    )
    s.enrich(
        [f], asset_metadata={"asset_criticality": "crown_jewel", "exposure": "internet"}
    )
    assert f.risk_score == 10.0
    assert f.evidence["risk_band"] == "critical"


def test_risk_band_thresholds() -> None:
    s = RiskScoringEnricher(enabled=True)
    cases = [
        (1.0, "info"),
        (3.0, "low"),
        (5.0, "medium"),
        (8.0, "high"),
        (9.5, "critical"),
    ]
    for cvss, band in cases:
        f = _f(cvss_score=cvss)
        s.enrich([f])
        assert f.evidence["risk_band"] == band, f"cvss={cvss}"


# --- Compliance mapper ------------------------------------------------


def test_compliance_mapper_disabled_passthrough() -> None:
    m = ComplianceMapperEnricher(enabled=False)
    f = _f(cwe="CWE-79")
    m.enrich([f])
    assert f.controls == []


def test_compliance_mapper_cwe_lookup_xss() -> None:
    m = ComplianceMapperEnricher(enabled=True)
    f = _f(cwe="CWE-79", severity=Severity.HIGH)
    m.enrich([f])
    assert any(c.startswith("CIS-") for c in f.controls)
    assert any(c.startswith("PCI-") for c in f.controls)
    assert any(c.startswith("NIST-") for c in f.controls)


def test_compliance_mapper_severity_floor_for_high() -> None:
    m = ComplianceMapperEnricher(enabled=True)
    f = _f(cwe=None, severity=Severity.CRITICAL)
    m.enrich([f])
    assert "CIS-7" in f.controls


def test_compliance_mapper_no_floor_for_low() -> None:
    m = ComplianceMapperEnricher(enabled=True)
    f = _f(cwe=None, severity=Severity.LOW)
    m.enrich([f])
    assert f.controls == []


def test_compliance_mapper_scanner_passthrough_checkov() -> None:
    m = ComplianceMapperEnricher(enabled=True)
    f = _f(
        scanner="checkov",
        cwe=None,
        severity=Severity.MEDIUM,
        evidence={"check_id": "CKV_AWS_18"},
    )
    m.enrich([f])
    assert "CHECKOV-CKV_AWS_18" in f.controls


def test_compliance_mapper_scanner_passthrough_prowler_dict() -> None:
    m = ComplianceMapperEnricher(enabled=True)
    f = _f(
        scanner="prowler",
        cwe=None,
        severity=Severity.MEDIUM,
        evidence={"compliance": {"CIS-1.5": "2.1.1", "PCI-3.2": "1.2.3"}},
    )
    m.enrich([f])
    assert any("CIS-1.5-2.1.1" in c.replace(" ", "_") for c in f.controls)


def test_compliance_mapper_dedup_controls() -> None:
    m = ComplianceMapperEnricher(enabled=True)
    f = _f(
        cwe="CWE-79",
        severity=Severity.HIGH,
        evidence={"compliance": ["CIS-16.10"]},  # already in CWE-79 mapping
    )
    m.enrich([f])
    cis_count = sum(1 for c in f.controls if c == "CIS-16.10")
    assert cis_count == 1


def test_coverage_summary_aggregates_by_control() -> None:
    f1 = _f(cwe="CWE-79", severity=Severity.HIGH)
    f2 = _f(cwe="CWE-79", severity=Severity.MEDIUM)
    f3 = _f(cwe="CWE-89", severity=Severity.HIGH)
    m = ComplianceMapperEnricher(enabled=True)
    m.enrich([f1, f2, f3])
    cov = coverage_summary([f1, f2, f3], framework_prefix="PCI-")
    assert all(k.startswith("PCI-") for k in cov)
    # CWE-79 maps to PCI-6.5.7; CWE-89 maps to PCI-6.5.1
    assert "PCI-6.5.7" in cov
    assert cov["PCI-6.5.7"]["count"] == 2


# --- Pipeline helper integration -------------------------------------


@pytest.mark.asyncio
async def test_run_risk_scoring_helper() -> None:
    from plugins.red_agent._post_pipeline import run_risk_scoring
    from plugins.red_agent.models import ScanRequest, Target, TargetType

    s = RiskScoringEnricher(enabled=True)
    request = ScanRequest(
        target=Target(
            type=TargetType.URL,
            value="https://crown.example.com",
            metadata={"asset_criticality": "crown_jewel", "exposure": "internet"},
        ),
        requested_by="op",
    )
    f = _f(cvss_score=5.0)
    out = await run_risk_scoring(risk_scorer=s, findings=[f], request=request)
    assert out[0].risk_score == round(5.0 * 1.5 * 1.2, 2)


@pytest.mark.asyncio
async def test_run_compliance_mapping_helper() -> None:
    from plugins.red_agent._post_pipeline import run_compliance_mapping

    m = ComplianceMapperEnricher(enabled=True)
    f = _f(cwe="CWE-89", severity=Severity.HIGH)
    out = await run_compliance_mapping(compliance=m, findings=[f])
    assert any(c.startswith("PCI-") for c in out[0].controls)
