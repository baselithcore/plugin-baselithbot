"""LLM-application recon scanner.

Passive-only fingerprinter for AI / LLM-backed web applications. Pulls
the target URL via a sandboxed curl and searches the response for
indicators of a generative-AI surface (Gradio, Streamlit-AI, OpenAI
proxy paths, HuggingFace Spaces, common chat/completion endpoints).
When detected, emits a single ``MEDIUM`` finding that points the
operator at the OWASP LLM Top 10 controls relevant to the surface.

This is the seed of the dedicated LLM-attack scanner suite — prompt
injection, tool abuse, RAG poisoning probes will land in sibling
modules. Today it gives operators something concrete to rate
``llm-top10-surface`` playbook runs against.
"""

from __future__ import annotations

import re

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind


_FINGERPRINTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("gradio", re.compile(r"gradio[-_]?(app|client|version)|gradio.live", re.I)),
    ("streamlit_ai", re.compile(r"streamlit.*\b(ai|llm|chatbot|gpt)\b", re.I)),
    (
        "openai_proxy",
        re.compile(r"/v1/(chat/completions|completions|embeddings)\b", re.I),
    ),
    ("hf_space", re.compile(r"huggingface\.co/spaces|hf-space", re.I)),
    ("langchain", re.compile(r"\blangchain\b|langserve|langgraph", re.I)),
    ("ollama", re.compile(r"\bollama\b", re.I)),
    ("anthropic_proxy", re.compile(r"/v1/messages\b|anthropic-version:", re.I)),
)


class LLMReconScanner(Scanner):
    """Passive AI/LLM application surface fingerprinter."""

    name = "llm_recon"
    kind = ScannerKind.RECON
    supports_intensity = (ScanIntensity.PASSIVE,)
    image = "curlimages/curl:latest"
    requires_network = True
    default_timeout = 60

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        del intensity
        url = self._target_to_url(target)
        if not url:
            return []
        argv = [
            "-sSL",
            "--max-time",
            "30",
            "-A",
            "BaselithRedAgent/1.0 (+https://baselithcore.io)",
            url,
        ]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
        )
        return self._parse(result.stdout, target, url)

    @staticmethod
    def _target_to_url(target: Target) -> str | None:
        if target.type == TargetType.URL:
            return target.value
        if target.type in (TargetType.HOSTNAME, TargetType.IP):
            return f"https://{target.value}/"
        return None

    def _parse(self, body: str, target: Target, url: str) -> list[Finding]:
        if not body:
            return []
        hits: list[str] = []
        for label, pattern in _FINGERPRINTS:
            if pattern.search(body):
                hits.append(label)
        if not hits:
            return []
        return [
            Finding(
                scanner=self.name,
                title="LLM-application surface detected",
                description=(
                    "Response body matched fingerprints for an AI/LLM-backed "
                    "application. The OWASP LLM Top 10 (LLM01–LLM10) controls "
                    "now apply to this asset; treat it as in-scope for prompt "
                    "injection, tool abuse, data leakage, and excessive agency."
                ),
                severity=Severity.MEDIUM,
                cwe="CWE-200",
                target=target.value,
                endpoint=url,
                evidence={
                    "fingerprints": hits,
                    "owasp_llm_top_10": [
                        "LLM01 Prompt Injection",
                        "LLM02 Insecure Output Handling",
                        "LLM06 Sensitive Information Disclosure",
                        "LLM07 Insecure Plugin Design",
                        "LLM08 Excessive Agency",
                    ],
                },
                remediation=(
                    "Run the ``llm-top10-surface`` playbook and confirm the "
                    "engagement RoE permits LLM-targeted active probes before "
                    "scheduling deeper scanners."
                ),
            )
        ]
