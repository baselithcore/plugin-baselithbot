"""subfinder passive subdomain enumeration adapter.

Discovers subdomains owned by the seed apex (`example.com` →
`api.example.com`, `dev.example.com`, …) by aggregating passive
sources only — Certificate Transparency logs, DNS aggregators,
search engines. No traffic is sent to the discovered hosts; the
target apex itself is queried only as a search keyword.

Each discovered hostname becomes an INFO-severity finding of kind
``OSINT``. Promotion to a scannable target happens out-of-band in
``integrations.osint_ingestion`` — and only when the orchestrator's
OSINT auto-promote toggle is set.
"""

from __future__ import annotations

import json

from plugins.red_agent.models import Finding, ScanIntensity, Severity, Target
from plugins.red_agent.scanners.base import Scanner, ScannerKind


class SubfinderScanner(Scanner):
    name = "subfinder"
    kind = ScannerKind.OSINT
    supports_intensity = (
        ScanIntensity.PASSIVE,
        ScanIntensity.ACTIVE,
    )
    image = "projectdiscovery/subfinder:latest"
    requires_network = True
    default_timeout = 600

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        argv = [
            "-d",
            target.value,
            "-silent",
            "-json",
        ]
        # Passive-only by default. Active resolution is gated on intensity
        # so PASSIVE scans never trigger upstream DNS queries.
        if intensity == ScanIntensity.PASSIVE:
            argv.append("-passive")

        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
        )
        return self._parse(result.stdout, target)

    def _parse(self, stdout: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[str] = set()
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            host = str(doc.get("host", "")).strip().lower()
            if not host or host in seen:
                continue
            # Apex itself is not a discovery — only sub-hosts under it.
            if host == target.value.lower():
                continue
            seen.add(host)
            findings.append(
                Finding(
                    scanner=self.name,
                    title=f"Subdomain discovered: {host}",
                    description=(
                        f"Passive enumeration found {host} as a subdomain of "
                        f"{target.value}."
                    ),
                    severity=Severity.INFO,
                    target=target.value,
                    endpoint=host,
                    evidence={
                        "host": host,
                        "source": doc.get("source"),
                        "input": doc.get("input"),
                    },
                    raw=doc,
                )
            )
        return findings
