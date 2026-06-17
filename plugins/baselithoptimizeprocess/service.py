"""Application service binding BOP's subsystems together.

This is the plugin's core seam: the store, the metrics broker, the pure detection
functions, and the optimizer agent are composed here once and exposed through a
small, intention-revealing API. The FastAPI router is a thin adapter over this
object, keeping transport concerns out of the domain logic. Every method is
async (Dogma I) and the heavy collaborators are injected (Dogma III), so the
in-memory backend can be swapped for a durable one with no caller changes.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from core.observability import get_tracer
from core.observability.logging import get_logger

from . import metrics
from .agent import BopOptimizerAgent
from .anomaly import BreachForecast
from .api_models import RegisterProcessRequest
from .automation import evaluate_rules
from .automation_models import ActionType, AutomationRule, RuleFiring
from .conformance import check_conformance
from .detection import aggregate_kpi, detect_bottleneck
from .event_models import ConformanceReport, Event, MiningResult
from .metrics_stream import MetricsBroker
from .mining import mine_event_log
from .webhook_security import WebhookValidationError, validate_webhook_url
from .models import (
    Bottleneck,
    KpiDefinition,
    KpiSnapshot,
    MetricSample,
    OptimizationProposal,
    ProcessGraph,
    ProposalStatus,
)
from ._analytics import AnalyticsMixin
from ._apply import ApplyMixin
from ._connectors import ConnectorMixin
from ._governance import GovernanceMixin
from ._insights import InsightsMixin
from ._resources import ResourceMixin
from .graph_sync import GraphSyncMixin
from .store import InMemoryProcessStore, ProcessStore
from .validation import ProcessValidationError, validate_process
from .tenancy import current_tenant
from .versioning_models import AuditAction
from .xml_import import import_process

logger = get_logger(__name__)


class BopService(
    ConnectorMixin,
    ApplyMixin,
    AnalyticsMixin,
    InsightsMixin,
    GovernanceMixin,
    ResourceMixin,
    GraphSyncMixin,
):
    """Facade over process mapping, metric monitoring, and optimization.

    Args:
        store: Persistence backend; defaults to an in-memory implementation.
        broker: Real-time fan-out broker; defaults to a fresh in-process one.
        agent: Optimizer agent; defaults to an LLM-backed agent with heuristic
            fallback.
    """

    def __init__(
        self,
        store: ProcessStore | None = None,
        broker: MetricsBroker | None = None,
        agent: BopOptimizerAgent | None = None,
    ) -> None:
        self._store: ProcessStore = store or InMemoryProcessStore()
        self._broker = broker or MetricsBroker()
        self._agent = agent or BopOptimizerAgent()
        self._tracer = get_tracer("bop-service")

    async def initialize(self) -> None:
        """Prepare the storage backend (e.g. create schema for Postgres)."""
        await self._store.initialize()

    # -- Process mapping ---------------------------------------------------

    async def register_process(self, request: RegisterProcessRequest) -> ProcessGraph:
        """Validate and persist a process supplied as a JSON DAG."""
        process = ProcessGraph(
            id=request.id,
            name=request.name,
            description=request.description,
            nodes=request.nodes,
            edges=request.edges,
            kpis=request.kpis,
            currency=request.currency,
            annual_case_volume=request.annual_case_volume,
        )
        validate_process(process)
        tenant = current_tenant()
        await self._materialize_resources(tenant, process)
        saved = await self._store.save_process(tenant, process)
        await self._record_save(tenant, saved, AuditAction.PROCESS_REGISTER)
        await self._sync_graph(tenant, saved)
        logger.info("bop_process_registered", process_id=process.id)
        return saved

    async def import_process_xml(
        self, process_id: str, xml: str, kpis: list[KpiDefinition]
    ) -> ProcessGraph:
        """Import a process from BPMN/XML, validate, and persist it."""
        process = import_process(process_id, xml, kpis)
        validate_process(process)
        tenant = current_tenant()
        saved = await self._store.save_process(tenant, process)
        await self._record_save(tenant, saved, AuditAction.PROCESS_IMPORT)
        await self._sync_graph(tenant, saved)
        logger.info(
            "bop_process_imported", process_id=process.id, nodes=len(process.nodes)
        )
        return saved

    async def get_process(self, process_id: str) -> ProcessGraph | None:
        """Fetch a process by id."""
        return await self._store.get_process(current_tenant(), process_id)

    async def list_processes(self) -> list[ProcessGraph]:
        """List all registered processes."""
        return await self._store.list_processes(current_tenant())

    async def delete_process(self, process_id: str) -> bool:
        """Delete a process and its derived state (audit ledger is retained)."""
        tenant = current_tenant()
        existing = await self._store.get_process(tenant, process_id)
        deleted = await self._store.delete_process(tenant, process_id)
        if deleted:
            if existing is not None:
                await self._unsync_graph(tenant, existing)
            await self._audit(
                tenant,
                AuditAction.PROCESS_DELETE,
                "process",
                process_id,
                process_id,
                "process and derived state deleted",
            )
        return deleted

    # -- Monitoring --------------------------------------------------------

    async def ingest_metrics(self, samples: list[MetricSample]) -> int:
        """Ingest samples, refresh derived state, and fan out live snapshots.

        Returns:
            The number of samples accepted.
        """
        if not samples:
            return 0
        tenant = current_tenant()
        process_id = samples[0].process_id
        with self._tracer.start_span(
            "bop.ingest_metrics",
            attributes={"process.id": process_id, "samples": len(samples)},
        ):
            accepted = await self._store.add_samples(tenant, samples)
            metrics.record_samples(process_id, accepted)
            process = await self._store.get_process(tenant, process_id)
            if process is not None:
                await self._refresh(tenant, process)
            return accepted

    async def snapshots(self, process_id: str) -> list[KpiSnapshot]:
        """Return the current KPI snapshots for a process."""
        tenant = current_tenant()
        process = await self._store.get_process(tenant, process_id)
        if process is None:
            return []
        return await self._compute_snapshots(tenant, process)

    async def list_bottlenecks(self, process_id: str) -> list[Bottleneck]:
        """Return the latest detected bottlenecks for a process."""
        return await self._store.list_bottlenecks(current_tenant(), process_id)

    def stream(self, process_id: str) -> AsyncIterator[dict[str, Any]]:
        """Subscribe to the real-time metrics feed for a process."""
        return self._broker.subscribe(process_id)

    # -- Optimization (human-in-the-loop) ----------------------------------

    async def optimize(
        self, process_id: str, context: str, max_proposals: int
    ) -> list[OptimizationProposal] | None:
        """Run an optimization pass; None when the process is unknown.

        Detects bottlenecks from current metrics, asks the agent for advisory
        proposals, persists them in ``PROPOSED`` status, and returns them.
        """
        tenant = current_tenant()
        process = await self._store.get_process(tenant, process_id)
        if process is None:
            return None
        started = time.perf_counter()
        with self._tracer.start_span(
            "bop.optimize", attributes={"process.id": process_id}
        ) as span:
            bottlenecks = await self._detect(tenant, process)
            proposals = await self._agent.propose(
                process, bottlenecks, context, max_proposals
            )
            for proposal in proposals:
                await self._store.save_proposal(tenant, proposal)
            span.set_attribute("bottlenecks", len(bottlenecks))
            span.set_attribute("proposals", len(proposals))
        metrics.record_optimization(
            process_id, "ok", len(proposals), time.perf_counter() - started
        )
        await self._audit(
            tenant,
            AuditAction.OPTIMIZE_RUN,
            "process",
            process_id,
            process_id,
            f"{len(proposals)} proposal(s) from {len(bottlenecks)} bottleneck(s)",
        )
        logger.info(
            "bop_optimization_pass",
            process_id=process_id,
            bottlenecks=len(bottlenecks),
            proposals=len(proposals),
        )
        return proposals

    async def list_proposals(
        self, process_id: str | None = None
    ) -> list[OptimizationProposal]:
        """List optimization proposals, optionally filtered by process."""
        return await self._store.list_proposals(current_tenant(), process_id)

    async def decide_proposal(
        self, proposal_id: str, approve: bool
    ) -> OptimizationProposal | None:
        """Record a human approve/reject decision; None if proposal unknown."""
        tenant = current_tenant()
        proposal = await self._store.get_proposal(tenant, proposal_id)
        if proposal is None:
            return None
        proposal.status = (
            ProposalStatus.APPROVED if approve else ProposalStatus.REJECTED
        )
        proposal.decided_at = datetime.now(timezone.utc)
        saved = await self._store.save_proposal(tenant, proposal)
        await self._audit(
            tenant,
            AuditAction.PROPOSAL_APPROVE if approve else AuditAction.PROPOSAL_REJECT,
            "proposal",
            proposal.id,
            proposal.process_id,
            proposal.title,
        )
        return saved

    # -- DataOps: mining, conformance, automation --------------------------

    async def import_event_log(
        self,
        process_id: str,
        events: list[Event],
        process_name: str = "",
        min_frequency: int = 0,
    ) -> MiningResult:
        """Mine an event log into a process, then ingest derived cycle times.

        The discovered model is persisted and its per-case durations are fed
        through the normal ingestion path, so a mined process is immediately
        monitored, scored, and automatable.
        """
        tenant = current_tenant()
        graph, result, samples = mine_event_log(
            process_id, events, process_name, min_frequency
        )
        validate_process(graph)
        await self._store.save_process(tenant, graph)
        await self._store.save_mining_result(tenant, result)
        await self._store.save_event_log(tenant, process_id, events)
        await self._record_save(tenant, graph, AuditAction.PROCESS_MINE)
        await self._sync_graph(tenant, graph)
        await self.ingest_metrics(samples)
        logger.info(
            "bop_event_log_mined",
            process_id=process_id,
            cases=result.case_count,
            variants=len(result.variants),
        )
        return result

    async def get_mining_result(self, process_id: str) -> MiningResult | None:
        """Return the latest mining analytics for a process."""
        return await self._store.get_mining_result(current_tenant(), process_id)

    async def run_conformance(
        self, process_id: str, events: list[Event]
    ) -> ConformanceReport | None:
        """Check an event log against a process model; None if process unknown."""
        process = await self._store.get_process(current_tenant(), process_id)
        if process is None:
            return None
        report = check_conformance(process, events)
        metrics.record_conformance(process_id, report.fitness)
        return report

    async def create_rule(self, rule: AutomationRule) -> AutomationRule:
        """Persist an automation rule.

        A webhook action's URL is SSRF-validated before the rule is stored, so a
        rule that would call an internal/loopback host is rejected up front
        rather than firing later.
        """
        if rule.action.type is ActionType.WEBHOOK:
            await validate_webhook_url(rule.action.webhook_url)
        tenant = current_tenant()
        saved = await self._store.save_rule(tenant, rule)
        await self._audit(
            tenant, AuditAction.RULE_CREATE, "rule", rule.id, rule.process_id, rule.name
        )
        return saved

    async def list_rules(self, process_id: str | None = None) -> list[AutomationRule]:
        """List automation rules, optionally filtered by process."""
        return await self._store.list_rules(current_tenant(), process_id)

    async def delete_rule(self, rule_id: str) -> bool:
        """Delete an automation rule."""
        tenant = current_tenant()
        rule = await self._store.get_rule(tenant, rule_id)
        deleted = await self._store.delete_rule(tenant, rule_id)
        if deleted:
            await self._audit(
                tenant,
                AuditAction.RULE_DELETE,
                "rule",
                rule_id,
                rule.process_id if rule else "",
                rule.name if rule else "",
            )
        return deleted

    async def list_firings(self, process_id: str) -> list[RuleFiring]:
        """Return recent automation-rule firings for a process."""
        return await self._store.list_firings(current_tenant(), process_id)

    # -- Internals ---------------------------------------------------------

    async def _run_automation(
        self,
        tenant: str,
        process: ProcessGraph,
        snapshots: list[KpiSnapshot],
        bottlenecks: list[Bottleneck],
        forecasts: list[BreachForecast],
    ) -> None:
        """Evaluate enabled rules and execute the actions that fire."""
        rules = await self._store.list_rules(tenant, process.id)
        firings = evaluate_rules(rules, snapshots, bottlenecks, forecasts)
        if not firings:
            return
        await self._store.add_firings(tenant, firings)
        for firing in firings:
            metrics.record_rule_firing(process.id, firing.action_type.value)
        await self._broker.publish(
            process.id,
            {
                "type": "automation",
                "process_id": process.id,
                "firings": [f.model_dump(mode="json") for f in firings],
            },
        )
        for firing in firings:
            await self._execute_action(process.id, firing, rules)

    async def _execute_action(
        self, process_id: str, firing: RuleFiring, rules: list[AutomationRule]
    ) -> None:
        """Run the side effect for a fired rule (all non-destructive)."""
        if firing.action_type is ActionType.RECOMMEND_OPTIMIZATION:
            await self.optimize(process_id, firing.detail, 5)
        elif firing.action_type is ActionType.WEBHOOK:
            rule = next((r for r in rules if r.id == firing.rule_id), None)
            if rule and rule.action.webhook_url:
                await self._post_webhook(rule.action.webhook_url, firing)

    @staticmethod
    async def _post_webhook(url: str, firing: RuleFiring) -> None:
        """Best-effort webhook POST; never raises into the ingestion path.

        Re-validates the URL against the SSRF guard immediately before the call
        (DNS may have changed since rule creation) and disables redirect
        following so a 30x cannot bounce the request onto an internal host.
        """
        try:
            await validate_webhook_url(url)
        except WebhookValidationError as exc:
            logger.warning("bop_webhook_blocked", url=url, error=str(exc))
            return
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                await client.post(url, json=firing.model_dump(mode="json"))
        except Exception as exc:  # noqa: BLE001 - automation must not break ingest
            logger.warning("bop_webhook_failed", url=url, error=str(exc))

    async def _refresh(self, tenant: str, process: ProcessGraph) -> None:
        """Recompute snapshots + bottlenecks and publish them to subscribers."""
        snapshots = await self._compute_snapshots(tenant, process)
        bottlenecks = await self._detect(tenant, process)
        await self._store.save_bottlenecks(tenant, process.id, bottlenecks)
        metrics.record_snapshots(process.id, snapshots)
        metrics.record_bottlenecks(process.id, bottlenecks)
        await self._broker.publish(
            process.id,
            {
                "type": "metrics",
                "process_id": process.id,
                "snapshots": [s.model_dump(mode="json") for s in snapshots],
                "bottlenecks": [b.model_dump(mode="json") for b in bottlenecks],
            },
        )
        forecasts = await self._forecasts_for(tenant, process)
        await self._evaluate_guards(tenant, process, snapshots)
        await self._run_automation(tenant, process, snapshots, bottlenecks, forecasts)

    async def _compute_snapshots(
        self, tenant: str, process: ProcessGraph
    ) -> list[KpiSnapshot]:
        """Aggregate each KPI's recent samples into a snapshot."""
        out: list[KpiSnapshot] = []
        for kpi in process.kpis:
            samples = await self._store.recent_samples(tenant, process.id, kpi.id)
            snapshot = aggregate_kpi(kpi, samples)
            if snapshot is not None:
                out.append(snapshot)
        return out

    async def _detect(self, tenant: str, process: ProcessGraph) -> list[Bottleneck]:
        """Detect bottlenecks across every KPI of a process."""
        out: list[Bottleneck] = []
        for kpi in process.kpis:
            samples = await self._store.recent_samples(tenant, process.id, kpi.id)
            bottleneck = detect_bottleneck(kpi, samples)
            if bottleneck is not None:
                out.append(bottleneck)
        return out


__all__ = ["BopService", "ProcessValidationError"]
