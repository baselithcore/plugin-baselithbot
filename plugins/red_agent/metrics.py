"""Prometheus metrics for the Red Agent.

Centralizes counters / gauges / histograms used by the LLM planner
and the OWASP LLM Top 10 active probes. Naming follows the
``red_agent_*`` prefix to keep red-agent telemetry distinct from the
``mas_*`` core metrics.

All counters are safe to import unconditionally — ``prometheus_client``
is already a hard dependency of the project; no try/except wrapper
is needed.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

LLM_PLANNER_CALLS_TOTAL = Counter(
    "red_agent_llm_planner_calls_total",
    "LLM planner provider calls labeled by provider and outcome.",
    ["provider", "outcome"],
)

LLM_PLANNER_TOKENS_TOTAL = Counter(
    "red_agent_llm_planner_tokens_total",
    "Total tokens billed by the LLM planner across all scans.",
    ["provider", "model"],
)

LLM_PLANNER_LATENCY_SECONDS = Histogram(
    "red_agent_llm_planner_latency_seconds",
    "Wall-clock latency of LLM planner provider calls.",
    ["provider"],
)

LLM_PROBE_FINDINGS_TOTAL = Counter(
    "red_agent_llm_probe_findings_total",
    "Findings emitted by the LLM-attack probe scanners.",
    ["scanner", "outcome", "category"],
)

LLM_PROBE_REQUESTS_TOTAL = Counter(
    "red_agent_llm_probe_requests_total",
    "Probe requests sent by the LLM-attack scanners.",
    ["scanner", "result"],  # result: ok / 5xx / sandbox_error
)

LLM_PROBE_HALTED_TOTAL = Counter(
    "red_agent_llm_probe_halted_total",
    "Probe runs that halted before walking the full corpus.",
    ["scanner", "reason"],
)


__all__ = [
    "LLM_PLANNER_CALLS_TOTAL",
    "LLM_PLANNER_LATENCY_SECONDS",
    "LLM_PLANNER_TOKENS_TOTAL",
    "LLM_PROBE_FINDINGS_TOTAL",
    "LLM_PROBE_HALTED_TOTAL",
    "LLM_PROBE_REQUESTS_TOTAL",
]
