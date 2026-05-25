"""
RedAgent orchestrator.

Drives the scan lifecycle:

  ScanRequest
    -> GuardrailPipeline (SSRF, scope, intensity)
    -> [HITL approval if active/intrusive]
    -> for scanner in selected: SandboxRunner -> Scanner.run -> Findings
    -> Persistence (Postgres) + VulnerabilityGraph (FalkorDB)
    -> Audit + observability events

Pipeline is deterministic for the MVP; LLM-driven planning over the
attack-surface graph is a fase 2 extension hook (see _plan_next).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from core.context import get_current_tenant_id
from core.observability.logging import get_logger
from plugins.red_agent.approvals import ApprovalRegistry
from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.events import ScanEventBus
from plugins.red_agent.graph import VulnerabilityGraph
from plugins.red_agent.guardrails import (
    GuardrailDecision,
    GuardrailPipeline,
    GuardrailViolation,
)
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    ScanRequest,
    ScanResult,
    ScanStatus,
)
from plugins.red_agent._agent_helpers import (
    apply_validated_impact,
    execute_scanner,
    filter_request_scanners,
)
from plugins.red_agent._differential import apply_cache, record_fingerprints
from plugins.red_agent._scan_consumer import consume_scanner_results
from plugins.red_agent.enrichers import (
    AttackMapperEnricher,
    ComplianceMapperEnricher,
    EpssKevEnricher,
    GreyNoiseEnricher,
    OSVEnricher,
    ReachabilityEnricher,
    RiskScoringEnricher,
    VexEnricher,
)
from plugins.red_agent.ml import (
    FPClassifierService,
    LLMTriageService,
    SemanticDedupService,
)
from plugins.red_agent.integrations import WebhookNotifier
from plugins.red_agent.critic import (
    CriticContext,
    StepCritic,
    default_critic,
)
from plugins.red_agent.persistence import FingerprintStore, RedAgentPersistence
from plugins.red_agent.planner import (
    AttackPlanner,
    ChainingPlanner,
    DeterministicPlanner,
    PlannerState,
)
from plugins.red_agent.rules_of_engagement import RoEDecision, RuleOfEngagementEngine
from plugins.red_agent.sandbox_runner import SandboxRunner
from plugins.red_agent.scanners import REGISTRY

logger = get_logger(__name__)


class RedAgent:
    """Top-level autonomous Red Team agent."""

    def __init__(
        self,
        config: RedAgentConfig,
        persistence: RedAgentPersistence,
        graph: VulnerabilityGraph,
        audit: AuditLogger,
        sandbox: SandboxRunner,
        events: ScanEventBus,
        approvals: ApprovalRegistry,
        approval_timeout: int = 600,
        planner: AttackPlanner | None = None,
        triage: LLMTriageService | None = None,
        dedup: SemanticDedupService | None = None,
        fp_classifier: FPClassifierService | None = None,
        epss_kev: EpssKevEnricher | None = None,
        attack_mapper: AttackMapperEnricher | None = None,
        vex: VexEnricher | None = None,
        reachability: ReachabilityEnricher | None = None,
        risk_scorer: RiskScoringEnricher | None = None,
        compliance: ComplianceMapperEnricher | None = None,
        fingerprints: FingerprintStore | None = None,
        osv: OSVEnricher | None = None,
        greynoise: GreyNoiseEnricher | None = None,
        webhook: WebhookNotifier | None = None,
        roe: RuleOfEngagementEngine | None = None,
        critic: StepCritic | None = None,
        virustotal: Any | None = None,
        shodan: Any | None = None,
        censys: Any | None = None,
        otx: Any | None = None,
        exploit_validator: Any | None = None,
    ) -> None:
        self.config = config
        self.persistence = persistence
        self.graph = graph
        self.audit = audit
        self.sandbox = sandbox
        self.events = events
        self.approvals = approvals
        self.approval_timeout = approval_timeout
        self.guardrails = GuardrailPipeline(config)
        self.planner: AttackPlanner = planner or _build_default_planner(
            config=config, audit=audit
        )
        self.triage = triage
        self.dedup = dedup
        self.fp_classifier = fp_classifier
        self.epss_kev = epss_kev
        self.attack_mapper = attack_mapper
        self.vex = vex
        self.reachability = reachability
        self.risk_scorer = risk_scorer
        self.compliance = compliance
        self.fingerprints = fingerprints
        self.osv = osv
        self.greynoise = greynoise
        self.virustotal = virustotal
        self.shodan = shodan
        self.censys = censys
        self.otx = otx
        self.exploit_validator = exploit_validator
        self.webhook = webhook
        self.roe = roe
        self.critic: StepCritic = critic if critic is not None else default_critic()
        self._semaphore = asyncio.Semaphore(config.max_concurrent_scans)
        self._running_tasks: dict[UUID, asyncio.Task[None]] = {}

    async def submit_scan(self, request: ScanRequest) -> UUID:
        scan_id = uuid4()
        if request.tenant_id is None:
            try:
                request = request.model_copy(
                    update={"tenant_id": get_current_tenant_id()}
                )
            except Exception:  # noqa: BLE001
                pass
        request = await filter_request_scanners(
            request=request,
            enabled_scanners=self.config.enabled_scanners,
            audit=self.audit,
            scan_id=scan_id,
        )

        roe_decision = None
        if self.roe is not None and request.engagement_id is not None:
            try:
                roe_decision = await self.roe.evaluate(request)
            except GuardrailViolation as e:
                await self.audit.record(
                    scan_id=scan_id,
                    actor=request.requested_by,
                    event="scan.roe_violation",
                    payload={
                        "code": e.code,
                        "message": e.message,
                        "engagement_id": str(request.engagement_id),
                    },
                )
                raise
            request = roe_decision.effective_request

        await self.persistence.insert_scan(scan_id, request)
        await self.audit.record(
            scan_id=scan_id,
            actor=request.requested_by,
            event="scan.submitted",
            payload={
                "target": request.target.value,
                "intensity": request.intensity.value,
            },
        )

        if roe_decision is not None and roe_decision.adjustments:
            await self.audit.record(
                scan_id=scan_id,
                actor=request.requested_by,
                event="scan.roe_adjusted",
                payload={
                    "engagement_id": str(request.engagement_id),
                    "autonomy_level": roe_decision.autonomy_level.value,
                    "adjustments": roe_decision.adjustments,
                },
            )

        extra_scope = roe_decision.extra_scope if roe_decision is not None else None
        try:
            decision = self.guardrails.check(request, extra_scope=extra_scope)
        except GuardrailViolation as e:
            await self.persistence.update_status(
                scan_id, ScanStatus.FAILED, error=str(e)
            )
            await self.audit.record(
                scan_id=scan_id,
                actor=request.requested_by,
                event="scan.guardrail_violation",
                payload={"code": e.code, "message": e.message},
            )
            raise

        if roe_decision is not None and roe_decision.force_hitl:
            decision = GuardrailDecision(
                allowed=decision.allowed,
                needs_human_approval=True,
                reason=(
                    decision.reason
                    if decision.needs_human_approval
                    else "HITL forced by engagement rules"
                ),
                violations=decision.violations,
            )

        # HITL wait is handled inside the background task so submit_scan
        # returns the scan_id immediately and the UI can poll status.
        task = asyncio.create_task(
            self._run_scan(
                scan_id,
                request,
                needs_hitl=decision.needs_human_approval,
                decision=decision,
                roe_decision=roe_decision,
            )
        )
        self._running_tasks[scan_id] = task

        def _on_done(_: asyncio.Task[None], sid: UUID = scan_id) -> None:
            self._running_tasks.pop(sid, None)

        task.add_done_callback(_on_done)
        return scan_id

    async def cancel_scan(self, scan_id: UUID, actor: str) -> bool:
        """Stop an in-flight scan.

        Resolves a pending HITL approval (as rejected) so a scan stuck in
        AWAITING_APPROVAL exits its wait, then cancels the running task.
        The task's CancelledError handler in _run_scan flips the row to
        CANCELLED, audits, and emits a final status event.
        """
        # Resolve any open approval first — frees a scan stuck on HITL.
        try:
            await self.approvals.resolve(scan_id, approved=False, actor=actor)
        except Exception:  # noqa: BLE001
            pass

        task = self._running_tasks.get(scan_id)
        if task is not None and not task.done():
            task.cancel()
            await self.audit.record(
                scan_id=scan_id,
                actor=actor,
                event="scan.cancel_requested",
            )
            return True

        # Task already gone — best-effort terminal-state nudge so a stale
        # row doesn't hang in QUEUED/RUNNING after a process restart.
        existing = await self.persistence.get_scan(scan_id)
        if existing is None:
            return False
        if existing.status in (
            ScanStatus.COMPLETED,
            ScanStatus.FAILED,
            ScanStatus.CANCELLED,
        ):
            return False
        await self.persistence.update_status(
            scan_id, ScanStatus.CANCELLED, error="cancelled by operator"
        )
        await self.audit.record(
            scan_id=scan_id,
            actor=actor,
            event="scan.cancelled",
            payload={"source": "post_hoc"},
        )
        await self.events.publish(
            scan_id, {"type": "status", "status": ScanStatus.CANCELLED.value}
        )
        return True

    async def _await_approval(
        self, scan_id: UUID, request: ScanRequest, decision: GuardrailDecision
    ) -> bool:
        future = await self.approvals.open(
            scan_id, reason=decision.reason, requested_by=request.requested_by
        )
        await self.events.publish(
            scan_id,
            {
                "type": "approval_requested",
                "reason": decision.reason,
                "intensity": request.intensity.value,
            },
        )
        try:
            return await asyncio.wait_for(future, timeout=self.approval_timeout)
        except asyncio.TimeoutError:
            await self.approvals.mark_timeout(scan_id)
            await self.audit.record(
                scan_id=scan_id,
                actor="red_agent",
                event="scan.hitl_timeout",
                payload={"timeout_seconds": self.approval_timeout},
            )
            return False

    async def _run_scan(
        self,
        scan_id: UUID,
        request: ScanRequest,
        *,
        needs_hitl: bool = False,
        decision: GuardrailDecision | None = None,
        roe_decision: RoEDecision | None = None,
    ) -> None:
        if needs_hitl and decision is not None:
            await self.persistence.update_status(scan_id, ScanStatus.AWAITING_APPROVAL)
            approved = await self._await_approval(scan_id, request, decision)
            if not approved:
                await self.persistence.update_status(
                    scan_id, ScanStatus.CANCELLED, error="HITL denied"
                )
                await self.audit.record(
                    scan_id=scan_id,
                    actor=request.requested_by,
                    event="scan.hitl_denied",
                )
                return

        async with self._semaphore:
            await self.persistence.update_status(scan_id, ScanStatus.RUNNING)
            await self.audit.record(
                scan_id=scan_id, actor="red_agent", event="scan.started"
            )
            await self.events.publish(
                scan_id, {"type": "status", "status": ScanStatus.RUNNING.value}
            )
            # Graph client is synchronous (FalkorDB / Redis-py); offload to a
            # thread so a slow Cypher round-trip does not block the event loop
            # — otherwise WebSocket frames stall and the UI shows a frozen
            # "running" badge with 0 findings.
            await asyncio.to_thread(
                self.graph.upsert_target, request.target, request.tenant_id
            )
            await asyncio.to_thread(self.graph.upsert_scan, scan_id, request)

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
                bug_bounty_mode=self.config.bug_bounty_mode,
                global_scope=list(self.config.scope_allowlist),
            )
            try:
                while True:
                    last_iter_findings = (
                        all_findings[-len(all_findings) :]
                        if planner_state.iterations == 0
                        else all_findings[len(planner_state.seen_findings) :]
                    )
                    step = await self.planner.plan(planner_state, last_iter_findings)
                    if step is None:
                        break
                    review = self.critic.review(step, critic_ctx)
                    if not review.approved:
                        await self.audit.record(
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
                        await self.audit.record(
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
                    await self.audit.record(
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
                        fingerprints=self.fingerprints,
                        persistence=self.persistence,
                        audit=self.audit,
                        scan_id=scan_id,
                        request=request,
                        step=step,
                        ttl_seconds=self.config.differential_ttl_seconds,
                        enabled=self.config.differential_enabled,
                    )
                    if reused_findings:
                        await self.persistence.insert_findings(scan_id, reused_findings)
                        all_findings.extend(reused_findings)
                    pending = {
                        asyncio.create_task(
                            self._run_one_scanner(scanner_name, step_request),
                            name=f"scanner:{scanner_name}",
                        ): scanner_name
                        for scanner_name in scanners_to_run
                    }
                    new_findings = await self._consume_scanner_results(
                        pending=pending,
                        scan_id=scan_id,
                        request=request,
                        step=step,
                    )
                    all_findings.extend(new_findings)
                    await record_fingerprints(
                        fingerprints=self.fingerprints,
                        scan_id=scan_id,
                        request=request,
                        step=step,
                        scanners_ran=scanners_to_run,
                        enabled=self.config.differential_enabled,
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
            await self.persistence.update_status(scan_id, terminal, error=error)

            duration = (datetime.now(timezone.utc) - started).total_seconds()
            await self.audit.record(
                scan_id=scan_id,
                actor="red_agent",
                event="scan.finished",
                payload={
                    "status": terminal.value,
                    "findings": len(all_findings),
                    "duration_seconds": duration,
                },
            )
            await self.events.publish(
                scan_id,
                {
                    "type": "status",
                    "status": terminal.value,
                    "findings": len(all_findings),
                },
            )

    async def _run_one_scanner(
        self, scanner_name: str, request: ScanRequest
    ) -> list[Finding]:
        return await execute_scanner(
            scanner_name=scanner_name,
            target=request.target,
            intensity=request.intensity,
            sandbox=self.sandbox,
            timeouts=self.config.scanner_timeouts,
            fallback_timeout=self.config.sandbox_timeout_seconds,
            output_max_bytes=self.config.scanner_output_max_bytes,
        )

    async def _consume_scanner_results(
        self,
        *,
        pending: dict[asyncio.Task[list[Finding]], str],
        scan_id: UUID,
        request: ScanRequest,
        step: Any,
    ) -> list[Finding]:
        return await consume_scanner_results(
            pending=pending,
            scan_id=scan_id,
            request=request,
            step=step,
            audit=self.audit,
            events=self.events,
            persistence=self.persistence,
            graph=self.graph,
            fp_classifier=self.fp_classifier,
            triage=self.triage,
            dedup=self.dedup,
            epss_kev=self.epss_kev,
            attack_mapper=self.attack_mapper,
            vex=self.vex,
            reachability=self.reachability,
            risk_scorer=self.risk_scorer,
            compliance=self.compliance,
            osv=self.osv,
            greynoise=self.greynoise,
            webhook=self.webhook,
            validated_only=self.config.validated_impact_only,
            validated_min_cvss=self.config.validated_impact_min_cvss,
            virustotal=getattr(self, "virustotal", None),
            shodan=getattr(self, "shodan", None),
            censys=getattr(self, "censys", None),
            otx=getattr(self, "otx", None),
            exploit_validator=getattr(self, "exploit_validator", None),
        )

    def _apply_validated_impact(self, findings: list[Finding]) -> list[Finding]:
        # Instance-bound shim around ``apply_validated_impact`` kept for tests
        # and external callers after the helper moved to ``_agent_helpers``.
        return apply_validated_impact(
            findings,
            enabled=self.config.validated_impact_only,
            min_cvss=self.config.validated_impact_min_cvss,
        )

    async def get_scan(self, scan_id: UUID) -> ScanResult | None:
        return await self.persistence.get_scan(scan_id)

    async def quick_scan(self, target_value: str, requested_by: str) -> UUID:
        from plugins.red_agent.models import Target, TargetType

        intensity = ScanIntensity.PASSIVE
        candidates = [
            name
            for name in self.config.enabled_scanners
            if name in REGISTRY and intensity in REGISTRY[name].supports_intensity
        ] or ["nmap", "nuclei"]
        return await self.submit_scan(
            ScanRequest(
                target=Target(type=TargetType.URL, value=target_value),
                scanners=candidates,
                intensity=intensity,
                requested_by=requested_by,
            )
        )


def _build_default_planner(
    *, config: RedAgentConfig, audit: AuditLogger
) -> AttackPlanner:
    """Pick the planner backend that matches the active configuration.

    LLM planner wins when explicitly enabled; otherwise the rule-based
    chain (multi-step or single-pass deterministic) is used. Kept out
    of ``RedAgent.__init__`` to avoid an import cycle through the LLM
    planner's optional ``core.services.llm`` dependency.
    """

    if getattr(config, "llm_planner_enabled", False):
        from plugins.red_agent.llm_planner import build_llm_planner

        return build_llm_planner(
            config=config,
            audit=audit,
            enabled_scanners=list(config.enabled_scanners),
            fallback_planner=ChainingPlanner(
                max_iterations=config.chain_max_iterations
            ),
        )
    if config.multi_step_chains:
        return ChainingPlanner(max_iterations=config.chain_max_iterations)
    return DeterministicPlanner()
