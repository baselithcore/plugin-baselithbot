"""Certificate Transparency (crt.sh) passive enumeration adapter.

Queries the public CT log aggregator at ``crt.sh`` for every
certificate that includes the seed apex in its `Common Name` or any
`Subject Alternative Name`. The result yields hostnames that the
target organisation has at some point issued certificates for —
including dev / staging hosts that may not be linked from anywhere.

No container is required; the adapter performs a single HTTPS GET
through ``httpx`` and never touches the discovered hosts. It is safe
to run at any intensity, but is exposed only through the OSINT path
so the master toggle (``RED_AGENT_OSINT_ENABLED``) gates it.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding, ScanIntensity, Severity, Target
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)

_CRTSH_URL = "https://crt.sh/"


class CrtShScanner(Scanner):
    name = "crtsh"
    kind = ScannerKind.OSINT
    supports_intensity = (
        ScanIntensity.PASSIVE,
        ScanIntensity.ACTIVE,
    )
    requires_network = True
    default_timeout = 60

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        # Fail-open: a CT log outage must not break the surrounding scan.
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    _CRTSH_URL,
                    params={"q": f"%.{target.value}", "output": "json"},
                )
            resp.raise_for_status()
            payload: list[dict[str, Any]] = resp.json()
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "red_agent.crtsh.fetch_failed",
                extra={"target": target.value, "err": str(exc)},
            )
            return []
        return self._parse(payload, target)

    def _parse(self, payload: list[dict[str, Any]], target: Target) -> list[Finding]:
        seen: set[str] = set()
        findings: list[Finding] = []
        apex = target.value.lower()
        for entry in payload:
            # Each entry concatenates SANs in name_value separated by newlines.
            raw_names = str(entry.get("name_value", ""))
            for name in raw_names.splitlines():
                host = name.strip().lower().lstrip("*.")
                if not host or host == apex:
                    continue
                if not host.endswith("." + apex) and host != apex:
                    continue
                if host in seen:
                    continue
                seen.add(host)
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"Subdomain discovered (CT): {host}",
                        description=(
                            f"Certificate Transparency entry shows {host} under {apex}."
                        ),
                        severity=Severity.INFO,
                        target=apex,
                        endpoint=host,
                        evidence={
                            "host": host,
                            "issuer_ca_id": entry.get("issuer_ca_id"),
                            "issuer_name": entry.get("issuer_name"),
                            "not_before": entry.get("not_before"),
                            "not_after": entry.get("not_after"),
                        },
                        raw=entry,
                    )
                )
        return findings
