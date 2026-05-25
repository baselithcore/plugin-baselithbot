"""Semgrep SAST scanner adapter.

Runs Semgrep with a curated rule set against a repo or filesystem target.
Default ruleset: ``p/ci`` (Semgrep curated CI baseline) which folds in
``p/owasp-top-ten``, ``p/secrets``, language-native security rules, and
the OSS community top 1000. Operators can override via the
``ruleset`` constructor argument.

Output: Semgrep's structured JSON. Each match becomes a finding mapped
through the rule severity (`ERROR`/`WARNING`/`INFO`) and tagged with the
rule id, owasp-top-10 category, cwe, and the file:line location.
"""

from __future__ import annotations

import json
from typing import Any

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind


_SEMGREP_SEVERITY_MAP: dict[str, Severity] = {
    "ERROR": Severity.HIGH,
    "WARNING": Severity.MEDIUM,
    "INFO": Severity.LOW,
}


class SemgrepScanner(Scanner):
    """Semgrep SAST adapter.

    Only meaningful for repository/filesystem targets — URL/IP targets are
    a no-op so misconfigured pipelines do not crash.
    """

    name = "semgrep"
    kind = ScannerKind.SAST
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = "semgrep/semgrep:latest"
    requires_network = True
    default_timeout = 1800
    default_ruleset = "p/ci"

    def __init__(
        self, sandbox: Any, timeout: int | None = None, ruleset: str | None = None
    ) -> None:
        super().__init__(sandbox, timeout)
        self.ruleset = ruleset or self.default_ruleset

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        del intensity
        if target.type not in (TargetType.REPO,):
            return []
        argv = [
            "semgrep",
            "scan",
            "--config",
            self.ruleset,
            "--json",
            "--quiet",
            "--metrics=off",
            "--timeout",
            "300",
            target.value,
        ]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
        )
        return self._parse(result.stdout, target)

    def _parse(self, json_text: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        try:
            doc = json.loads(json_text)
        except json.JSONDecodeError:
            return findings
        for r in doc.get("results", []) or []:
            extra = r.get("extra") or {}
            metadata = extra.get("metadata") or {}
            sev_raw = str(extra.get("severity", "INFO")).upper()
            cwe = self._extract_cwe(metadata)
            owasp = metadata.get("owasp")
            start = r.get("start") or {}
            findings.append(
                Finding(
                    scanner=self.name,
                    title=f"{r.get('check_id', 'semgrep')} ({metadata.get('category', 'security')})",
                    description=str(extra.get("message", "")),
                    severity=_SEMGREP_SEVERITY_MAP.get(sev_raw, Severity.LOW),
                    cwe=cwe,
                    target=target.value,
                    endpoint=r.get("path"),
                    evidence={
                        "rule_id": r.get("check_id"),
                        "owasp": owasp,
                        "category": metadata.get("category"),
                        "technology": metadata.get("technology"),
                        "line": start.get("line"),
                        "col": start.get("col"),
                        "snippet": (extra.get("lines") or "")[:500],
                    },
                    raw=r,
                    remediation=(
                        extra.get("fix")
                        or metadata.get("fix")
                        or "Review the flagged code path; apply the rule's recommended fix."
                    ),
                )
            )
        return findings

    @staticmethod
    def _extract_cwe(metadata: dict[str, Any]) -> str | None:
        cwe_field = metadata.get("cwe")
        if isinstance(cwe_field, list) and cwe_field:
            cwe_field = cwe_field[0]
        if isinstance(cwe_field, str) and cwe_field.upper().startswith("CWE-"):
            return cwe_field.upper().split(":", 1)[0].strip()
        if isinstance(cwe_field, str) and cwe_field.strip().isdigit():
            return f"CWE-{cwe_field.strip()}"
        return None
