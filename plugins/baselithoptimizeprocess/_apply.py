"""Governed apply + rollback mixin for :class:`BopService`.

Promotes a candidate redesign to the live process as a new immutable version,
tracked as an :class:`AppliedChange` so it can be reverted to the prior version
at any time. An optional :class:`ChangeGuard` arms automatic rollback when a
watched KPI regresses past a threshold after the change goes live — evaluated on
every metric ingest via :meth:`_evaluate_guards`.

Self-contained (depends only on ``self._store`` + tenant/actor context and the
pure version/audit helpers) so it composes with the other service mixins without
cross-mixin coupling.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

from .api_models import RegisterProcessRequest
from .apply_models import AppliedChange, ChangeGuard, ChangeStatus
from .audit import build_version, content_hash, make_event
from .detection import aggregate_kpi
from .models import KpiDirection, KpiSnapshot, ProcessGraph, ProposalStatus
from .store import ProcessStore
from .tenancy import current_actor, current_tenant
from .validation import validate_process
from .versioning_models import AuditAction

if TYPE_CHECKING:  # for the cast that reaches sibling-mixin methods on the service
    from .service import BopService


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class ApplyMixin:
    """Governed change application + rollback behaviour for the BOP service."""

    _store: ProcessStore

    async def apply_change(
        self,
        process_id: str,
        request: RegisterProcessRequest,
        proposal_id: str = "",
        guard: ChangeGuard | None = None,
    ) -> AppliedChange | None:
        """Apply a candidate redesign as a new version; None if process unknown."""
        tenant = current_tenant()
        actor = current_actor()
        baseline = await self._store.get_process(tenant, process_id)
        if baseline is None:
            return None
        variant = ProcessGraph(
            id=baseline.id,
            name=request.name or baseline.name,
            description=request.description,
            nodes=request.nodes,
            edges=request.edges,
            kpis=request.kpis,
            currency=request.currency,
            annual_case_volume=request.annual_case_volume,
        )
        validate_process(variant)
        await cast("BopService", self)._materialize_resources(tenant, variant)
        prev = await self._store.latest_version(tenant, process_id)
        from_version = prev.version if prev else None

        await self._store.save_process(tenant, variant)
        await self._persist_version(
            tenant, variant, actor, AuditAction.PROCESS_APPLY, "change applied"
        )
        await cast("BopService", self)._sync_graph(tenant, variant)
        latest = await self._store.latest_version(tenant, process_id)
        to_version = latest.version if latest else 1

        baseline_value = None
        status = ChangeStatus.ACTIVE
        if guard is not None:
            baseline_value = await self._current_kpi_value(
                tenant, baseline, guard.kpi_id
            )
            status = ChangeStatus.MONITORING

        change = AppliedChange(
            id=uuid.uuid4().hex,
            process_id=process_id,
            proposal_id=proposal_id,
            from_version=from_version,
            to_version=to_version,
            status=status,
            guard=guard,
            baseline_value=baseline_value,
            applied_by=actor,
            detail=request.name or baseline.name,
        )
        await self._store.save_change(tenant, change)
        await self._mark_proposal_applied(tenant, proposal_id)
        return change

    async def rollback_change(self, change_id: str) -> AppliedChange | None:
        """Revert an applied change to its prior version; None if not reversible."""
        tenant = current_tenant()
        actor = current_actor()
        change = await self._store.get_change(tenant, change_id)
        if (
            change is None
            or change.status is ChangeStatus.ROLLED_BACK
            or change.from_version is None
        ):
            return None
        version = await self._store.get_version(
            tenant, change.process_id, change.from_version
        )
        if version is None:
            return None
        await self._store.save_process(tenant, version.graph)
        await self._persist_version(
            tenant,
            version.graph,
            actor,
            AuditAction.PROCESS_ROLLBACK,
            f"rolled back to v{change.from_version}",
        )
        await cast("BopService", self)._sync_graph(tenant, version.graph)
        change.status = ChangeStatus.ROLLED_BACK
        change.resolved_at = _utcnow()
        return await self._store.save_change(tenant, change)

    async def rollback_to_version(
        self, process_id: str, version: int
    ) -> ProcessGraph | None:
        """Manually restore a named prior version as the live process."""
        tenant = current_tenant()
        actor = current_actor()
        snapshot = await self._store.get_version(tenant, process_id, version)
        if snapshot is None:
            return None
        await self._store.save_process(tenant, snapshot.graph)
        await self._persist_version(
            tenant,
            snapshot.graph,
            actor,
            AuditAction.PROCESS_ROLLBACK,
            f"manual rollback to v{version}",
        )
        await cast("BopService", self)._sync_graph(tenant, snapshot.graph)
        return await self._store.get_process(tenant, process_id)

    async def list_changes(self, process_id: str) -> list[AppliedChange]:
        """List a process's applied changes, newest first."""
        return await self._store.list_changes(current_tenant(), process_id)

    # -- Internals ---------------------------------------------------------

    async def _evaluate_guards(
        self, tenant: str, process: ProcessGraph, snapshots: list[KpiSnapshot]
    ) -> None:
        """Auto-roll-back monitored changes whose guarded KPI has regressed."""
        changes = await self._store.list_changes(tenant, process.id)
        snap_by = {s.kpi_id: s for s in snapshots}
        kpis = {k.id: k for k in process.kpis}
        for change in changes:
            guard = change.guard
            if change.status is not ChangeStatus.MONITORING or guard is None:
                continue
            snap = snap_by.get(guard.kpi_id)
            kpi = kpis.get(guard.kpi_id)
            if snap is None or kpi is None or not change.baseline_value:
                continue
            regression = _regression_pct(
                kpi.direction, change.baseline_value, snap.value
            )
            if regression > guard.max_regression_pct:
                await self.rollback_change(change.id)

    async def _persist_version(
        self,
        tenant: str,
        graph: ProcessGraph,
        actor: str,
        action: AuditAction,
        detail: str,
    ) -> None:
        """Save a new version on content change, then audit the action."""
        prev = await self._store.latest_version(tenant, graph.id)
        if prev is None or prev.content_hash != content_hash(graph):
            await self._store.add_version(tenant, build_version(graph, prev, actor))
        await self._store.add_audit(
            tenant,
            make_event(tenant, actor, action, "process", graph.id, graph.id, detail),
        )

    async def _current_kpi_value(
        self, tenant: str, process: ProcessGraph, kpi_id: str
    ) -> float | None:
        """Current aggregated value of one KPI, or None when unmeasured."""
        kpi = next((k for k in process.kpis if k.id == kpi_id), None)
        if kpi is None:
            return None
        samples = await self._store.recent_samples(tenant, process.id, kpi_id)
        snapshot = aggregate_kpi(kpi, samples)
        return snapshot.value if snapshot else None

    async def _mark_proposal_applied(self, tenant: str, proposal_id: str) -> None:
        """Flip an originating proposal to APPLIED, if one was supplied."""
        if not proposal_id:
            return
        proposal = await self._store.get_proposal(tenant, proposal_id)
        if proposal is not None:
            proposal.status = ProposalStatus.APPLIED
            await self._store.save_proposal(tenant, proposal)


def _regression_pct(direction: KpiDirection, baseline: float, current: float) -> float:
    """Percent the KPI has *worsened* (direction-aware); negative = improved."""
    if baseline == 0:
        return 0.0
    if direction is KpiDirection.MAXIMIZE:
        return (baseline - current) / abs(baseline) * 100.0
    return (current - baseline) / abs(baseline) * 100.0


__all__ = ["ApplyMixin"]
