"""Shared infrastructure for the OWASP LLM Top 10 active probes.

Each `llm_*` scanner sends a curated set of payloads to a chat
endpoint and matches the response against detection rules. This
package factors out the parts common to every probe — corpus loading,
HTTP request shaping, response parsing, redaction, rate limiting,
stop conditions, finding construction.

Targets describe the LLM application via ``Target.metadata``:

  chat_endpoint            full URL of the chat/completions endpoint
  request_template         JSON object; ``{prompt}`` placeholder is
                           replaced per-request before sending
  response_path            dot-path into the JSON response body, e.g.
                           ``choices.0.message.content`` (default:
                           ``content``)
  auth_header_name         header carrying the auth token (default
                           ``Authorization``)
  auth_token               literal token, or empty when the endpoint
                           is unauthenticated. Operators wrap real
                           tokens in ``RoE.metadata`` and pass them
                           through; the scanner never logs the raw
                           value.
  system_prompt_sentinel   the marker the operator planted in the
                           system prompt at engagement setup; the
                           ``leaked`` outcome looks for this string
                           in the response.
  rate_limit_seconds       seconds between requests (default 1.0)
  max_consecutive_5xx      stop the probe after this many 5xx in a
                           row (default 5)
  max_consecutive_refusals stop after this many polite refusals in a
                           row — the model is hardened (default 10)

Findings carry CWE-1426 (Improper Validation of Generative AI Output)
unless the payload entry overrides it.

This package re-exports the same public surface previously exposed by
the ``_llm_probe`` module so existing import paths keep working.
"""

from __future__ import annotations

from plugins.red_agent.sandbox_runner import SandboxResult
from plugins.red_agent.scanners._llm_probe._findings import make_finding
from plugins.red_agent.scanners._llm_probe._http import (
    build_curl_argv,
    build_request_body,
    detect_outcome,
    extract_response_text,
    parse_curl_output,
    substitute_sentinel,
)
from plugins.red_agent.scanners._llm_probe._models import (
    DEFAULT_CWE,
    DEFAULT_REFUSAL_MARKERS,
    SENTINEL_PLACEHOLDER,
    PayloadEntry,
    ProbeOutcome,
    ProbeRun,
    TargetConfig,
    load_payloads,
)
from plugins.red_agent.scanners._llm_probe._runner import corpus_path, run_probes

__all__ = [
    "DEFAULT_CWE",
    "DEFAULT_REFUSAL_MARKERS",
    "PayloadEntry",
    "ProbeOutcome",
    "ProbeRun",
    "TargetConfig",
    "build_curl_argv",
    "build_request_body",
    "corpus_path",
    "detect_outcome",
    "extract_response_text",
    "load_payloads",
    "make_finding",
    "parse_curl_output",
    "run_probes",
    "substitute_sentinel",
]

# Keep typing-only re-export referenced so lint doesn't trim it.
_ = (SandboxResult, SENTINEL_PLACEHOLDER)
