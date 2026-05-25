"""OWASP LLM02 — Insecure Output Handling probe.

Drives ``output_handling.yaml`` to elicit raw HTML/JS, SQL, shell,
or SSRF strings the host application would forward unsanitized to
a downstream interpreter. Findings carry the CWE matching the
output category (XSS → CWE-79, SQLi → CWE-89, shell → CWE-78,
SSRF → CWE-918).
"""

from __future__ import annotations

from plugins.red_agent.models import Finding, ScanIntensity, Target
from plugins.red_agent.scanners._llm_probe import load_payloads, run_probes
from plugins.red_agent.scanners.base import Scanner, ScannerKind

CORPUS_FILENAME = "output_handling.yaml"


class LLMOutputHandlingScanner(Scanner):
    name = "llm_output_handling"
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


__all__ = ["LLMOutputHandlingScanner", "CORPUS_FILENAME"]
