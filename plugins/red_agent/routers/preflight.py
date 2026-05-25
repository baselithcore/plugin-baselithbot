"""Pre-flight guardrails endpoint.

Returns the guardrail decision for a candidate scan request *without*
submitting it. The UI ScanWizard calls this on the second step so
operators see SSRF / scope / HITL outcomes before committing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.dependencies import get_red_agent_config, require_viewer
from plugins.red_agent.guardrails import (
    GuardrailDecision,
    GuardrailPipeline,
    GuardrailViolation,
)
from plugins.red_agent.models import ScanIntensity, ScanRequest, Target

router = APIRouter(prefix="/guardrails", tags=["red-agent"])


class PreflightRequest(BaseModel):
    target: Target
    scanners: list[str]
    intensity: ScanIntensity = ScanIntensity.PASSIVE


class PreflightResponse(BaseModel):
    allowed: bool
    needs_human_approval: bool
    reason: str
    violations: list[str]
    target_violation: str | None = None
    target_violation_message: str | None = None


@router.post("/preflight", dependencies=[require_viewer()])
async def preflight(
    body: PreflightRequest,
    config: RedAgentConfig = Depends(get_red_agent_config),
) -> PreflightResponse:
    pipeline = GuardrailPipeline(config)

    target_violation: str | None = None
    target_violation_message: str | None = None

    try:
        pipeline.target.validate(body.target)
    except GuardrailViolation as e:
        target_violation = e.code
        target_violation_message = e.message
        return PreflightResponse(
            allowed=False,
            needs_human_approval=False,
            reason="target validation failed",
            violations=[e.code],
            target_violation=target_violation,
            target_violation_message=target_violation_message,
        )

    request = ScanRequest(
        target=body.target,
        scanners=body.scanners,
        intensity=body.intensity,
        requested_by="preflight",
    )
    decision: GuardrailDecision = pipeline.intensity.evaluate(request)
    return PreflightResponse(
        allowed=decision.allowed,
        needs_human_approval=decision.needs_human_approval,
        reason=decision.reason,
        violations=decision.violations,
    )
