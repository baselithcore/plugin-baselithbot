"""Gitleaks secrets scanner adapter.

Detects hard-coded secrets (API keys, tokens, private keys, JDBC URLs,
cloud creds) in a repository or filesystem target via the upstream
Gitleaks regex + entropy ruleset. Intentionally conservative: passive
intensity only.

Each leak becomes a HIGH-severity finding tagged ``CWE-798`` (use of
hard-coded credentials) — KEV-equivalent on the threat side because a
leaked credential is, by definition, exploitable.
"""

from __future__ import annotations

import json

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind


class GitleaksScanner(Scanner):
    name = "gitleaks"
    kind = ScannerKind.SECRET
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = "zricethezav/gitleaks:latest"
    requires_network = False
    default_timeout = 900

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        del intensity
        if target.type != TargetType.REPO:
            return []
        argv = [
            "detect",
            "--source",
            target.value,
            "--report-format",
            "json",
            "--report-path",
            "/tmp/gitleaks-report.json",  # nosec B108
            "--no-banner",
            "--exit-code",
            "0",
        ]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=False,
            scanner=self.name,
            artifacts=["/tmp/gitleaks-report.json"],  # nosec B108
        )
        report = result.artifacts.get("gitleaks-report.json", "[]")
        return self._parse(report, target)

    def _parse(self, json_text: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        try:
            doc = json.loads(json_text or "[]")
        except json.JSONDecodeError:
            return findings
        if not isinstance(doc, list):
            return findings
        for hit in doc:
            if not isinstance(hit, dict):
                continue
            secret = str(hit.get("Secret", ""))
            redacted = self._redact(secret)
            findings.append(
                Finding(
                    scanner=self.name,
                    title=f"Hard-coded secret: {hit.get('RuleID', 'unknown rule')}",
                    description=(
                        f"{hit.get('Description', 'Secret detected by Gitleaks ruleset.')} "
                        f"Found in `{hit.get('File', '?')}` line {hit.get('StartLine', '?')}."
                    ),
                    severity=Severity.HIGH,
                    cwe="CWE-798",
                    target=target.value,
                    endpoint=hit.get("File"),
                    evidence={
                        "rule_id": hit.get("RuleID"),
                        "file": hit.get("File"),
                        "line": hit.get("StartLine"),
                        "match": (hit.get("Match", "") or "")[:200],
                        "redacted_secret": redacted,
                        "commit": hit.get("Commit"),
                        "author": hit.get("Author"),
                        "date": hit.get("Date"),
                    },
                    raw={k: v for k, v in hit.items() if k != "Secret"},
                    remediation=(
                        "Rotate the leaked credential immediately, then purge "
                        "it from git history (e.g. `git filter-repo`) and add "
                        "the pattern to the secret-scanning baseline."
                    ),
                )
            )
        return findings

    @staticmethod
    def _redact(secret: str) -> str:
        if not secret:
            return ""
        if len(secret) <= 8:
            return "*" * len(secret)
        return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"
