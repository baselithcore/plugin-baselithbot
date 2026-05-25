"""Checkov IaC scanner adapter.

Scans Terraform / CloudFormation / Kubernetes / Helm / Dockerfile /
Serverless / Bicep manifests for misconfigurations using Bridgecrew's
policy library (700+ checks aligned with CIS, NIST, PCI, HIPAA).

Output format: ``--output json`` produces the per-framework dict shape
documented at https://www.checkov.io/2.Basics/Reviewing%20Scan%20Results.html
where ``results.failed_checks[]`` carries each violation with a stable
``check_id`` (``CKV_*``), ``check_name`` and (when available) a CWE +
remediation URL.
"""

from __future__ import annotations

import json
from typing import Any

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

_SEVERITY_MAP: dict[str, Severity] = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
    "INFO": Severity.INFO,
}


class CheckovScanner(Scanner):
    name = "checkov"
    kind = ScannerKind.CONFIG
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = "bridgecrew/checkov:latest"
    requires_network = False
    default_timeout = 900

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if target.type not in (TargetType.IAC, TargetType.REPO):
            return []
        argv = [
            "--directory",
            "/workspace",
            "--output",
            "json",
            "--soft-fail",
            "--quiet",
        ]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=False,
            scanner=self.name,
        )
        return self._parse(result.stdout, target)

    def _parse(self, json_text: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        try:
            doc = json.loads(json_text)
        except json.JSONDecodeError:
            return findings

        # Checkov emits either a single object (one framework) or a list
        # (multi-framework). Normalize.
        runs = doc if isinstance(doc, list) else [doc]
        for run in runs:
            if not isinstance(run, dict):
                continue
            results = run.get("results") or {}
            for failed in results.get("failed_checks", []) or []:
                if not isinstance(failed, dict):
                    continue
                findings.append(_finding_from_check(failed, target))
        return findings


def _finding_from_check(check: dict[str, Any], target: Target) -> Finding:
    severity = _SEVERITY_MAP.get(
        str(check.get("severity") or "MEDIUM").upper(), Severity.MEDIUM
    )
    cwe = check.get("cwe") or _first_cwe(check.get("bc_check_id"))
    file_path = check.get("file_path") or check.get("repo_file_path") or ""
    file_line = check.get("file_line_range") or []
    location = (
        f"{file_path}#L{file_line[0]}-{file_line[-1]}"
        if file_path and file_line
        else file_path or target.value
    )
    return Finding(
        scanner="checkov",
        title=f"{check.get('check_id')}: {check.get('check_name', '')}",
        description=check.get("description") or check.get("check_name", ""),
        severity=severity,
        cwe=cwe,
        target=target.value,
        endpoint=location,
        evidence={
            "check_id": check.get("check_id"),
            "bc_check_id": check.get("bc_check_id"),
            "resource": check.get("resource"),
            "file_path": file_path,
            "file_line_range": file_line,
            "guideline": check.get("guideline"),
        },
        raw=check,
        remediation=check.get("guideline")
        or "Review Checkov guideline; align with CIS/NIST baseline.",
    )


def _first_cwe(_bc_check_id: Any) -> str | None:
    """Checkov does not always emit CWE; placeholder for future mapping table."""
    return None
