"""Planner settings, prompt construction, and LLM-response parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from plugins.red_agent.llm_planner._redaction import redact_secrets
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Target,
    TargetType,
)
from plugins.red_agent.planner import PlannerState, PlannerStep


@dataclass
class _LLMPlannerSettings:
    model: str
    provider: str
    max_tokens_per_scan: int
    max_tokens_per_call: int
    max_iterations: int
    temperature: float
    redact: bool
    fallback_to_deterministic: bool


_VALID_INTENSITIES = {i.value for i in ScanIntensity}


def _coerce_target(payload: dict, default: Target) -> Target:
    """Build a Target from the LLM response, preferring planner-known types."""

    raw_type = (payload.get("type") or default.type.value).lower()
    raw_value = payload.get("value") or default.value
    try:
        ttype = TargetType(raw_type)
    except ValueError:
        ttype = default.type
    return Target(type=ttype, value=str(raw_value))


def _parse_step(text: str, state: PlannerState) -> PlannerStep | None:
    """Parse the LLM response text into a PlannerStep.

    Accepts a JSON object with ``stop`` (bool), ``scanners`` (list[str]),
    ``target`` (object with ``type``/``value``), ``intensity`` (string),
    ``rationale`` (string), and ``derived_from`` (list[str]). Strips
    Markdown fences if present. Returns ``None`` on stop=true or when
    the JSON is structurally invalid.
    """

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("planner response must be a JSON object")

    if payload.get("stop") is True:
        return None

    scanners = payload.get("scanners") or []
    if not isinstance(scanners, list) or not all(isinstance(s, str) for s in scanners):
        raise ValueError("scanners must be a list of strings")
    if not scanners:
        return None

    target_payload = payload.get("target") or {}
    if not isinstance(target_payload, dict):
        raise ValueError("target must be an object")
    target = _coerce_target(target_payload, state.initial_target)

    intensity_raw = (payload.get("intensity") or state.intensity.value).lower()
    if intensity_raw not in _VALID_INTENSITIES:
        raise ValueError(f"unknown intensity {intensity_raw!r}")
    intensity = ScanIntensity(intensity_raw)

    rationale = str(payload.get("rationale") or "")
    derived_from_raw = payload.get("derived_from") or []
    derived_from = (
        [str(x) for x in derived_from_raw] if isinstance(derived_from_raw, list) else []
    )

    return PlannerStep(
        scanners=[s for s in scanners if s],
        target=target,
        intensity=intensity,
        rationale=rationale,
        derived_from=derived_from,
    )


_SYSTEM_PROMPT = (
    "You are the planner for a defensive Red Team agent. Each turn you "
    "receive the engagement goal, the initial target, the scanners available, "
    "the intensity ceiling enforced by the engagement, and the findings "
    "discovered so far. You propose the NEXT scan step or stop. You never "
    "execute scanners yourself; an orchestrator runs your proposal in a "
    "sandbox and a separate critic re-checks every step against scope and "
    "intensity. Return ONLY a JSON object matching this schema: "
    '{"stop": bool, "scanners": [string], "target": {"type": string, '
    '"value": string}, "intensity": "passive"|"active"|"intrusive", '
    '"rationale": string, "derived_from": [string]}. '
    "If the previous iterations produced nothing actionable, return "
    '{"stop": true}. Keep proposals inside the engagement scope.'
)


def _build_prompt(
    state: PlannerState,
    new_findings: list[Finding],
    settings: _LLMPlannerSettings,
    enabled_scanners: list[str],
) -> str:
    findings_payload: list[dict] = []
    for f in (state.seen_findings or [])[-20:]:
        findings_payload.append(
            {
                "scanner": f.scanner,
                "title": f.title,
                "severity": f.severity.value,
                "endpoint": f.endpoint,
                "service": f.service,
                "cwe": f.cwe,
                "evidence": redact_secrets(f.evidence)
                if settings.redact
                else f.evidence,
            }
        )
    new_payload: list[dict] = []
    for f in new_findings[-20:]:
        new_payload.append(
            {
                "id": str(f.id),
                "scanner": f.scanner,
                "title": f.title,
                "severity": f.severity.value,
                "endpoint": f.endpoint,
                "service": f.service,
                "cwe": f.cwe,
                "evidence": redact_secrets(f.evidence)
                if settings.redact
                else f.evidence,
            }
        )
    ceiling = (state.autonomy_max_intensity or state.intensity).value
    body = {
        "iteration": state.iterations,
        "max_iterations": settings.max_iterations,
        "initial_target": {
            "type": state.initial_target.type.value,
            "value": state.initial_target.value,
        },
        "intensity_ceiling": ceiling,
        "requested_scanners": list(state.requested_scanners),
        "enabled_scanners": enabled_scanners,
        "seen_endpoints": sorted(state.seen_endpoints),
        "seen_services": sorted(state.seen_services),
        "previous_findings": findings_payload,
        "new_findings": new_payload,
    }
    return json.dumps(body, default=str)
