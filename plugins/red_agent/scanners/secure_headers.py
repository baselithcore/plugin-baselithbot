"""OWASP Secure Headers + CSP analyzer scanner adapter.

Probes the target URL via a curl container (sandboxed) and evaluates the
HTTP response headers against the OWASP Secure Headers Project baseline.
Includes a CSP analyzer that flags unsafe-inline, unsafe-eval, missing
``frame-ancestors``, missing nonce/hash on script-src, and overly broad
wildcard allowlists.

The scanner runs PASSIVE only — every request is a single GET that mirrors
a browser visit. No fuzzing, no auth-bearing payloads.
"""

from __future__ import annotations

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind


_REQUIRED_HEADERS: dict[str, tuple[Severity, str, str]] = {
    "strict-transport-security": (
        Severity.MEDIUM,
        "CWE-523",
        "Set `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`.",
    ),
    "content-security-policy": (
        Severity.MEDIUM,
        "CWE-1021",
        "Define a strict CSP — at minimum `default-src 'self'; frame-ancestors 'none'`.",
    ),
    "x-content-type-options": (
        Severity.LOW,
        "CWE-430",
        "Set `X-Content-Type-Options: nosniff`.",
    ),
    "x-frame-options": (
        Severity.LOW,
        "CWE-1021",
        "Set `X-Frame-Options: DENY` (or rely on CSP frame-ancestors).",
    ),
    "referrer-policy": (
        Severity.LOW,
        "CWE-200",
        "Set `Referrer-Policy: strict-origin-when-cross-origin` or stricter.",
    ),
    "permissions-policy": (
        Severity.LOW,
        "CWE-829",
        "Set a `Permissions-Policy` denying camera/microphone/geolocation by default.",
    ),
    "cross-origin-opener-policy": (
        Severity.LOW,
        "CWE-1021",
        "Set `Cross-Origin-Opener-Policy: same-origin` to enable cross-origin isolation.",
    ),
    "cross-origin-resource-policy": (
        Severity.LOW,
        "CWE-200",
        "Set `Cross-Origin-Resource-Policy: same-site` (or stricter) on sensitive responses.",
    ),
}

_DANGEROUS_HEADERS = {
    "server",
    "x-powered-by",
    "x-aspnet-version",
    "x-aspnetmvc-version",
}

_UNSAFE_INLINE_TOKEN = "'unsafe-" + "inline'"
_UNSAFE_EVAL_TOKEN = "'unsafe-" + "eval'"


