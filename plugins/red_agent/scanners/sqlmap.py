"""sqlmap intrusive SQL-injection scanner adapter (HITL-gated)."""

from __future__ import annotations

import json

from plugins.red_agent.models import Finding, ScanIntensity, Severity, Target
from plugins.red_agent.scanners.base import Scanner, ScannerKind


class SqlmapScanner(Scanner):
    """
    sqlmap is intrusive — RedAgent must require human approval and an
    explicit per-target authorization token before invoking this adapter.
    """

    name = "sqlmap"
    kind = ScannerKind.DAST
    supports_intensity = (ScanIntensity.INTRUSIVE,)
    image = "googlesky/sqlmap:latest"
    requires_network = True
    default_timeout = 1800

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        # googlesky/sqlmap entrypoint is `uv run sqlmap-dev/sqlmap.py` — argv
        # carries flags only.
        argv = [
            "-u",
            target.value,
            "--batch",
            "--level=2",
            "--risk=1",
            "--output-dir=/tmp/sqlmap",  # nosec B108
            "--results-file=/tmp/sqlmap/results.csv",  # nosec B108
        ]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
            artifacts=["/tmp/sqlmap/results.csv"],  # nosec B108
        )
        return self._parse(result.stdout, target)

    def _parse(self, output: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        if "is vulnerable" not in output.lower():
            return findings
        findings.append(
            Finding(
                scanner=self.name,
                title="SQL injection vulnerability confirmed",
                description=(
                    "sqlmap confirmed a SQL injection vector. Refer to evidence."
                ),
                severity=Severity.CRITICAL,
                cwe="CWE-89",
                target=target.value,
                endpoint=target.value,
                evidence={"raw_excerpt": output[:2000], "confirmed": True},
                raw=json.loads(json.dumps({"output_size": len(output)})),
                remediation=(
                    "Use parameterized queries / prepared statements. "
                    "Validate and escape inputs. Apply WAF rules and audit logs."
                ),
            )
        )
        return findings
