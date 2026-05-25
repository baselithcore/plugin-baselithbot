"""OWASP LLM06 — Sensitive Information Disclosure probe.

Drives ``data_leakage.yaml`` to test whether the target LLM can be
coaxed into emitting training-data fragments, hidden context
variables, embedded credentials, or PII. Detection looks for
operator-planted sentinels plus shape-based markers (key prefixes,
common email domains).
"""

from __future__ import annotations

from plugins.red_agent.models import Finding, ScanIntensity, Target
from plugins.red_agent.scanners._llm_probe import load_payloads, run_probes
from plugins.red_agent.scanners.base import Scanner, ScannerKind

CORPUS_FILENAME = "data_leakage.yaml"


class LLMDataLeakageScanner(Scanner):
    name = "llm_data_leakage"
    kind = ScannerKind.DAST
    supports_intensity = (ScanIntensity.ACTIVE, ScanIntensity.INTRUSIVE)
    image = "curlimages/curl:latest"
    requires_network = True
    default_timeout = 1800

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if intensity not in self.supports_intensity:
            return []
        payloads = load_payloads(CORPUS_FILENAME)
        result = await run_probes(
            scanner_name=self.name,
            sandbox=self.sandbox,
            image=self.image,
            timeout=self.timeout,
            target=target,
            payloads=payloads,
        )
        return result.findings


__all__ = ["LLMDataLeakageScanner", "CORPUS_FILENAME"]
