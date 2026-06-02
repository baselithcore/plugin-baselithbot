"""Scanner-dispatch and finding-shaping helpers extracted from ``agent.py``.

None of these depend on ``RedAgent`` instance state — everything they
need is passed in explicitly.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding, Severity

if TYPE_CHECKING:
    from plugins.red_agent.audit import AuditLogger
    from plugins.red_agent.models import ScanRequest

_logger = get_logger(__name__)


async def filter_request_scanners(
    *,
    request: "ScanRequest",
    enabled_scanners: list[str],
    audit: "AuditLogger",
    scan_id: "UUID",
) -> "ScanRequest":
    """Drop scanners not in ``enabled_scanners`` from a submitted ScanRequest.

    Audits the change, returns a new ``ScanRequest`` with the filtered list.
    Falls back to the full policy list when the intersection is empty so
    the scan does not silently produce zero work — except for target
    types whose only meaningful adapter is type-specific. Substituting a
    network scanner for a binary-sample scan would dispatch nmap/nuclei
    against a 64-character SHA-256 string and waste minutes timing out.
    """
    from plugins.red_agent.models import TargetType

    if not request.scanners:
        return request
    enabled = set(enabled_scanners)
    kept = [s for s in request.scanners if s in enabled]
    dropped = [s for s in request.scanners if s not in enabled]
    if dropped:
        await audit.record(
            scan_id=scan_id,
            actor=request.requested_by,
            event="scan.scanners_filtered_by_policy",
            payload={
                "requested": list(request.scanners),
                "kept": kept,
                "dropped": dropped,
            },
        )
    # Type-specific scanners that must not be substituted away even when
    # the operator's policy excludes them. Binary samples require the
    # static analyzer; nothing else can read a quarantined PE.
    pinned_for_type: dict[TargetType, str] = {
        TargetType.BINARY: "binary_analyzer",
    }
    pinned = pinned_for_type.get(request.target.type)
    if pinned and pinned in request.scanners:
        return request.model_copy(update={"scanners": [pinned]})
    if not kept:
        kept = list(enabled_scanners)
    return request.model_copy(update={"scanners": kept})


async def execute_scanner(
    *,
    scanner_name: str,
    target: Any,
    intensity: Any,
    sandbox: Any,
    timeouts: dict[str, int],
    fallback_timeout: int,
    output_max_bytes: int,
) -> list[Finding]:
    """Resolve a scanner from the registry, run it, and bound its output.

    Centralises the scanner lookup + intensity check + payload truncation
    so ``RedAgent`` stays under the 500-line file cap and unit tests can
    exercise the full pipeline without the orchestrator state.
    """
    from plugins.red_agent.scanners import REGISTRY
    from plugins.red_agent.scanners.base import Scanner

    if scanner_name not in REGISTRY:
        _logger.warning("unknown scanner", extra={"name": scanner_name})
        return []
    cls = REGISTRY[scanner_name]
    timeout = timeouts.get(scanner_name, fallback_timeout)
    scanner: Scanner = cls(sandbox, timeout=timeout)
    if not scanner.supports(intensity):
        _logger.info(
            "scanner skipped (intensity not supported)",
            extra={"scanner": scanner_name, "intensity": intensity.value},
        )
        return []
    findings = await scanner.run(target, intensity)
    for f in findings:
        f.raw = truncate_payload(f.raw, output_max_bytes)
        f.evidence = truncate_payload(f.evidence, output_max_bytes)
    return findings


def truncate_payload(payload: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    """Bound the bytes of a finding's evidence/raw payload.

    Walks string leaves and clips them once the running total reaches
    ``max_bytes``. The truncation marker preserves auditability — operators
    can fetch the full output from the audit log if needed.
    """
    try:
        encoded = json.dumps(payload, default=str).encode()
    except (TypeError, ValueError):
        return {"_truncated": True, "_reason": "non_serializable"}

    total = len(encoded)
    if total <= max_bytes:
        return payload

    return {
        "_truncated": True,
        "_original_bytes": total,
        "_head": encoded[:max_bytes].decode(errors="replace"),
    }


def scanner_error_finding(
    *, scanner_name: str, target: str, err: BaseException
) -> Finding:
    """Convert a scanner crash into a low-severity ``Finding`` so the operator sees it.

    Without this, scanner exceptions are only logged — the scan completes
    with zero findings and the UI lights up nothing. We surface a minimal,
    clearly-marked record so the failure is visible and triageable. The
    ``evidence`` payload carries the exception details for debugging.
    """
    message = str(err) or err.__class__.__name__
    return Finding(
        scanner=scanner_name,
        title=f"Scanner {scanner_name} failed to execute",
        description=(
            f"The {scanner_name} adapter raised an exception while scanning "
            f"{target}. No findings were collected from this scanner; results "
            "from other scanners in the same run are unaffected."
        ),
        severity=Severity.INFO,
        target=target,
        evidence={
            "scanner_failure": True,
            "exception_type": type(err).__name__,
            "message": message[:500],
        },
        remediation=(
            "Check the scanner image is reachable (docker pull), the sandbox "
            "provider is configured (RED_AGENT_SANDBOX_PROVIDER), or enable "
            "RED_AGENT_USE_MOCK_SCANNERS=true for a development workflow."
        ),
    )


def apply_validated_impact(
    findings: list[Finding], *, enabled: bool, min_cvss: float
) -> list[Finding]:
    """Drop findings without proven exploitable impact when enabled.

    High-confidence filter. A finding survives if either
    (a) severity ≥ HIGH, or (b) ``cvss_score >= min_cvss``, or
    (c) evidence carries an explicit ``confirmed`` flag set by the
    scanner adapter (e.g. sqlmap's confirmed SQLi).
    """
    if not enabled:
        return findings
    kept: list[Finding] = []
    for f in findings:
        if f.severity in (Severity.HIGH, Severity.CRITICAL):
            kept.append(f)
            continue
        if f.cvss_score is not None and f.cvss_score >= min_cvss:
            kept.append(f)
            continue
        if isinstance(f.evidence, dict) and f.evidence.get("confirmed"):
            kept.append(f)
            continue
    return kept
