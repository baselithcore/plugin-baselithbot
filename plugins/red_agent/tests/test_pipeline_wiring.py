"""Pipeline-wiring regression tests.

Confirms the orchestrator dispatches the four threat-intel enrichers
and the exploit validator added in the recent expansion. The tests
exercise the same code path the live agent does (``run_threat_intel_enrichers``
+ ``run_post_scanner_pipeline``) but stub the enrichers so the
post-pipeline can run without external services.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from plugins.red_agent._agent_helpers import (
    run_post_scanner_pipeline,
    run_threat_intel_enrichers,
)
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    ScanRequest,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.planner import PlannerStep


class _StubAudit:
    """Minimal AuditLogger surface — every coroutine swallows its args."""

    async def record(self, **_kwargs: Any) -> None:
        return None


class _StubEnricher:
    """Mimics the duck-typed shape of every threat-intel enricher.

    ``enabled`` plus a coroutine ``enrich(findings)`` is all the
    pipeline reads.
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.enrich = AsyncMock(side_effect=self._noop)

    async def _noop(self, findings: list[Finding]) -> list[Finding]:
        return findings


def _request() -> ScanRequest:
    return ScanRequest(
        target=Target(type=TargetType.URL, value="https://example.test"),
        intensity=ScanIntensity.PASSIVE,
        scanners=("nuclei",),
        requested_by="tests",
    )


def _step(req: ScanRequest) -> PlannerStep:
    return PlannerStep(
        target=req.target,
        intensity=req.intensity,
        scanners=list(req.scanners),
    )


@pytest.mark.asyncio
async def test_run_threat_intel_enrichers_dispatches_new_sources() -> None:
    findings = [
        Finding(
            scanner="nmap",
            title="t",
            description="",
            severity=Severity.MEDIUM,
            target="8.8.8.8",
        )
    ]
    vt = _StubEnricher()
    sh = _StubEnricher()
    cs = _StubEnricher()
    otx = _StubEnricher()

    await run_threat_intel_enrichers(
        epss_kev=None,
        attack_mapper=None,
        audit=_StubAudit(),
        scan_id=uuid4(),
        findings=findings,
        virustotal=vt,
        shodan=sh,
        censys=cs,
        otx=otx,
    )

    assert vt.enrich.await_count == 1
    assert sh.enrich.await_count == 1
    assert cs.enrich.await_count == 1
    assert otx.enrich.await_count == 1


@pytest.mark.asyncio
async def test_run_threat_intel_enrichers_skips_disabled_sources() -> None:
    findings = [
        Finding(
            scanner="nmap",
            title="t",
            description="",
            severity=Severity.MEDIUM,
            target="8.8.8.8",
        )
    ]
    vt = _StubEnricher(enabled=False)

    await run_threat_intel_enrichers(
        epss_kev=None,
        attack_mapper=None,
        audit=_StubAudit(),
        scan_id=uuid4(),
        findings=findings,
        virustotal=vt,
    )

    assert vt.enrich.await_count == 0


@pytest.mark.asyncio
async def test_run_post_scanner_pipeline_routes_to_exploit_validator() -> None:
    request = _request()
    step = _step(request)
    findings = [
        Finding(
            scanner="nuclei",
            title="t",
            description="",
            severity=Severity.HIGH,
            target=request.target.value,
        )
    ]
    validator = AsyncMock()
    validator.enabled = True
    validator.enrich = AsyncMock(return_value=findings)

    fresh, dups = await run_post_scanner_pipeline(
        scanner_findings=findings,
        fp_classifier=None,
        triage=None,
        dedup=None,
        audit=_StubAudit(),
        scan_id=uuid4(),
        request=request,
        step=step,
        validated_only=False,
        validated_min_cvss=0.0,
        exploit_validator=validator,
    )

    assert validator.enrich.await_count == 1
    assert len(fresh) == 1
    assert dups == []


@pytest.mark.asyncio
async def test_run_post_scanner_pipeline_omits_validator_when_none() -> None:
    request = _request()
    step = _step(request)
    findings = [
        Finding(
            scanner="nuclei",
            title="t",
            description="",
            severity=Severity.HIGH,
            target=request.target.value,
        )
    ]

    fresh, dups = await run_post_scanner_pipeline(
        scanner_findings=findings,
        fp_classifier=None,
        triage=None,
        dedup=None,
        audit=_StubAudit(),
        scan_id=uuid4(),
        request=request,
        step=step,
        validated_only=False,
        validated_min_cvss=0.0,
    )

    assert len(fresh) == 1
    assert dups == []
