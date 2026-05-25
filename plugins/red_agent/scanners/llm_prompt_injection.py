"""OWASP LLM01 — Prompt Injection scanner.

Active probe that walks the curated ``injection.yaml`` corpus and
sends each payload to the target chat endpoint via a sandboxed curl.
Detection is rule-based per :func:`_llm_probe.detect_outcome`. Each
positive emits a redacted Finding (CWE-1426). Stop conditions and
rate limiting are inherited from the shared probe driver.

The scanner refuses to start unless the engagement RoE has already
capped the request to ``ACTIVE`` or above. Combined with the
existing autonomy ladder this means the probe only runs once an
operator has explicitly granted ``execute_active`` on the engagement.
"""

from __future__ import annotations

from plugins.red_agent.models import Finding, ScanIntensity, Target
from plugins.red_agent.scanners._llm_probe import load_payloads, run_probes
from plugins.red_agent.scanners.base import Scanner, ScannerKind

CORPUS_FILENAME = "injection.yaml"


class LLMPromptInjectionScanner(Scanner):
    """Active prompt-injection probe."""

    name = "llm_prompt_injection"
    kind = ScannerKind.DAST
    supports_intensity = (ScanIntensity.ACTIVE, ScanIntensity.INTRUSIVE)
    image = "curlimages/curl:latest"
    requires_network = True
    default_timeout = 1800

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if intensity not in self.supports_intensity:
            return []
        payloads = load_payloads(CORPUS_FILENAME)
        run_result = await run_probes(
            scanner_name=self.name,
            sandbox=self.sandbox,
            image=self.image,
            timeout=self.timeout,
            target=target,
            payloads=payloads,
        )
        return run_result.findings


__all__ = ["LLMPromptInjectionScanner", "CORPUS_FILENAME"]