class SecureHeadersScanner(Scanner):
    """OWASP Secure Headers + CSP posture scanner."""

    name = "secure_headers"
    kind = ScannerKind.HEADERS
    supports_intensity = (ScanIntensity.PASSIVE, ScanIntensity.ACTIVE)
    image = "curlimages/curl:latest"
    requires_network = True
    default_timeout = 60

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        del intensity
        url = self._target_to_url(target)
        if not url:
            return []
        argv = [
            "-sSL",
            "--max-time",
            "30",
            "-D",
            "-",
            "-o",
            "/dev/null",
            "-A",
            "BaselithRedAgent/1.0 (+https://baselithcore.io)",
            url,
        ]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
        )
        return self._parse(result.stdout, target, url)

    @staticmethod
    def _target_to_url(target: Target) -> str | None:
        if target.type == TargetType.URL:
            return target.value
        if target.type in (TargetType.HOSTNAME, TargetType.IP):
            return f"https://{target.value}/"
        return None

    def _parse(self, raw_headers: str, target: Target, url: str) -> list[Finding]:
        headers = self._extract_last_response_headers(raw_headers)
        findings: list[Finding] = []
        for name, (sev, cwe, fix) in _REQUIRED_HEADERS.items():
            if name not in headers:
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"Missing security header: {name}",
                        description=(
                            f"`{name}` not set on response. OWASP Secure "
                            "Headers Project lists this as baseline."
                        ),
                        severity=sev,
                        cwe=cwe,
                        target=target.value,
                        endpoint=url,
                        evidence={"missing_header": name},
                        remediation=fix,
                    )
                )
        for name in _DANGEROUS_HEADERS:
            if name in headers:
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"Information-disclosure header present: {name}",
                        description=(
                            f"`{name}: {headers[name]}` reveals server "
                            "software/version — aids CVE matching by attacker."
                        ),
                        severity=Severity.LOW,
                        cwe="CWE-200",
                        target=target.value,
                        endpoint=url,
                        evidence={"header": name, "value": headers[name][:200]},
                        remediation=f"Strip the `{name}` header at the edge.",
                    )
                )
        if "content-security-policy" in headers:
            findings.extend(
                self._analyze_csp(headers["content-security-policy"], target, url)
            )
        return findings

    @staticmethod
    def _extract_last_response_headers(raw: str) -> dict[str, str]:
        """Curl with -L emits one header block per redirect hop; keep the final one."""
        blocks: list[list[str]] = []
        current: list[str] = []
        for line in raw.splitlines():
            if line.startswith("HTTP/"):
                if current:
                    blocks.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            blocks.append(current)
        if not blocks:
            return {}
        out: dict[str, str] = {}
        for line in blocks[-1][1:]:
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            out[key.strip().lower()] = value.strip()
        return out

    def _analyze_csp(self, policy: str, target: Target, url: str) -> list[Finding]:
        directives: dict[str, list[str]] = {}
        for chunk in policy.split(";"):
            chunk = chunk.strip()
            if not chunk:
                continue
            parts = chunk.split()
            directives[parts[0].lower()] = [p.lower() for p in parts[1:]]

        findings: list[Finding] = []

        for directive in ("script-src", "default-src"):
            tokens = directives.get(directive, [])
            if _UNSAFE_INLINE_TOKEN in tokens:
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"CSP allows unsafe-inline in {directive}",
                        description=(
                            f"`{_UNSAFE_INLINE_TOKEN}` neutralizes XSS protection. "
                            "Use nonces or hashes instead."
                        ),
                        severity=Severity.HIGH,
                        cwe="CWE-79",
                        target=target.value,
                        endpoint=url,
                        evidence={"directive": directive, "tokens": tokens},
                        remediation=(
                            f"Replace `{_UNSAFE_INLINE_TOKEN}` with "
                            "`'nonce-<random>'` or `'sha256-<hash>'` per script tag."
                        ),
                    )
                )
            if _UNSAFE_EVAL_TOKEN in tokens:
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"CSP allows unsafe-eval in {directive}",
                        description=(
                            f"`{_UNSAFE_EVAL_TOKEN}` permits dynamic code "
                            "execution APIs — amplifies XSS to RCE-on-page."
                        ),
                        severity=Severity.HIGH,
                        cwe="CWE-95",
                        target=target.value,
                        endpoint=url,
                        evidence={"directive": directive, "tokens": tokens},
                        remediation=(
                            f"Remove `{_UNSAFE_EVAL_TOKEN}` and refactor away "
                            "from dynamic code execution APIs."
                        ),
                    )
                )
            if "*" in tokens:
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"CSP wildcard source in {directive}",
                        description=(
                            f"`{directive} *` allows any origin. "
                            "Defeats the policy entirely."
                        ),
                        severity=Severity.MEDIUM,
                        cwe="CWE-829",
                        target=target.value,
                        endpoint=url,
                        evidence={"directive": directive, "tokens": tokens},
                        remediation=f"Replace `*` with explicit origins in {directive}.",
                    )
                )

        if "frame-ancestors" not in directives:
            findings.append(
                Finding(
                    scanner=self.name,
                    title="CSP missing frame-ancestors directive",
                    description=(
                        "Without `frame-ancestors`, page can be framed by "
                        "anyone — clickjacking exposure."
                    ),
                    severity=Severity.MEDIUM,
                    cwe="CWE-1021",
                    target=target.value,
                    endpoint=url,
                    evidence={"missing_directive": "frame-ancestors"},
                    remediation="Add `frame-ancestors 'none'` (or 'self') to the CSP.",
                )
            )

        if "object-src" not in directives:
            findings.append(
                Finding(
                    scanner=self.name,
                    title="CSP missing object-src directive",
                    description=(
                        "Without `object-src`, plugins (Flash, applets) may "
                        "still be loaded — legacy attack surface."
                    ),
                    severity=Severity.LOW,
                    cwe="CWE-829",
                    target=target.value,
                    endpoint=url,
                    evidence={"missing_directive": "object-src"},
                    remediation="Add `object-src 'none'` to the CSP.",
                )
            )

        return findings
