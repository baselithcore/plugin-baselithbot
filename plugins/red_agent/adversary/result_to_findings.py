"""Convert :class:`EmulationResult` records into :class:`Finding`.

Emulation outcomes flow through the same persistence and UI as
vuln-scan findings, which means we have to map them onto the
``Finding`` shape. The mapping is intentionally conservative:

- ``EXECUTED`` (no defender block) → ``HIGH`` severity finding.
  Detection coverage is missing for that technique.
- ``BLOCKED`` → ``INFO`` severity finding. Records the positive
  evidence that the control fired; useful for purple-team reports.
- ``ERROR`` / ``TIMEOUT`` → ``LOW`` severity. Operational issue,
  not a security signal.
- ``PRECONDITION_FAILED`` / ``SKIPPED`` → no finding emitted.

Severity is opinionated — the SOC's worry is detection gaps, not
the act of emulation. ``EXECUTED`` is therefore the *bad* outcome
from a defender's perspective and earns the alarming severity.
"""

from __future__ import annotations

from plugins.red_agent.adversary.result import EmulationOutcome, EmulationResult
from plugins.red_agent.models import Finding, Severity


_SEVERITY_BY_OUTCOME: dict[EmulationOutcome, Severity | None] = {
    EmulationOutcome.EXECUTED: Severity.HIGH,
    EmulationOutcome.BLOCKED: Severity.INFO,
    EmulationOutcome.ERROR: Severity.LOW,
    EmulationOutcome.TIMEOUT: Severity.LOW,
    EmulationOutcome.PRECONDITION_FAILED: None,
    EmulationOutcome.SKIPPED: None,
}


_TITLE_BY_OUTCOME: dict[EmulationOutcome, str] = {
    EmulationOutcome.EXECUTED: "Detection gap: technique executed without block",
    EmulationOutcome.BLOCKED: "Detection coverage: technique blocked",
    EmulationOutcome.ERROR: "Emulation error",
    EmulationOutcome.TIMEOUT: "Emulation timeout",
}


def to_finding(result: EmulationResult) -> Finding | None:
    """Lift one emulation result into a :class:`Finding`.

    Returns ``None`` for outcomes that don't warrant a finding (the
    test self-skipped or didn't run). Caller is responsible for
    persisting the returned Finding through the normal pipeline so
    enrichers (ATT&CK mapper, compliance mapper, risk scorer) run
    against it the same as for any other detection.
    """

    severity = _SEVERITY_BY_OUTCOME.get(result.outcome)
    if severity is None:
        return None

    title_prefix = _TITLE_BY_OUTCOME.get(result.outcome, "Emulation result")
    return Finding(
        scanner="adversary_emulation",
        title=f"{title_prefix}: {result.technique_id}",
        description=(
            f"ATT&CK technique {result.technique_id} ran on agent "
            f"{result.agent_id} with outcome {result.outcome.value}."
        ),
        severity=severity,
        target=result.agent_id,
        endpoint=result.technique_id,
        evidence={
            "plan_id": str(result.plan_id),
            "step_index": result.step_index,
            "outcome": result.outcome.value,
            "duration_seconds": result.duration_seconds,
            "exit_code": result.exit_code,
            "stdout_excerpt": (result.stdout or "")[:512],
            "stderr_excerpt": (result.stderr or "")[:512],
        },
        raw=result.model_dump(mode="json"),
    )
