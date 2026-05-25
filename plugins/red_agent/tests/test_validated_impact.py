"""Validated-impact filter behavior tests (RedAgent._apply_validated_impact)."""

from __future__ import annotations

from plugins.red_agent.agent import RedAgent
from plugins.red_agent.approvals import ApprovalRegistry
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.events import ScanEventBus
from plugins.red_agent.models import Finding, Severity


class _Stub:
    pass


def _agent(*, validated: bool, min_cvss: float = 4.0) -> RedAgent:
    cfg = RedAgentConfig(
        validated_impact_only=validated,
        validated_impact_min_cvss=min_cvss,
        scope_allowlist=["example.com"],
    )
    return RedAgent(
        config=cfg,
        persistence=_Stub(),  # type: ignore[arg-type]
        graph=_Stub(),  # type: ignore[arg-type]
        audit=_Stub(),  # type: ignore[arg-type]
        sandbox=_Stub(),  # type: ignore[arg-type]
        events=ScanEventBus(),
        approvals=ApprovalRegistry(),
    )


def _fixture_findings() -> list[Finding]:
    return [
        Finding(
            scanner="nuclei",
            title="info-noise",
            description="d",
            severity=Severity.INFO,
            target="example.com",
        ),
        Finding(
            scanner="nuclei",
            title="medium-low-cvss",
            description="d",
            severity=Severity.MEDIUM,
            cvss_score=3.0,
            target="example.com",
        ),
        Finding(
            scanner="nuclei",
            title="medium-high-cvss",
            description="d",
            severity=Severity.MEDIUM,
            cvss_score=7.5,
            target="example.com",
        ),
        Finding(
            scanner="nuclei",
            title="critical-rce",
            description="d",
            severity=Severity.CRITICAL,
            target="example.com",
        ),
        Finding(
            scanner="sqlmap",
            title="confirmed-sqli",
            description="d",
            severity=Severity.LOW,
            target="example.com",
            evidence={"confirmed": True},
        ),
    ]


def test_disabled_returns_all_findings() -> None:
    a = _agent(validated=False)
    fs = _fixture_findings()
    assert a._apply_validated_impact(fs) == fs


def test_enabled_drops_info_and_low_without_confirmation() -> None:
    a = _agent(validated=True, min_cvss=5.0)
    kept = a._apply_validated_impact(_fixture_findings())
    titles = {f.title for f in kept}
    assert titles == {"medium-high-cvss", "critical-rce", "confirmed-sqli"}


def test_high_severity_always_kept() -> None:
    a = _agent(validated=True, min_cvss=10.0)
    kept = a._apply_validated_impact(
        [
            Finding(
                scanner="x",
                title="high",
                description="d",
                severity=Severity.HIGH,
                target="t",
            )
        ]
    )
    assert len(kept) == 1


def test_confirmed_evidence_overrides_low_severity() -> None:
    a = _agent(validated=True, min_cvss=10.0)
    kept = a._apply_validated_impact(
        [
            Finding(
                scanner="sqlmap",
                title="x",
                description="d",
                severity=Severity.LOW,
                target="t",
                evidence={"confirmed": True},
            )
        ]
    )
    assert len(kept) == 1
