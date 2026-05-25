"""Anchore Syft (SBOM) + Grype (vulnerability match) scanners.

Two complementary supply-chain adapters:

* :class:`SyftScanner` produces an SPDX-JSON SBOM and registers the
  package inventory as ``INFO`` findings — visibility-only, but the SBOM
  document itself is preserved verbatim under ``Finding.evidence['sbom']``
  for downstream attestation, in-toto / SLSA workflows, or asset
  inventory.
* :class:`GrypeScanner` matches the package list against Anchore's
  vulnerability database (NVD + GHSA + Alpine + Ubuntu + RHEL feeds)
  and emits one finding per vulnerable package. Complements Trivy with
  better OS coverage and signed advisory provenance.

Both scanners run in PASSIVE only — they enumerate, they do not probe.
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


_GRYPE_SEVERITY_MAP: dict[str, Severity] = {
    "Negligible": Severity.INFO,
    "Low": Severity.LOW,
    "Medium": Severity.MEDIUM,
    "High": Severity.HIGH,
    "Critical": Severity.CRITICAL,
    "Unknown": Severity.INFO,
}


class SyftScanner(Scanner):
    """Generate SBOM (SPDX-JSON) for repo/filesystem targets."""

    name = "syft"
    kind = ScannerKind.SBOM
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = "anchore/syft:latest"
    requires_network = False
    default_timeout = 900

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        del intensity
        if target.type not in (TargetType.REPO,):
            return []
        argv = [
            f"dir:{target.value}",
            "-o",
            "spdx-json",
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
        packages = doc.get("packages") or []
        if not isinstance(packages, list):
            return findings
        # One aggregate INFO finding carries the SBOM document — avoids
        # exploding into one finding per package while preserving the
        # full SBOM for attestation.
        findings.append(
            Finding(
                scanner=self.name,
                title=f"SBOM generated ({len(packages)} packages)",
                description=(
                    f"SPDX SBOM produced for {target.value}. "
                    "Use this as input to attestation/signing workflows."
                ),
                severity=Severity.INFO,
                target=target.value,
                evidence={
                    "package_count": len(packages),
                    "spdx_version": doc.get("spdxVersion"),
                    "packages_preview": [
                        {
                            "name": p.get("name"),
                            "version": p.get("versionInfo"),
                            "license": p.get("licenseConcluded"),
                        }
                        for p in packages[:50]
                        if isinstance(p, dict)
                    ],
                },
                raw={"sbom": doc},
                remediation=(
                    "Sign the SBOM (e.g. cosign attest) and include it in "
                    "the release artifacts for SLSA Level 2+ compliance."
                ),
            )
        )
        return findings


class GrypeScanner(Scanner):
    """Match package inventory against Anchore Grype vulnerability feeds."""

    name = "grype"
    kind = ScannerKind.SCA
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = "anchore/grype:latest"
    requires_network = True
    default_timeout = 1200

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        del intensity
        if target.type not in (TargetType.REPO,):
            return []
        argv = [
            f"dir:{target.value}",
            "-o",
            "json",
            "--quiet",
        ]
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
        for match in doc.get("matches", []) or []:
            if not isinstance(match, dict):
                continue
            vuln = match.get("vulnerability") or {}
            artifact = match.get("artifact") or {}
            sev_raw = str(vuln.get("severity", "Unknown"))
            cvss_score = self._extract_cvss(vuln)
            findings.append(
                Finding(
                    scanner=self.name,
                    title=f"{vuln.get('id', 'vuln')} in {artifact.get('name', 'package')}",
                    description=(vuln.get("description") or "")[:1000],
                    severity=_GRYPE_SEVERITY_MAP.get(sev_raw, Severity.INFO),
                    cvss_score=cvss_score,
                    cve=vuln.get("id")
                    if str(vuln.get("id", "")).startswith("CVE-")
                    else None,
                    target=target.value,
                    evidence={
                        "package": artifact.get("name"),
                        "version": artifact.get("version"),
                        "type": artifact.get("type"),
                        "fix_versions": (vuln.get("fix") or {}).get("versions"),
                        "fix_state": (vuln.get("fix") or {}).get("state"),
                        "namespace": vuln.get("namespace"),
                        "advisories": [
                            a.get("link")
                            for a in (vuln.get("advisories") or [])
                            if isinstance(a, dict)
                        ],
                    },
                    raw=match,
                    remediation=self._build_remediation(vuln, artifact),
                )
            )
        return findings

    @staticmethod
    def _extract_cvss(vuln: dict[str, Any]) -> float | None:
        cvss_list = vuln.get("cvss") or []
        if not isinstance(cvss_list, list):
            return None
        for entry in cvss_list:
            if not isinstance(entry, dict):
                continue
            metrics = entry.get("metrics") or {}
            base = metrics.get("baseScore")
            if isinstance(base, (int, float)):
                return float(base)
        return None

    @staticmethod
    def _build_remediation(vuln: dict[str, Any], artifact: dict[str, Any]) -> str:
        fix = vuln.get("fix") or {}
        versions = fix.get("versions") or []
        if versions:
            return f"Upgrade `{artifact.get('name', 'package')}` to {versions[0]} or later."
        return (
            "No upstream fix available yet. Apply vendor mitigations and "
            "monitor the advisory for updates."
        )
