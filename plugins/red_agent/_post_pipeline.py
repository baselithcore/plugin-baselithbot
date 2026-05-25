"""Suppression-side helpers extracted from ``_agent_helpers.py``.

Hosts the optional enrichment steps that *can drop* findings (VEX,
reachability) so ``_agent_helpers.py`` stays under the 500-line cap and
the suppression policies live next to each other for review.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding, TargetType

if TYPE_CHECKING:
    from plugins.red_agent.audit import AuditLogger
    from plugins.red_agent.enrichers import (
        ComplianceMapperEnricher,
        ExploitValidationEnricher,
        ReachabilityEnricher,
        RiskScoringEnricher,
        VexEnricher,
    )
    from plugins.red_agent.models import ScanRequest

_logger = get_logger(__name__)


async def run_reachability(
    *,
    reachability: "ReachabilityEnricher | None",
    audit: "AuditLogger",
    scan_id: UUID,
    findings: list[Finding],
    request: "ScanRequest",
) -> list[Finding]:
    """Annotate / suppress SCA findings using a source-tree reachability check.

    The repo path is resolved from ``Target.metadata['repo_path']``
    when present, falling back to ``Target.value`` for ``REPO`` / ``IAC``
    target types. When no usable path is available the enricher returns
    the input unchanged. Fail-open: any error returns the input list.
    """
    if reachability is None or not reachability.enabled or not findings:
        return findings
    target = request.target
    repo_path: str | None = None
    if isinstance(target.metadata, dict):
        meta_path = target.metadata.get("repo_path")
        if isinstance(meta_path, str) and meta_path:
            repo_path = meta_path
    if repo_path is None and target.type in (TargetType.REPO, TargetType.IAC):
        repo_path = target.value
    if repo_path is None:
        return findings
    try:
        kept, suppressed = reachability.enrich(findings, repo_root=Path(repo_path))
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "red_agent.reachability.enrich_failed",
            extra={"scan_id": str(scan_id), "err": str(exc)},
        )
        return findings
    if suppressed:
        await audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.reachability_suppressed",
            payload={
                "input": len(findings),
                "kept": len(kept),
                "suppressed": len(suppressed),
                "packages": sorted(
                    {
                        (f.evidence or {}).get("package", "")
                        for f in suppressed
                        if isinstance(f.evidence, dict)
                    }
                    - {""}
                ),
            },
        )
    return kept


async def run_risk_scoring(
    *,
    risk_scorer: "RiskScoringEnricher | None",
    findings: list[Finding],
    request: "ScanRequest",
) -> list[Finding]:
    """Compute the unified VPR-style risk score per finding.

    Reads asset criticality + exposure from ``Target.metadata`` so the
    multiplier chain reflects the operator's deployment context. Pure
    in-memory transform; no I/O, no audit event.
    """
    if risk_scorer is None or not risk_scorer.enabled or not findings:
        return findings
    asset_metadata: dict[str, object] = {}
    if isinstance(request.target.metadata, dict):
        asset_metadata = dict(request.target.metadata)
    try:
        return risk_scorer.enrich(findings, asset_metadata=asset_metadata)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("red_agent.risk_scorer.failed", extra={"err": str(exc)})
        return findings


async def run_compliance_mapping(
    *,
    compliance: "ComplianceMapperEnricher | None",
    findings: list[Finding],
) -> list[Finding]:
    """Annotate findings with compliance control IDs (CIS/PCI/NIST/ISO/SOC2).

    Pure in-memory transform; static lookup table + scanner-passthrough.
    """
    if compliance is None or not compliance.enabled or not findings:
        return findings
    try:
        return compliance.enrich(findings)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("red_agent.compliance_mapper.failed", extra={"err": str(exc)})
        return findings


async def run_exploit_validation(
    *,
    validator: "ExploitValidationEnricher | None",
    audit: "AuditLogger",
    scan_id: UUID,
    findings: list[Finding],
    request: "ScanRequest",
) -> list[Finding]:
    """Re-issue PoC traffic to confirm exploitability of detection findings.

    Gated behind ``exploit_validation_enabled``; the enricher itself
    enforces the intrusive-only intensity gate. Records a single audit
    summary event when at least one finding's status changed. Fail-
    open: any unexpected error returns the input list unchanged.
    """
    if validator is None or not validator.enabled or not findings:
        return findings
    try:
        result = await validator.enrich(findings, intensity=request.intensity)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "red_agent.exploit_validator.failed",
            extra={"scan_id": str(scan_id), "err": str(exc)},
        )
        return findings

    summary: dict[str, int] = {}
    for f in result:
        if f.validated_at is None:
            continue
        summary[f.validation_status.value] = (
            summary.get(f.validation_status.value, 0) + 1
        )
    if summary:
        await audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.exploit_validated",
            payload={"input": len(findings), **summary},
        )
    return result


async def run_vex_suppression(
    *,
    vex: "VexEnricher | None",
    audit: "AuditLogger",
    scan_id: UUID,
    findings: list[Finding],
) -> list[Finding]:
    """Drop findings whose CVE is suppressed by an operator-supplied VEX doc.

    VEX statements (OpenVEX 0.2.0 / CycloneDX VEX 1.6) are vendor or
    operator attestations that a CVE does not apply to the deployed
    artifact. Honoring them upstream of the LLM/dedup chain saves cost
    and keeps the canonical reason for the suppression in the audit log.
    Fail-open: any error returns the input list unchanged.
    """
    if vex is None or not vex.enabled or not findings:
        return findings
    try:
        kept, suppressed = vex.enrich(findings)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "red_agent.vex.enrich_failed",
            extra={"scan_id": str(scan_id), "err": str(exc)},
        )
        return findings
    if suppressed:
        await audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.vex_suppressed",
            payload={
                "input": len(findings),
                "kept": len(kept),
                "suppressed": len(suppressed),
                "cves": sorted({f.cve for f in suppressed if f.cve}),
            },
        )
    return kept
