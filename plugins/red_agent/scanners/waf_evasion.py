"""WAF detection + evasion probe.

Two-step:

1. **Fingerprint** the WAF with five well-known triggers (the same
   set ``wafw00f`` ships) and inspect headers / response bodies for
   vendor banners (Cloudflare, AWS WAF, Akamai, F5, Imperva).
2. For each baseline payload that the WAF blocks, retry with three
   common evasion encodings (URL double-encoding, mixed case,
   unicode-fullwidth substitution) and report whether any succeeded.

INTRUSIVE intensity only — every probe is intentionally suspicious
traffic. The scanner refuses any other intensity by construction.

Targets are URL or HOSTNAME. The findings are informational by
default — a successful evasion is High severity because it directly
contradicts the customer's "the WAF protects us" mental model.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from core.observability.logging import get_logger
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)


_WAF_FINGERPRINTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Cloudflare", re.compile(r"cloudflare|cf-ray|__cfduid", re.IGNORECASE)),
    ("AWS WAF", re.compile(r"aws(\s|-)?waf|x-amzn-requestid", re.IGNORECASE)),
    ("Akamai", re.compile(r"akamai|akamaighost|x-akamai", re.IGNORECASE)),
    ("F5 BIG-IP ASM", re.compile(r"big-?ip|f5\s|tspd_", re.IGNORECASE)),
    ("Imperva", re.compile(r"imperva|incap_ses|visid_incap", re.IGNORECASE)),
    ("ModSecurity", re.compile(r"mod_security|modsecurity", re.IGNORECASE)),
)

# Baseline payloads that any conservative WAF rejects with 403.
_BASELINE_PAYLOADS: tuple[tuple[str, str], ...] = (
    ("sqli", "' OR 1=1 --"),
    ("xss", "<script>alert(1)</script>"),
    ("path", "../../../etc/passwd"),
)


def _url_double_encode(s: str) -> str:
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        else:
            out.append("%25" + format(ord(ch), "02X"))
    return "".join(out)


def _mixed_case(s: str) -> str:
    return "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(s))


def _fullwidth(s: str) -> str:
    out: list[str] = []
    for ch in s:
        if "A" <= ch <= "Z":
            out.append(chr(ord(ch) - ord("A") + 0xFF21))
        elif "a" <= ch <= "z":
            out.append(chr(ord(ch) - ord("a") + 0xFF41))
        else:
            out.append(ch)
    return "".join(out)


_EVASIONS: tuple[tuple[str, Any], ...] = (
    ("url_double_encode", _url_double_encode),
    ("mixed_case", _mixed_case),
    ("fullwidth_unicode", _fullwidth),
)


class WAFEvasionScanner(Scanner):
    name = "waf_evasion"
    kind = ScannerKind.DAST
    supports_intensity = (ScanIntensity.INTRUSIVE,)
    requires_network = True
    default_timeout = 60

    def __init__(
        self,
        sandbox: Any = None,
        timeout: int | None = None,
        *,
        request_timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__(sandbox, timeout=timeout)  # type: ignore[arg-type]
        self._request_timeout = request_timeout_seconds

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if intensity != ScanIntensity.INTRUSIVE:
            return []
        if target.type not in (TargetType.URL, TargetType.HOSTNAME):
            return []
        base = self._base_url(target)
        if base is None:
            return []

        async with httpx.AsyncClient(
            timeout=self._request_timeout, follow_redirects=False
        ) as client:
            findings: list[Finding] = []
            vendor = await self._fingerprint(client, base, target)
            if vendor:
                findings.append(vendor)
            findings.extend(await self._probe_evasions(client, base, target))
            return findings

    def _base_url(self, target: Target) -> str | None:
        value = target.value.strip()
        if target.type == TargetType.HOSTNAME:
            return f"https://{value.rstrip('/')}"
        return value.rstrip("/")

    async def _fingerprint(
        self, client: httpx.AsyncClient, base: str, target: Target
    ) -> Finding | None:
        try:
            resp = await client.get(base, params={"q": "../" * 8})
        except httpx.HTTPError:
            return None
        haystack = (
            " ".join(f"{k}: {v}" for k, v in resp.headers.items())
            + " "
            + (resp.text or "")[:1024]
        )
        for vendor, pattern in _WAF_FINGERPRINTS:
            if pattern.search(haystack):
                return Finding(
                    scanner=self.name,
                    title=f"WAF detected: {vendor}",
                    description=(
                        f"Banner / header signatures match {vendor}. "
                        "Subsequent probes test whether common "
                        "encoding tricks bypass the configured rules."
                    ),
                    severity=Severity.INFO,
                    target=target.value,
                    endpoint=base,
                    evidence={"vendor": vendor, "status_code": resp.status_code},
                )
        return None

    async def _probe_evasions(
        self, client: httpx.AsyncClient, base: str, target: Target
    ) -> list[Finding]:
        findings: list[Finding] = []
        for label, payload in _BASELINE_PAYLOADS:
            blocked = await self._is_blocked(client, base, payload)
            if not blocked:
                continue
            for evasion_label, encoder in _EVASIONS:
                encoded = encoder(payload)
                if not await self._is_blocked(client, base, encoded):
                    findings.append(
                        Finding(
                            scanner=self.name,
                            title=(
                                f"WAF evasion succeeded: {label} via {evasion_label}"
                            ),
                            description=(
                                "The WAF blocked the baseline payload "
                                f"({label}) but allowed the same "
                                f"payload encoded via {evasion_label}. "
                                "The rule chain has a coverage gap "
                                "for this encoding."
                            ),
                            severity=Severity.HIGH,
                            target=target.value,
                            endpoint=base,
                            evidence={
                                "payload_class": label,
                                "evasion": evasion_label,
                                "baseline_blocked": True,
                            },
                            cwe="CWE-693",
                            remediation=(
                                "Add a normalisation step to the WAF "
                                "rule chain before pattern matching."
                            ),
                        )
                    )
        return findings

    async def _is_blocked(
        self, client: httpx.AsyncClient, base: str, payload: str
    ) -> bool:
        try:
            resp = await client.get(base, params={"q": payload})
        except httpx.HTTPError:
            return False
        return resp.status_code in {403, 406, 429, 501}
