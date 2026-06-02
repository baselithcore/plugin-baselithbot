"""The scan-execution loop extracted from ``RedAgent._run_scan``.

Kept as a free coroutine taking the agent instance explicitly so the
orchestrator class stays under the 500-line file cap. Behaviour is
identical to the original method body.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from core.observability.logging import get_logger
from plugins.red_agent._differential import apply_cache, record_fingerprints
from plugins.red_agent.critic import CriticContext
from plugins.red_agent.guardrails import GuardrailDecision
from plugins.red_agent.models import (
    Finding,
    ScanRequest,
    ScanStatus,
)
from plugins.red_agent.planner import PlannerState
from plugins.red_agent.rules_of_engagement import RoEDecision

if TYPE_CHECKING:
    from plugins.red_agent.agent._agent import RedAgent

logger = get_logger(__name__)


async def await_approval(
    agent: "RedAgent",
    scan_id: UUID,
    request: ScanRequest,
    decision: GuardrailDecision,
) -> bool:
    future = await agent.approvals.open(
        scan_id, reason=decision.reason, requested_by=request.requested_by
    )
    await agent.events.publish(
        scan_id,
        {
            "type": "approval_requested",
            "reason": decision.reason,
            "intensity": request.intensity.value,
        },
    )
    try:
        return await asyncio.wait_for(future, timeout=agent.approval_timeout)
    except asyncio.TimeoutError:
        await agent.approvals.mark_timeout(scan_id)
        await agent.audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.hitl_timeout",
            payload={"timeout_seconds": agent.approval_timeout},
        )
        return False


async def run_scan(
    agent: "RedAgent",
    scan_id: UUID,
    request: ScanRequest,
    *,
    needs_hitl: bool = False,
    decision: GuardrailDecision | None = None,
    roe_decision: RoEDecision | None = None,
) -> None:
    if needs_hitl and decision is not None:
        await agent.persistence.update_status(scan_id, ScanStatus.AWAITING_APPROVAL)
        approved = await agent._await_approval(scan_id, request, decision)
        if not approved:
            await agent.persistence.update_status(
                scan_id, ScanStatus.CANCELLED, error="HITL denied"
            )
            await agent.audit.record(
                scan_id=scan_id,
                actor=request.requested_by,
                event="scan.hitl_denied",
            )
            return

    async with agent._semaphore:
        await agent.persistence.update_status(scan_id, ScanStatus.RUNNING)
        await agent.audit.record(
            scan_id=scan_id, actor="red_agent", event="scan.started"
        )
        await agent.events.publish(
            scan_id, {"type": "status", "status": ScanStatus.RUNNING.value}
        )
        # Graph client is synchronous (FalkorDB / Redis-py); offload to a
        # thread so a slow Cypher round-trip does not block the event loop
        # — otherwise WebSocket frames stall and the UI shows a frozen
        # "running" badge with 0 findings.
        await asyncio.to_thread(
            agent.graph.upsert_target, request.target, request.tenant_id
        )
        await asyncio.to_thread(agent.graph.upsert_scan, scan_id, request)

        started = datetime.now(timezone.utc)
        error: str | None = None
        cancelled = False
        all_findings: list[Finding] = []
        planner_state = PlannerState(
            initial_target=request.target,
            intensity=request.intensity,
            requested_scanners=list(request.scanners),
            scan_id=scan_id,
            autonomy_max_intensity=(
                roe_decision.effective_request.intensity
                if roe_decision is not None
                else request.intensity
            ),
        )
        critic_ctx = CriticContext(
            extra_scope=(list(roe_decision.extra_scope) if roe_decision else []),
            excluded_targets=(
                list(roe_decision.excluded_targets) if roe_decision else []
            ),
            max_intensity=request.intensity,
            bug_bounty_mode=agent.config.bug_bounty_mode,
            global_scope=list(agent.config.scope_allowlist),
        )
        try:
            while True:
                last_iter_findings = (
                    all_findings[-len(all_findings) :]
                    if planner_state.iterations == 0
                    else all_findings[len(planner_state.seen_findings) :]
                )
                step = await agent.planner.plan(planner_state, last_iter_findings)
                if step is None:
                    break
                review = agent.critic.review(step, critic_ctx)
                if not review.approved:
                    await agent.audit.record(
                        scan_id=scan_id,
                        actor="red_agent",
                        event="scan.critic_veto",
                        payload={
                            "iteration": planner_state.iterations,
                            "scanners": step.scanners,
                            "target": step.target.value,
                            "reason": review.reason,
                        },
                    )
                    break
                if review.amended_step is not None:
                    await agent.audit.record(
                        scan_id=scan_id,
                        actor="red_agent",
                        event="scan.critic_amended",
                        payload={
                            "iteration": planner_state.iterations,
                            "before": {
                                "scanners": step.scanners,
                                "target": step.target.value,
                            },
                            "after": {
                                "scanners": review.amended_step.scanners,
                                "target": review.amended_step.target.value,
                            },
                            "reason": review.reason,
                        },
                    )
                    step = review.amended_step
                await agent.audit.record(
                    scan_id=scan_id,
                    actor="red_agent",
                    event="scan.planner_step",
                    payload={
                        "iteration": planner_state.iterations,
                        "scanners": step.scanners,
                        "target": step.target.value,
                        "rationale": step.rationale,
                    },
                )
                step_request = request.model_copy(
                    update={
                        "scanners": step.scanners,
                        "target": step.target,
                        "intensity": step.intensity,
                    }
                )
                scanners_to_run, reused_findings = await apply_cache(
                    fingerprints=agent.fingerprints,
                    persistence=agent.persistence,
                    audit=agent.audit,
                    scan_id=scan_id,
                    request=request,
                    step=step,
                    ttl_seconds=agent.config.differential_ttl_seconds,
                    enabled=agent.config.differential_enabled,
                )
                if reused_findings:
                    await agent.persistence.insert_findings(scan_id, reused_findings)
                    all_findings.extend(reused_findings)
                pending = {
                    asyncio.create_task(
                        agent._run_one_scanner(scanner_name, step_request),
                        name=f"scanner:{scanner_name}",
                    ): scanner_name
                    for scanner_name in scanners_to_run
                }
                new_findings = await agent._consume_scanner_results(
                    pending=pending,
                    scan_id=scan_id,
                    request=request,
                    step=step,
                )
                all_findings.extend(new_findings)
                await record_fingerprints(
                    fingerprints=agent.fingerprints,
                    scan_id=scan_id,
                    request=request,
                    step=step,
                    scanners_ran=scanners_to_run,
                    enabled=agent.config.differential_enabled,
                )
                for scanner_name in scanners_to_run:
                    critic_ctx.executed.add((scanner_name, step.target.value))
                planner_state.seen_findings = list(all_findings)
                for f in new_findings:
                    if f.endpoint:
                        planner_state.seen_endpoints.add(f.endpoint)
                    if f.service:
                        planner_state.seen_services.add(f.service)
                planner_state.iterations += 1
        except asyncio.CancelledError:
            cancelled = True
            error = "cancelled by operator"
            logger.info("scan cancelled", extra={"scan_id": str(scan_id)})
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            logger.exception("scan failed", extra={"scan_id": str(scan_id)})

        if cancelled:
            terminal = ScanStatus.CANCELLED
        elif error:
            terminal = ScanStatus.FAILED
        else:
            terminal = ScanStatus.COMPLETED
        await agent.persistence.update_status(scan_id, terminal, error=error)

        duration = (datetime.now(timezone.utc) - started).total_seconds()
        await agent.audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.finished",
            payload={
                "status": terminal.value,
                "findings": len(all_findings),
                "duration_seconds": duration,
            },
        )
        await agent.events.publish(
            scan_id,
            {
                "type": "status",
                "status": terminal.value,
                "findings": len(all_findings),
            },
        )
