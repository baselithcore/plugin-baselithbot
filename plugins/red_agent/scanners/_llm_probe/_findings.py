"""Finding construction and detection guidance for the LLM probes.

Assembles a redacted ``Finding`` for a positive detection and the
Sigma-flavoured detection-guidance block attached to its evidence.
"""

from __future__ import annotations

from plugins.red_agent.llm_planner import redact_secrets
from plugins.red_agent.models import Finding, Target
from plugins.red_agent.scanners._llm_probe._models import (
    PayloadEntry,
    ProbeOutcome,
    TargetConfig,
)

_OUTCOME_DETECTION_TEMPLATE: dict[str, str] = {
    "leaked": (
        "Alert when a chat-completion response from the LLM application "
        "contains the planted system-prompt sentinel or other leakage "
        "markers. Build the selection from the `markers` keyword list."
    ),
    "tool_misfire": (
        "Alert when a chat-completion response emits a function/tool "
        "call that was not requested by the user — `function_call`, "
        "`tool_calls`, or named-function selectors in the keyword list."
    ),
    "bypassed": (
        "Alert when a chat-completion response carries content the "
        "model was supposed to refuse — keywords list the harmful "
        "tokens specific to this payload."
    ),
}

_OUTCOME_MITIGATIONS: dict[str, list[str]] = {
    "leaked": [
        "Move secrets out of the system prompt; rely on retrieval-time "
        "scoping instead.",
        "Add a server-side response filter that strips known sentinels "
        "before returning to the user.",
    ],
    "tool_misfire": [
        "Require user confirmation before executing tool calls with side effects.",
        "Whitelist allowed tools per session; reject anything else at "
        "the orchestrator boundary.",
    ],
    "bypassed": [
        "Layer a downstream output classifier (refusal-aware) over the "
        "raw model response.",
        "Add red-team regression tests for this payload category to CI.",
    ],
}


def _detection_guidance(
    payload: PayloadEntry,
    outcome: ProbeOutcome,
    cfg: TargetConfig,
) -> dict[str, object]:
    outcome_key = outcome.outcome or "bypassed"
    return {
        "logsource": {
            "product": "llm_application",
            "category": "chat_completion",
        },
        "detection": _OUTCOME_DETECTION_TEMPLATE[outcome_key],
        "keywords": list(outcome.matched),
        "mitigations": _OUTCOME_MITIGATIONS[outcome_key],
        "owasp": payload.category,
        "endpoint": cfg.chat_endpoint,
    }


def make_finding(
    *,
    scanner_name: str,
    target: Target,
    cfg: TargetConfig,
    payload: PayloadEntry,
    outcome: ProbeOutcome,
    request_body: dict,
    response_status: int,
    response_text: str,
) -> Finding:
    """Assemble a redacted Finding for a positive detection."""

    redacted_request = redact_secrets(request_body)
    redacted_response = redact_secrets(response_text)
    title = f"LLM {payload.category} probe matched ({outcome.outcome})"
    description = (
        f"Probe ``{payload.id}`` ({payload.category}) elicited a "
        f"{outcome.outcome} response from the target LLM. The model "
        f"violated its expected behavior on a known prompt-injection "
        f"vector — review the engagement RoE before declaring impact."
    )
    evidence = {
        "payload_id": payload.id,
        "category": payload.category,
        "outcome": outcome.outcome,
        "matched_markers": outcome.matched,
        "request": redacted_request,
        "response_status": response_status,
        "response_excerpt": redacted_response,
        "endpoint": cfg.chat_endpoint,
        "source": payload.source,
        "detection_guidance": _detection_guidance(payload, outcome, cfg),
    }
    return Finding(
        scanner=scanner_name,
        title=title,
        description=description,
        severity=payload.severity,
        cwe=payload.cwe,
        target=target.value,
        endpoint=cfg.chat_endpoint,
        evidence=evidence,
        remediation=(
            "Treat the LLM application as untrusted output: validate "
            "every model response server-side, never auto-execute tool "
            "calls without policy checks, and harden the system prompt "
            "with explicit refusal rules for the payload category."
        ),
    )
