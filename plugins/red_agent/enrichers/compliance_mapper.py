"""Compliance-pack control mapper.

Tags each finding with the security-control IDs it relates to across
the major frameworks operators are audited on:

* **CIS Critical Security Controls v8.1** (``CIS-X.Y``)
* **PCI DSS 4.0** (``PCI-X.Y.Z``)
* **NIST 800-53 rev5** (``NIST-XX-N``)
* **ISO/IEC 27001:2022 Annex A** (``ISO27001-A.X.Y``)
* **SOC 2 / TSC 2017** (``SOC2-CCX.Y``)

Mapping strategy:

1. **CWE-driven** lookup table covering the OWASP Top 10 / CWE Top 25
   surface — covers the bulk of DAST/SAST/SCA findings.
2. **Scanner-passthrough**: scanners that already emit framework
   references (Checkov ``guideline``, Prowler ``compliance`` block,
   kube-bench CIS-K8s control id) get those forwarded verbatim.
3. **Severity floor** when neither (1) nor (2) yields anything: every
   HIGH/CRITICAL finding is at minimum mapped to ``CIS-7`` (Continuous
   Vulnerability Management) so framework dashboards never show empty
   coverage for a security-relevant population of findings.

The output is ``Finding.controls`` and a duplicate copy in
``Finding.evidence['controls']`` so SIEM consumers that read the OCSF
``unmapped`` block can still see the mapping.
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding, Severity

logger = get_logger(__name__)


# CWE → control IDs. Curated for the most common Top 25 / OWASP categories.
# Operators extend via constructor argument.
_DEFAULT_CWE_MAP: dict[str, list[str]] = {
    # Injection family
    "CWE-89": ["CIS-16.10", "PCI-6.5.1", "NIST-SI-10", "ISO27001-A.8.28", "SOC2-CC7.1"],
    "CWE-78": ["CIS-16.10", "PCI-6.5.1", "NIST-SI-10"],
    "CWE-94": ["CIS-16.10", "PCI-6.5.1", "NIST-SI-10"],
    # XSS
    "CWE-79": ["CIS-16.10", "PCI-6.5.7", "NIST-SI-10", "ISO27001-A.8.28"],
    # Auth / Sessions
    "CWE-287": ["CIS-6.3", "PCI-8.3", "NIST-IA-2", "ISO27001-A.8.5", "SOC2-CC6.1"],
    "CWE-306": ["CIS-6.1", "PCI-8.3", "NIST-IA-2"],
    "CWE-384": ["CIS-6.4", "PCI-8.6", "NIST-AC-12"],
    # Authorization / IDOR
    "CWE-285": ["CIS-3.3", "PCI-7.1", "NIST-AC-3", "SOC2-CC6.3"],
    "CWE-639": ["CIS-3.3", "PCI-7.1", "NIST-AC-3"],
    # SSRF / open redirect
    "CWE-918": ["CIS-12.2", "PCI-1.4", "NIST-SC-7"],
    "CWE-601": ["CIS-9.4", "PCI-6.5.8", "NIST-SI-10"],
    # Crypto
    "CWE-327": ["CIS-3.10", "PCI-3.5", "NIST-SC-13", "ISO27001-A.8.24"],
    "CWE-326": ["CIS-3.10", "PCI-3.5", "NIST-SC-13"],
    "CWE-295": ["CIS-3.10", "PCI-4.2", "NIST-SC-17"],
    # Secrets / sensitive data
    "CWE-798": ["CIS-4.1", "PCI-3.4", "NIST-IA-5", "ISO27001-A.8.24"],
    "CWE-200": ["CIS-3.3", "PCI-3.4", "NIST-SC-28", "ISO27001-A.8.10"],
    # Deserialization / dangerous functions
    "CWE-502": ["CIS-16.10", "PCI-6.5.6", "NIST-SI-10"],
    "CWE-611": ["CIS-16.10", "PCI-6.5.7", "NIST-SI-10"],
    # Memory safety
    "CWE-787": ["CIS-16.13", "NIST-SI-2", "ISO27001-A.8.8"],
    "CWE-125": ["CIS-16.13", "NIST-SI-2"],
    "CWE-416": ["CIS-16.13", "NIST-SI-2"],
    "CWE-119": ["CIS-16.13", "NIST-SI-2"],
    # Vulnerable / outdated component
    "CWE-1104": ["CIS-7.4", "PCI-6.3.3", "NIST-SI-2", "ISO27001-A.8.8"],
    "CWE-937": ["CIS-7.4", "PCI-6.3.3", "NIST-SI-2"],
    # Misconfiguration
    "CWE-16": ["CIS-7.5", "PCI-2.2", "NIST-CM-6", "ISO27001-A.8.9"],
    "CWE-1021": ["CIS-9.4", "PCI-6.5.7", "NIST-SI-10"],
    # Headers / TLS specific
    "CWE-693": ["CIS-7.5", "PCI-2.2", "NIST-CM-6"],
    "CWE-319": ["CIS-3.10", "PCI-4.1", "NIST-SC-8"],
}

_SEVERITY_FLOOR_CONTROLS = ["CIS-7"]


class ComplianceMapperEnricher:
    """Annotate findings with framework control IDs."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        cwe_map: dict[str, list[str]] | None = None,
        severity_floor: Severity = Severity.HIGH,
    ) -> None:
        self.enabled = enabled
        self.cwe_map = dict(_DEFAULT_CWE_MAP)
        if cwe_map:
            for k, v in cwe_map.items():
                self.cwe_map.setdefault(k.upper(), []).extend(v)
        self.severity_floor = severity_floor

    def enrich(self, findings: list[Finding]) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        for f in findings:
            mapped = _mapped_for_finding(f, cwe_map=self.cwe_map)
            if not mapped and f.severity in (Severity.HIGH, Severity.CRITICAL):
                mapped = list(_SEVERITY_FLOOR_CONTROLS)
            if mapped:
                # Stable ordered uniq — preserve insertion order, drop dups.
                seen: set[str] = set()
                ordered: list[str] = []
                for c in mapped:
                    if c not in seen:
                        seen.add(c)
                        ordered.append(c)
                f.controls = ordered
                if isinstance(f.evidence, dict):
                    f.evidence["controls"] = ordered
        return findings


