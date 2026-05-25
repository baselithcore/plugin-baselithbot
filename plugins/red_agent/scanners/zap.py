"""OWASP ZAP baseline scanner adapter."""

from __future__ import annotations

import json

from plugins.red_agent.models import Finding, ScanIntensity, Severity, Target
from plugins.red_agent.scanners.base import Scanner, ScannerKind

_RISK_MAP: dict[str, Severity] = {
    "0": Severity.INFO,
    "1": Severity.LOW,
    "2": Severity.MEDIUM,
    "3": Severity.HIGH,
}


class ZapBaselineScanner(Scanner):
    name = "zap"
    kind = ScannerKind.DAST
    supports_intensity = (
        ScanIntensity.PASSIVE,
        ScanIntensity.ACTIVE,
    )
    image = "ghcr.io/zaproxy/zaproxy:stable"
    requires_network = True
    default_timeout = 1800

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        script = (
            "zap-baseline.py"
            if intensity == ScanIntensity.PASSIVE
            else "zap-full-scan.py"
        )
        argv = [
            script,
            "-t",
            target.value,
            "-J",
            "/zap/wrk/report.json",
            "-I",
        ]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
            artifacts=["/zap/wrk/report.json"],
        )
        return self._parse(result.artifacts.get("report.json", "{}"), target)

    def _parse(self, json_text: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        try:
            doc = json.loads(json_text)
        except json.JSONDecodeError:
            return findings

        for site in doc.get("site", []):
            for alert in site.get("alerts", []):
                risk = str(alert.get("riskcode", "0"))
                cwe = alert.get("cweid")
                instances = alert.get("instances") or [{}]
                for instance in instances:
                    findings.append(
                        Finding(
                            scanner=self.name,
                            title=alert.get("name", "zap alert"),
                            description=alert.get("desc", ""),
                            severity=_RISK_MAP.get(risk, Severity.INFO),
                            cwe=f"CWE-{cwe}" if cwe else None,
                            target=target.value,
                            endpoint=instance.get("uri"),
                            evidence={
                                "method": instance.get("method"),
                                "evidence": instance.get("evidence"),
                                "param": instance.get("param"),
                            },
                            raw=alert,
                            remediation=alert.get("solution"),
                        )
                    )
        return findings
