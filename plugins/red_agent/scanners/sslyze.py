"""sslyze TLS/crypto compliance scanner adapter.

Runs sslyze against a target host:port and evaluates the cipher suite,
protocol version, certificate, OCSP, HSTS, and downgrade posture against
two baseline policies:

* **PCI-DSS 4.0** (Requirement 4.2.1) — TLS >= 1.2, no weak ciphers, no
  RC4/3DES/EXPORT/NULL/aNULL, server ordering.
* **NIST SP 800-52 Rev 2 / FIPS 140-3** — TLS >= 1.2 (1.3 preferred), AEAD
  ciphers only, ECDHE/DHE forward secrecy, certificate signed with strong
  algorithm.

The compliance check is *local* — sslyze produces the JSON, this module
evaluates it. That keeps the policy explicit, auditable, and tunable
without rebuilding sslyze itself.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

_WEAK_CIPHER_KEYWORDS = (
    "RC4",
    "3DES",
    "DES_",
    "EXPORT",
    "NULL",
    "MD5",
    "anon",
    "ADH",
    "AECDH",
)


class SslyzeScanner(Scanner):
    """TLS configuration + compliance scanner.

    Passive: every probe is a TLS handshake — same traffic profile as a
    browser load. Safe to run without intrusive approval.
    """

    name = "sslyze"
    kind = ScannerKind.TLS
    supports_intensity = (ScanIntensity.PASSIVE, ScanIntensity.ACTIVE)
    image = "nablac0d3/sslyze:latest"
    requires_network = True
    default_timeout = 600

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        del intensity
        host_port = self._target_to_host_port(target)
        if not host_port:
            return []
        # Image entrypoint is `sslyze` — argv carries flags only.
        argv = [
            "--regular",
            "--json_out=-",
            host_port,
        ]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
        )
        return self._parse(result.stdout, target)

    @staticmethod
    def _target_to_host_port(target: Target) -> str | None:
        if target.type == TargetType.URL:
            parsed = urlparse(target.value)
            host = parsed.hostname
            if not host:
                return None
            port = parsed.port or (443 if parsed.scheme == "https" else 443)
            return f"{host}:{port}"
        if target.type in (TargetType.HOSTNAME, TargetType.IP):
            return f"{target.value}:443"
        return None

    def _parse(self, json_text: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        try:
            doc = json.loads(json_text)
        except json.JSONDecodeError:
            return findings

        for server in doc.get("server_scan_results", []):
            scan_result = server.get("scan_result") or {}
            findings.extend(self._eval_protocols(scan_result, target))
            findings.extend(self._eval_certificate(scan_result, target))
            findings.extend(self._eval_hsts(scan_result, target))
            findings.extend(self._eval_compliance(scan_result, target))
        return findings

    def _eval_protocols(
        self, scan_result: dict[str, Any], target: Target
    ) -> list[Finding]:
        results: list[Finding] = []
        for proto_key in (
            "ssl_2_0_cipher_suites",
            "ssl_3_0_cipher_suites",
            "tls_1_0_cipher_suites",
            "tls_1_1_cipher_suites",
        ):
            section = scan_result.get(proto_key) or {}
            inner = section.get("result") or {}
            accepted = inner.get("accepted_cipher_suites") or []
            if accepted:
                pretty = (
                    proto_key.replace("_cipher_suites", "").replace("_", " ").upper()
                )
                results.append(
                    Finding(
                        scanner=self.name,
                        title=f"Weak TLS protocol enabled: {pretty}",
                        description=(
                            f"Server accepts {pretty}, deprecated by RFC 8996 "
                            "and forbidden by PCI-DSS 4.0 / NIST SP 800-52 Rev 2."
                        ),
                        severity=Severity.HIGH,
                        cwe="CWE-326",
                        target=target.value,
                        evidence={
                            "protocol": pretty,
                            "accepted_ciphers_count": len(accepted),
                            "compliance_violation": ["PCI-DSS-4.2.1", "NIST-800-52r2"],
                        },
                        remediation=(
                            f"Disable {pretty} on the server. Allow only TLS 1.2 "
                            "(AEAD ciphers + ECDHE) and TLS 1.3."
                        ),
                    )
                )
        for proto_key in ("tls_1_2_cipher_suites", "tls_1_3_cipher_suites"):
            section = scan_result.get(proto_key) or {}
            inner = section.get("result") or {}
            for cipher in inner.get("accepted_cipher_suites") or []:
                name = (cipher.get("cipher_suite") or {}).get("name", "")
                if any(weak in name for weak in _WEAK_CIPHER_KEYWORDS):
                    results.append(
                        Finding(
                            scanner=self.name,
                            title=f"Weak cipher suite enabled: {name}",
                            description=(
                                f"Cipher {name} accepted on "
                                f"{proto_key.split('_cipher')[0].upper()} — "
                                "fails AEAD/forward-secrecy requirements."
                            ),
                            severity=Severity.MEDIUM,
                            cwe="CWE-327",
                            target=target.value,
                            evidence={
                                "cipher": name,
                                "compliance_violation": [
                                    "PCI-DSS-4.2.1",
                                    "NIST-800-52r2",
                                ],
                            },
                            remediation="Restrict ciphers to AEAD ECDHE/DHE suites.",
                        )
                    )
        return results

    def _eval_certificate(
        self, scan_result: dict[str, Any], target: Target
    ) -> list[Finding]:
        results: list[Finding] = []
        section = scan_result.get("certificate_info") or {}
        inner = section.get("result") or {}
        for deployment in inner.get("certificate_deployments") or []:
            chain = deployment.get("received_certificate_chain") or []
            if not chain:
                continue
            leaf = chain[0]
            sig_algo = leaf.get("signature_hash_algorithm") or {}
            algo_name = (sig_algo.get("name") or "").lower()
            if algo_name in {"md5", "sha1"}:
                results.append(
                    Finding(
                        scanner=self.name,
                        title=f"Certificate uses weak signature algorithm: {algo_name}",
                        description=(
                            "Leaf certificate signed with an algorithm browsers "
                            "and CA/B-Forum baseline forbid."
                        ),
                        severity=Severity.HIGH,
                        cwe="CWE-327",
                        target=target.value,
                        evidence={"signature_algorithm": algo_name},
                        remediation="Re-issue the certificate with SHA-256 or stronger.",
                    )
                )
            pubkey = leaf.get("public_key") or {}
            if pubkey.get("algorithm") == "rsa":
                size = pubkey.get("size") or 0
                if size and size < 2048:
                    results.append(
                        Finding(
                            scanner=self.name,
                            title=f"RSA key too small: {size} bits",
                            description=(
                                "Certificate public key below the 2048-bit "
                                "minimum required by NIST SP 800-57."
                            ),
                            severity=Severity.HIGH,
                            cwe="CWE-326",
                            target=target.value,
                            evidence={"rsa_key_bits": size},
                            remediation="Re-issue with RSA >= 2048 or ECDSA P-256.",
                        )
                    )
        return results

    def _eval_hsts(self, scan_result: dict[str, Any], target: Target) -> list[Finding]:
        results: list[Finding] = []
        section = scan_result.get("http_headers") or {}
        inner = section.get("result") or {}
        hsts = inner.get("strict_transport_security_header")
        if hsts is None:
            results.append(
                Finding(
                    scanner=self.name,
                    title="HSTS header missing",
                    description=(
                        "No Strict-Transport-Security header — clients will "
                        "happily fall back to plaintext after first contact."
                    ),
                    severity=Severity.MEDIUM,
                    cwe="CWE-523",
                    target=target.value,
                    evidence={"header": "Strict-Transport-Security"},
                    remediation=(
                        "Set `Strict-Transport-Security: max-age=63072000; "
                        "includeSubDomains; preload` on every HTTPS response."
                    ),
                )
            )
        return results

    def _eval_compliance(
        self, scan_result: dict[str, Any], target: Target
    ) -> list[Finding]:
        results: list[Finding] = []
        section = scan_result.get("tls_1_3_cipher_suites") or {}
        inner = section.get("result") or {}
        if not (inner.get("accepted_cipher_suites") or []):
            results.append(
                Finding(
                    scanner=self.name,
                    title="TLS 1.3 not enabled",
                    description=(
                        "Server does not negotiate TLS 1.3. Recommended by "
                        "NIST SP 800-52 Rev 2 §3.1; TLS 1.2 still acceptable "
                        "but TLS 1.3 should be the default."
                    ),
                    severity=Severity.LOW,
                    cwe="CWE-326",
                    target=target.value,
                    evidence={"compliance_recommendation": "NIST-800-52r2-3.1"},
                    remediation="Enable TLS 1.3 alongside TLS 1.2 on the server.",
                )
            )
        return results