def _mapped_for_finding(f: Finding, *, cwe_map: dict[str, list[str]]) -> list[str]:
    out: list[str] = []
    # 1) CWE lookup
    if f.cwe:
        out.extend(cwe_map.get(f.cwe.upper(), []))
    # 2) Scanner-passthrough
    out.extend(_scanner_controls(f))
    return out


def _scanner_controls(f: Finding) -> list[str]:
    """Forward control IDs that a scanner already attached to the finding."""
    if not isinstance(f.evidence, dict):
        return []
    out: list[str] = []
    # Checkov: store the bc_check_id; surface as ``CHECKOV-<id>`` so framework
    # dashboards can join on it without colliding with native control IDs.
    bc_id = f.evidence.get("bc_check_id") or f.evidence.get("check_id")
    if isinstance(bc_id, str) and bc_id:
        out.append(f"CHECKOV-{bc_id}")
    # Prowler: ``compliance`` block can be a dict {"CIS-1.5": "2.1.3", ...}
    # or a list of strings. Either way emit framework-prefixed entries.
    compliance = f.evidence.get("compliance")
    if isinstance(compliance, dict):
        for fw, ctrl in compliance.items():
            if isinstance(ctrl, str):
                out.append(f"{fw.upper()}-{ctrl}".replace(" ", "_"))
    elif isinstance(compliance, list):
        out.extend(str(c) for c in compliance if isinstance(c, str))
    # kube-bench: control_version + test_number
    cv = f.evidence.get("control_version")
    tn = f.evidence.get("test_number")
    if isinstance(cv, str) and isinstance(tn, str):
        out.append(f"{cv.upper()}/{tn}")
    return out


def coverage_summary(
    findings: list[Finding], *, framework_prefix: str | None = None
) -> dict[str, Any]:
    """Aggregate findings → controls mapping.

    Returns ``{control_id: {count, severities, finding_ids}}``. When
    ``framework_prefix`` is supplied (e.g. ``"PCI-"``), only matching
    controls are included — useful for the per-framework report.
    """
    coverage: dict[str, dict[str, Any]] = {}
    for f in findings:
        for ctrl in f.controls or []:
            if framework_prefix and not ctrl.startswith(framework_prefix):
                continue
            entry = coverage.setdefault(
                ctrl,
                {"count": 0, "severities": {}, "finding_ids": []},
            )
            entry["count"] += 1
            sev = f.severity.value
            entry["severities"][sev] = entry["severities"].get(sev, 0) + 1
            entry["finding_ids"].append(str(f.id))
    return coverage
