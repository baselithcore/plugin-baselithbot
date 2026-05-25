"""OWASP LLM07 + LLM08 — tool abuse / excessive agency probe.

Sends payloads from ``tool_abuse.yaml`` and flags responses that
emit an unauthorized tool/function call, attempt SSRF via a fetch
tool, or escalate privileges through a `set_role`-style invocation.
Findings carry CWE-1426 by default, with payload-level overrides
for SSRF (CWE-918) and command injection (CWE-78).
"""

from __future__ import annotations

from plugins.red_agent.models import Finding, ScanIntensity, Target
from plugins.red_agent.scanners._llm_probe import load_payloads, run_probes
from plugins.red_agent.scanners.base import Scanner, ScannerKind

CORPUS_FILENAME = "tool_abuse.yaml"


class LLMToolAbuseScanner(Scanner):
    name = "llm_tool_abuse"
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


__all__ = ["LLMToolAbuseScanner", "CORPUS_FILENAME"]
