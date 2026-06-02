"""IOC-related finding builders for the binary analyzer.

Mixin providing the embedded-indicator finding builders (IPv4/IPv6,
URL, domain, generic IOC), suspicious-import findings, and embedded
secret-material findings. Combined into ``BinaryAnalyzerScanner``.
"""

from __future__ import annotations

from plugins.red_agent.models import Finding, Severity, Target
from plugins.red_agent.scanners._binary_iocs import (
    classify_ipv4,
    classify_url,
    is_routable_ipv4,
    threat_intel_pivot_links,
)
from plugins.red_agent.scanners.binary_analyzer._helpers import (
    _imports_to_attack,
    _ioc_severity,
    _url_severity,
)
from plugins.red_agent.scanners.binary_analyzer._render import (
    _render_indicator_list,
    _render_ip_indicator,
    _render_reserved_ips,
    _render_url_indicator,
)


class _IocFindingsMixin:
    """IOC / secret finding builders mixed into ``BinaryAnalyzerScanner``."""

    name: str

    def _ioc_findings(
        self, target: Target, iocs: dict[str, list[str]]
    ) -> list[Finding]:
        out: list[Finding] = []
        for kind, values in iocs.items():
            if not values:
                continue
            if kind == "ipv4":
                out.extend(self._ipv4_findings(target, values))
                continue
            if kind == "ipv6":
                out.extend(self._ipv6_findings(target, values))
                continue
            if kind == "url":
                out.extend(self._url_findings(target, values))
                continue
            if kind == "domain":
                out.append(self._domain_bulk_finding(target, values))
                continue
            severity = _ioc_severity(kind, values)
            sample = values[:16]
            out.append(
                Finding(
                    scanner=self.name,
                    title=(
                        f"Embedded {kind} IOC: {sample[0]}"
                        if len(values) == 1
                        else f"Embedded {kind} IOCs ({len(values)}): {', '.join(sample[:3])}…"
                    ),
                    description=_render_indicator_list(kind, values),
                    severity=severity,
                    cwe="CWE-200",
                    target=target.value,
                    evidence={
                        "kind": kind,
                        "indicators": values[:200],
                        "truncated": len(values) > 200,
                    },
                    remediation=(
                        "Cross-reference indicators against threat-intel "
                        "feeds (MISP, GreyNoise, AlienVault OTX) and add "
                        "high-confidence matches to the deny lists."
                    ),
                )
            )
        return out

    def _ipv4_findings(self, target: Target, values: list[str]) -> list[Finding]:
        """One finding per routable IPv4 — title carries the address.

        Reserved / private IPs collapse into a single LOW finding so the
        operator's queue is not flooded by every embedded ``127.0.0.1``.
        """
        routable: list[str] = []
        reserved: list[tuple[str, str]] = []
        for ip in values:
            klass = classify_ipv4(ip)
            if klass:
                reserved.append((ip, klass))
            elif is_routable_ipv4(ip):
                routable.append(ip)
            else:
                reserved.append((ip, "non-routable"))
        out: list[Finding] = []
        for ip in routable:
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded routable IPv4: {ip}",
                    description=_render_ip_indicator(ip, kind="ipv4"),
                    severity=Severity.MEDIUM,
                    cwe="CWE-200",
                    target=target.value,
                    evidence={
                        "kind": "ipv4",
                        "value": ip,
                        "classification": "routable",
                        "pivots": threat_intel_pivot_links("ipv4", ip),
                    },
                    remediation=(
                        "Pivot the IP against VirusTotal/AbuseIPDB/GreyNoise. "
                        "If malicious, add to perimeter blocklists and hunt "
                        "for prior connections in firewall/proxy logs."
                    ),
                )
            )
        if reserved:
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded reserved IPv4 ({len(reserved)})",
                    description=_render_reserved_ips(reserved),
                    severity=Severity.LOW,
                    cwe="CWE-200",
                    target=target.value,
                    evidence={
                        "kind": "ipv4_reserved",
                        "indicators": [
                            {"value": v, "classification": k} for v, k in reserved[:200]
                        ],
                        "truncated": len(reserved) > 200,
                    },
                    remediation=(
                        "Reserved/private addresses are usually default "
                        "config or test fixtures. Confirm none reveal "
                        "internal infrastructure topology before shipping."
                    ),
                )
            )
        return out

    def _ipv6_findings(self, target: Target, values: list[str]) -> list[Finding]:
        return [
            Finding(
                scanner=self.name,
                title=(
                    f"Embedded IPv6: {values[0]}"
                    if len(values) == 1
                    else f"Embedded IPv6 indicators ({len(values)})"
                ),
                description=_render_indicator_list("ipv6", values),
                severity=Severity.MEDIUM,
                cwe="CWE-200",
                target=target.value,
                evidence={
                    "kind": "ipv6",
                    "indicators": values[:200],
                    "truncated": len(values) > 200,
                },
                remediation=(
                    "Resolve each address against threat-intel feeds and "
                    "the corporate IPv6 allocation map."
                ),
            )
        ]

    def _url_findings(self, target: Target, values: list[str]) -> list[Finding]:
        """Per-URL findings, escalated when the URL trips a heuristic."""
        out: list[Finding] = []
        for url in values:
            labels = classify_url(url)
            severity = _url_severity(labels)
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded URL: {url[:96]}",
                    description=_render_url_indicator(url, labels),
                    severity=severity,
                    cwe="CWE-200",
                    target=target.value,
                    evidence={
                        "kind": "url",
                        "value": url,
                        "labels": labels,
                        "pivots": threat_intel_pivot_links("url", url),
                    },
                    remediation=(
                        "If the URL is unfamiliar, sandbox-detonate it and "
                        "check WHOIS / passive DNS for the parent domain."
                    ),
                )
            )
        return out

    def _domain_bulk_finding(self, target: Target, values: list[str]) -> Finding:
        return Finding(
            scanner=self.name,
            title=(
                f"Embedded domain: {values[0]}"
                if len(values) == 1
                else f"Embedded domains ({len(values)})"
            ),
            description=_render_indicator_list("domain", values),
            severity=Severity.MEDIUM,
            cwe="CWE-200",
            target=target.value,
            evidence={
                "kind": "domain",
                "indicators": values[:200],
                "truncated": len(values) > 200,
                "pivots": {
                    v: threat_intel_pivot_links("domain", v) for v in values[:5]
                },
            },
            remediation=(
                "Compare against the corporate DNS allow-list and historical "
                "passive-DNS records (RiskIQ, DomainTools)."
            ),
        )

    def _import_findings(self, target: Target, suspicious: list[str]) -> list[Finding]:
        if not suspicious:
            return []
        return [
            Finding(
                scanner=self.name,
                title=f"Suspicious Win32 imports ({len(suspicious)})",
                description=(
                    "Sample imports APIs commonly abused by malware for "
                    "process injection, anti-analysis, or credential "
                    "access: " + ", ".join(suspicious[:32]) + "."
                ),
                severity=Severity.HIGH if len(suspicious) >= 4 else Severity.MEDIUM,
                cwe="CWE-506",
                target=target.value,
                evidence={
                    "imports": suspicious,
                    "attack_techniques": _imports_to_attack(suspicious),
                },
                remediation=(
                    "Review the call sites of each highlighted API; "
                    "legitimate uses should be documented in the binary's "
                    "design notes before approval."
                ),
            )
        ]

    def _private_key_findings(
        self, target: Target, iocs: dict[str, list[str]]
    ) -> list[Finding]:
        keys = iocs.get("private_key") or []
        aws = iocs.get("aws_access_key") or []
        jwt = iocs.get("jwt") or []
        out: list[Finding] = []
        if keys:
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded private key material ({len(keys)})",
                    description=("Sample contains PEM-encoded private key headers."),
                    severity=Severity.CRITICAL,
                    cwe="CWE-798",
                    target=target.value,
                    evidence={"matches": keys[:8]},
                    remediation="Rotate the key and remove it from the binary.",
                )
            )
        if aws:
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded AWS access keys ({len(aws)})",
                    description="AWS access-key IDs detected in the binary.",
                    severity=Severity.CRITICAL,
                    cwe="CWE-798",
                    target=target.value,
                    evidence={"keys": aws[:16]},
                    remediation="Disable the IAM key and rotate credentials.",
                )
            )
        if jwt:
            out.append(
                Finding(
                    scanner=self.name,
                    title=f"Embedded JWTs ({len(jwt)})",
                    description="Sample carries JSON Web Tokens.",
                    severity=Severity.HIGH,
                    cwe="CWE-798",
                    target=target.value,
                    evidence={"tokens": jwt[:8]},
                    remediation="Revoke the token at the issuer.",
                )
            )
        return out
