"""Trivy SCA / IaC scanner adapter (filesystem + repo)."""

from __future__ import annotations

import json

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

_SEVERITY_MAP: dict[str, Severity] = {
    "UNKNOWN": Severity.INFO,
    "LOW": Severity.LOW,
    "MEDIUM": Severity.MEDIUM,
    "HIGH": Severity.HIGH,
    "CRITICAL": Severity.CRITICAL,
}


class TrivyScanner(Scanner):
    name = "trivy"
    kind = ScannerKind.SCA
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = "aquasec/trivy:latest"
    requires_network = True
    default_timeout = 900

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        # The image's ENTRYPOINT is `trivy` — argv carries the subcommand
        # + flags only; no leading binary name.
        if target.type == TargetType.REPO:
            argv = ["repo", "--format", "json", "--quiet", target.value]
        else:
            argv = ["fs", "--format", "json", "--quiet", target.value]

        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
        )
        return self._parse(result.stdout, target)

    def _parse(self, json_text: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        try:
            doc = json.loads(json_text)
        except json.JSONDecodeError:
            return findings

        for res in doc.get("Results", []):
            for vuln in res.get("Vulnerabilities", []) or []:
                cvss_score = None
                cvss_data = vuln.get("CVSS") or {}
                if isinstance(cvss_data, dict):
                    for vendor in cvss_data.values():
                        v3 = vendor.get("V3Score")
                        if v3 is not None:
                            cvss_score = float(v3)
                            break

                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"{vuln.get('VulnerabilityID')} in {vuln.get('PkgName')}",
                        description=vuln.get("Description", ""),
                        severity=_SEVERITY_MAP.get(
                            vuln.get("Severity", "UNKNOWN").upper(), Severity.INFO
                        ),
                        cvss_score=cvss_score,
                        cve=vuln.get("VulnerabilityID"),
                        target=target.value,
                        evidence={
                            "package": vuln.get("PkgName"),
                            "installed_version": vuln.get("InstalledVersion"),
                            "fixed_version": vuln.get("FixedVersion"),
                        },
                        raw=vuln,
                        remediation=(
                            f"Upgrade {vuln.get('PkgName')} to {vuln.get('FixedVersion')}"
                            if vuln.get("FixedVersion")
                            else "Apply vendor patch when available; consider mitigations."
                        ),
                    )
                )
        return findings
