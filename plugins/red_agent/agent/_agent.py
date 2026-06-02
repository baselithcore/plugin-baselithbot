"""RedAgent orchestrator class.

Drives the scan lifecycle:

  ScanRequest
    -> GuardrailPipeline (SSRF, scope, intensity)
    -> [HITL approval if active/intrusive]
    -> for scanner in selected: SandboxRunner -> Scanner.run -> Findings
    -> Persistence (Postgres) + VulnerabilityGraph (FalkorDB)
    -> Audit + observability events

The scan-execution loop itself lives in ``_scan_loop`` so this module
stays under the 500-line file cap.
"""

from __future__ import annotations

import asyncio
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
    StepCritic,
    default_critic,
)
from plugins.red_agent.persistence import FingerprintStore, RedAgentPersistence
from plugins.red_agent.planner import AttackPlanner
from plugins.red_agent.rules_of_engagement import RoEDecision, RuleOfEngagementEngine
from plugins.red_agent.sandbox_runner import SandboxRunner
from plugins.red_agent.scanners import REGISTRY
from plugins.red_agent.agent._planner_factory import _build_default_planner
from plugins.red_agent.agent._scan_loop import await_approval, run_scan

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
        return await await_approval(self, scan_id, request, decision)

    async def _run_scan(
        self,
        scan_id: UUID,
        request: ScanRequest,
        *,
        needs_hitl: bool = False,
        decision: GuardrailDecision | None = None,
        roe_decision: RoEDecision | None = None,
    ) -> None:
        await run_scan(
            self,
            scan_id,
            request,
            needs_hitl=needs_hitl,
            decision=decision,
            roe_decision=roe_decision,
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
