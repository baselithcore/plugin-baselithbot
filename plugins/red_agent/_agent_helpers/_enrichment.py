"""Enrichment-pipeline helpers extracted from ``agent.py``.

None of these depend on ``RedAgent`` instance state — everything they
need is passed in explicitly.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

from core.observability.logging import get_logger
from plugins.red_agent._agent_helpers._scanners import apply_validated_impact
from plugins.red_agent._post_pipeline import (
    run_compliance_mapping,
    run_exploit_validation,
    run_reachability,
    run_risk_scoring,
    run_vex_suppression,
)
from plugins.red_agent.models import Finding, Target

if TYPE_CHECKING:
    from plugins.red_agent.audit import AuditLogger
    from plugins.red_agent.enrichers import (
        AttackMapperEnricher,
        ComplianceMapperEnricher,
        EpssKevEnricher,
        GreyNoiseEnricher,
        OSVEnricher,
        ReachabilityEnricher,
        RiskScoringEnricher,
        VexEnricher,
    )
    from plugins.red_agent.ml import (
        FPClassifierService,
        LLMTriageService,
        SemanticDedupService,
    )
    from plugins.red_agent.models import ScanRequest
    from plugins.red_agent.planner import PlannerStep

_logger = get_logger(__name__)


def _sigma_singleton() -> "SigmaHintEnricher":
    """Module-level singleton — pure local CWE lookup, no I/O."""
    global _SIGMA_INSTANCE
    if _SIGMA_INSTANCE is None:
        from plugins.red_agent.enrichers.sigma_hints import (
            SigmaHintEnricher as _SigmaCls,
        )

        _SIGMA_INSTANCE = _SigmaCls()
    return _SIGMA_INSTANCE


_SIGMA_INSTANCE: "SigmaHintEnricher | None" = None

if TYPE_CHECKING:
    from plugins.red_agent.enrichers.sigma_hints import SigmaHintEnricher


async def run_post_scanner_pipeline(
    *,
    scanner_findings: list[Finding],
    fp_classifier: "FPClassifierService | None",
    triage: "LLMTriageService | None",
    dedup: "SemanticDedupService | None",
    audit: "AuditLogger",
    scan_id: "UUID",
    request: "ScanRequest",
    step: "PlannerStep",
    validated_only: bool,
    validated_min_cvss: float,
    epss_kev: "EpssKevEnricher | None" = None,
    attack_mapper: "AttackMapperEnricher | None" = None,
    vex: "VexEnricher | None" = None,
    reachability: "ReachabilityEnricher | None" = None,
    risk_scorer: "RiskScoringEnricher | None" = None,
    compliance: "ComplianceMapperEnricher | None" = None,
    osv: "OSVEnricher | None" = None,
    greynoise: "GreyNoiseEnricher | None" = None,
    virustotal: "Any | None" = None,
    shodan: "Any | None" = None,
    censys: "Any | None" = None,
    otx: "Any | None" = None,
    exploit_validator: "Any | None" = None,
) -> tuple[list[Finding], list[Finding]]:
    """Run the full enrichment chain on a single scanner's findings.

    Order matters:

    1. ``apply_validated_impact`` — cheap rule-based noise filter
    2. ``run_vex_suppression`` — vendor attestations override everything
       downstream (no point paying ML/LLM cost for a CVE the vendor
       already declared ``not_affected``)
    3. ``run_ml_fp_classifier`` — sub-millisecond ML pre-filter
    4. ``run_threat_intel_enrichers`` — annotate with EPSS/KEV/ATT&CK
       *before* triage so the LLM sees real-world exploitation context
    5. ``run_reachability`` — drop / annotate SCA findings whose
       vulnerable package is unreachable from source. Runs after threat
       intel so KEV listing can override the drop policy.
    6. ``run_risk_scoring`` — combine CVSS + EPSS + KEV + reachability
       + asset criticality into a single VPR-style score. Must run
       after every signal it consumes.
    7. ``run_compliance_mapping`` — annotate findings with control IDs
       across CIS / PCI / NIST / ISO27001 / SOC2 frameworks.
    8. ``run_llm_triage`` — LLM enrichment, only what survived M1
    9. ``run_semantic_dedupe`` — cross-scan dedup of survivors

    Returns ``(fresh, duplicates)`` ready for persistence + WS push.
    """
    findings = apply_validated_impact(
        scanner_findings, enabled=validated_only, min_cvss=validated_min_cvss
    )
    findings = await run_vex_suppression(
        vex=vex, audit=audit, scan_id=scan_id, findings=findings
    )
    findings = await run_ml_fp_classifier(
        classifier=fp_classifier, audit=audit, scan_id=scan_id, findings=findings
    )
    findings = await run_threat_intel_enrichers(
        epss_kev=epss_kev,
        attack_mapper=attack_mapper,
        audit=audit,
        scan_id=scan_id,
        findings=findings,
        osv=osv,
        greynoise=greynoise,
        virustotal=virustotal,
        shodan=shodan,
        censys=censys,
        otx=otx,
    )
    findings = await run_reachability(
        reachability=reachability,
        audit=audit,
        scan_id=scan_id,
        findings=findings,
        request=request,
    )
    findings = await run_risk_scoring(
        risk_scorer=risk_scorer, findings=findings, request=request
    )
    findings = await run_compliance_mapping(compliance=compliance, findings=findings)
    findings = await run_exploit_validation(
        validator=exploit_validator,
        audit=audit,
        scan_id=scan_id,
        findings=findings,
        request=request,
    )
    findings = await run_llm_triage(
        triage=triage,
        audit=audit,
        scan_id=scan_id,
        findings=findings,
        target=step.target,
    )
    return await run_semantic_dedupe(
        dedup=dedup,
        audit=audit,
        scan_id=scan_id,
        findings=findings,
        request=request,
        step=step,
    )


async def _safe_call(
    fn: Any,
    findings: list[Finding],
    audit: "AuditLogger",
    scan_id: "UUID",
    label: str,
) -> None:
    """Run a single enricher's ``enrich`` coroutine fail-open.

    Used by :func:`run_threat_intel_enrichers` to fan out HTTP-bound
    enrichers in parallel: any exception is logged and swallowed so
    one flaky upstream feed never blocks the others.
    """
    del audit, scan_id  # reserved for future per-enricher audit events
    try:
        await fn(findings)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(f"red_agent.enricher.{label}.failed", extra={"err": str(exc)})


async def run_threat_intel_enrichers(
    *,
    epss_kev: "EpssKevEnricher | None",
    attack_mapper: "AttackMapperEnricher | None",
    audit: "AuditLogger",
    scan_id: "UUID",
    findings: list[Finding],
    osv: "OSVEnricher | None" = None,
    greynoise: "GreyNoiseEnricher | None" = None,
    virustotal: "Any | None" = None,
    shodan: "Any | None" = None,
    censys: "Any | None" = None,
    otx: "Any | None" = None,
) -> list[Finding]:
    """Run EPSS/KEV + ATT&CK + OSV + GreyNoise enrichers; fail-open.

    HTTP-bound enrichers (EPSS/KEV, OSV, GreyNoise) fan out in parallel
    via :func:`asyncio.gather` since each one mutates ``Finding.evidence``
    independently. The local-only ATT&CK mapper runs first because it is
    a synchronous CWE lookup with no I/O.
    """
    if not findings:
        return findings
    if attack_mapper is not None and attack_mapper.enabled:
        try:
            findings = attack_mapper.enrich(findings)
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "red_agent.enricher.attack_mapper.failed",
                extra={"scan_id": str(scan_id), "err": str(exc)},
            )
    try:
        findings = _sigma_singleton().enrich(findings)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "red_agent.enricher.sigma_hints.failed",
            extra={"scan_id": str(scan_id), "err": str(exc)},
        )
    network_calls: list[Any] = []
    if osv is not None and osv.enabled:
        network_calls.append(_safe_call(osv.enrich, findings, audit, scan_id, "osv"))
    if greynoise is not None and greynoise.enabled:
        network_calls.append(
            _safe_call(greynoise.enrich, findings, audit, scan_id, "greynoise")
        )
    for enricher, label in (
        (virustotal, "virustotal"),
        (shodan, "shodan"),
        (censys, "censys"),
        (otx, "otx"),
    ):
        if enricher is not None and getattr(enricher, "enabled", False):
            network_calls.append(
                _safe_call(enricher.enrich, findings, audit, scan_id, label)
            )
    if network_calls:
        await asyncio.gather(*network_calls, return_exceptions=True)
    if epss_kev is not None and epss_kev.enabled:
        try:
            findings = await epss_kev.enrich(findings)
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "red_agent.enricher.epss_kev.failed",
                extra={"scan_id": str(scan_id), "err": str(exc)},
            )
        else:
            cves = sum(1 for f in findings if f.cve)
            if cves:
                await audit.record(
                    scan_id=scan_id,
                    actor="red_agent",
                    event="scan.threat_intel_enriched",
                    payload={"cve_count": cves, "total_findings": len(findings)},
                )
    return findings


async def run_ml_fp_classifier(
    *,
    classifier: "FPClassifierService | None",
    audit: "AuditLogger",
    scan_id: "UUID",
    findings: list[Finding],
) -> list[Finding]:
    """Apply the optional ML false-positive classifier.

    Runs ahead of the LLM triage so high-confidence FPs are filtered
    out before paying for an LLM round-trip. Fail-open: any error
    returns the input list unchanged.
    """
    if classifier is None or not classifier.enabled or not findings:
        return findings
    before = len(findings)
    try:
        kept = classifier.annotate_and_filter(findings)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "red_agent.ml.fp_classifier.failed",
            extra={"scan_id": str(scan_id), "err": str(exc)},
        )
        return findings
    dropped = before - len(kept)
    if dropped:
        await audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.ml_fp_filter",
            payload={"input": before, "kept": len(kept), "dropped": dropped},
        )
    return kept


async def run_llm_triage(
    *,
    triage: "LLMTriageService | None",
    audit: "AuditLogger",
    scan_id: "UUID",
    findings: list[Finding],
    target: object,
) -> list[Finding]:
    """Apply the optional LLM triage pass; record an audit event when it runs.

    Fail-open: any exception (or absent service) returns the input list
    unchanged so a misbehaving LLM never blocks the scan flow.
    """
    if triage is None or not triage.enabled or not findings:
        return findings
    if not isinstance(target, Target):
        return findings
    before = len(findings)
    try:
        triaged = await triage.triage(findings, target)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "red_agent.triage.failed",
            extra={"scan_id": str(scan_id), "err": str(exc)},
        )
        return findings
    dropped = before - len(triaged)
    if dropped or triaged != findings:
        await audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.llm_triage",
            payload={"input": before, "kept": len(triaged), "dropped": dropped},
        )
    return triaged


async def run_semantic_dedupe(
    *,
    dedup: "SemanticDedupService | None",
    audit: "AuditLogger",
    scan_id: "UUID",
    findings: list[Finding],
    request: "ScanRequest",
    step: "PlannerStep",
) -> tuple[list[Finding], list[Finding]]:
    """Apply the optional semantic-dedup pass.

    Returns ``(new, duplicates)``. Fail-open: any exception (or absent
    service) returns ``(findings, [])`` so dedup failures never drop
    real findings.
    """
    if dedup is None or not dedup.enabled or not findings:
        return findings, []
    target_value = (
        step.target.value if step.target is not None else request.target.value
    )
    try:
        result = await dedup.dedupe(
            scan_id=scan_id,
            findings=findings,
            tenant_id=request.tenant_id,
            target_value=target_value,
        )
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "red_agent.dedup.failed",
            extra={"scan_id": str(scan_id), "err": str(exc)},
        )
        return findings, []
    if result.duplicates:
        await audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.semantic_dedup",
            payload={"new": len(result.new), "duplicates": len(result.duplicates)},
        )
    return result.new, result.duplicates
