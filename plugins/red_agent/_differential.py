"""Differential-scan fingerprinting + cache lookup.

Skips re-running a scanner when its input fingerprint matches a recent
successful run. Cuts cost on monorepos / scheduled scans where most
targets do not change between cycles. Snyk and GitHub Code Scanning use
the same approach for SCA + code-scanning queues.

Fingerprint inputs:

* scanner name (so a config change to one scanner does not invalidate
  others)
* target type + value
* normalized scanner-relevant target metadata (commit SHA, image digest,
  IaC file tree hash) when available
* intensity (passive scans cannot be reused for an active run)

The fingerprint is a SHA-256 hex digest. The cache lives in
``red_agent_scan_fingerprints``; a hit within ``ttl_seconds`` causes the
orchestrator to skip the scanner and copy findings from the prior scan.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from plugins.red_agent.models import ScanIntensity, Target


@dataclass(slots=True, frozen=True)
class ScanFingerprint:
    """Stable identifier for a (target, scanner, intensity, inputs) tuple."""

    digest: str
    scanner: str

    @classmethod
    def compute(
        cls,
        *,
        target: Target,
        scanner: str,
        intensity: ScanIntensity,
        extra: dict[str, Any] | None = None,
    ) -> "ScanFingerprint":
        payload: dict[str, Any] = {
            "scanner": scanner,
            "intensity": intensity.value,
            "target_type": target.type.value,
            "target_value": target.value,
            "metadata": _normalize_metadata(target.metadata or {}),
        }
        if extra:
            payload["extra"] = _normalize_metadata(extra)
        # Sort keys → digest is order-independent.
        encoded = json.dumps(payload, sort_keys=True, default=str).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        return cls(digest=digest, scanner=scanner)


async def apply_cache(
    *,
    fingerprints: Any,
    persistence: Any,
    audit: Any,
    scan_id: Any,
    request: Any,
    step: Any,
    ttl_seconds: int,
    enabled: bool,
) -> tuple[list[str], list[Any]]:
    """Filter ``step.scanners`` against the fingerprint cache.

    Returns ``(scanners_to_run, reused_findings)``. Each cached hit
    triggers an audit ``scan.differential_skip`` entry and the prior
    scan's findings are copied (not re-persisted) into the current
    scan so the UI sees a complete picture without re-running the
    expensive scanner.
    """
    if (
        not enabled
        or fingerprints is None
        or not getattr(fingerprints, "available", False)
        or not step.scanners
    ):
        return list(step.scanners), []

    to_run: list[str] = []
    reused: list[Any] = []
    skipped: list[dict[str, str]] = []
    for scanner in step.scanners:
        fp = ScanFingerprint.compute(
            target=step.target, scanner=scanner, intensity=step.intensity
        )
        cached_scan_id = await fingerprints.lookup(
            fingerprint=fp.digest,
            scanner=scanner,
            ttl_seconds=ttl_seconds,
            tenant_id=request.tenant_id,
        )
        if cached_scan_id is None:
            to_run.append(scanner)
            continue
        prior = await persistence.get_scan(cached_scan_id)
        if prior is None:
            to_run.append(scanner)
            continue
        scanner_findings = [
            f.model_copy(update={"id": _new_finding_id()})
            for f in prior.findings
            if f.scanner == scanner
        ]
        reused.extend(scanner_findings)
        skipped.append(
            {
                "scanner": scanner,
                "fingerprint": fp.digest,
                "cached_scan_id": str(cached_scan_id),
                "reused_findings": str(len(scanner_findings)),
            }
        )

    if skipped:
        await audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.differential_skip",
            payload={"skipped": skipped, "kept": to_run},
        )
    return to_run, reused


async def record_fingerprints(
    *,
    fingerprints: Any,
    scan_id: Any,
    request: Any,
    step: Any,
    scanners_ran: list[str],
    enabled: bool,
) -> None:
    """Upsert fingerprint rows for every scanner that completed in this step."""
    if (
        not enabled
        or fingerprints is None
        or not getattr(fingerprints, "available", False)
        or not scanners_ran
    ):
        return
    for scanner in scanners_ran:
        fp = ScanFingerprint.compute(
            target=step.target, scanner=scanner, intensity=step.intensity
        )
        await fingerprints.upsert(
            fingerprint=fp.digest,
            scanner=scanner,
            scan_id=scan_id,
            tenant_id=request.tenant_id,
        )


def _new_finding_id() -> Any:
    """Fresh UUID for reused findings so they slot into the current scan cleanly."""
    from uuid import uuid4

    return uuid4()


def _normalize_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """Return a fingerprint-relevant subset of ``meta``.

    Only keys that affect scanner output are retained; volatile fields
    (timestamps, request IDs, last_scan_at, …) are dropped so a target
    edit that does not change scan inputs does not bust the cache.
    """
    relevant_keys = {
        "commit_sha",
        "branch",
        "image_digest",
        "image_tag",
        "iac_root_hash",
        "repo_path",
        "asset_criticality",
        "exposure",
    }
    out: dict[str, Any] = {}
    for k in sorted(relevant_keys):
        if k in meta and meta[k] is not None:
            out[k] = meta[k]
    return out
