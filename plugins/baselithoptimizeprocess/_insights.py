"""Insights mixin for :class:`BopService`: variants, performance, root cause, SLAs.

The advanced process-mining lenses, split out (like :class:`AnalyticsMixin`) to
keep the service body under the size cap. All three analyses run against the
*stored* event log — mine once, analyse repeatedly — so they need no event payload
on the request. SLA definitions are persisted governance artefacts and audited on
write. The mixin only touches ``self._store``, the tenant context, and the sibling
``_audit`` helper, so it composes cleanly with the rest of the service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from .event_models import Event
from .filtering import EventFilter, filter_events
from .performance import analyze_performance
from .prediction import build_predictor
from .prediction_models import CasePrediction, PredictorModel
from .rootcause import analyze_root_cause
from .rootcause_models import RootCauseReport
from .sla_models import PerformanceReport, SlaDefinition
from .store import ProcessStore
from .tenancy import current_tenant
from .variant_models import VariantDiff, VariantReport
from .variants import analyze_variants, diff_variants
from .versioning_models import AuditAction

if TYPE_CHECKING:  # for the cast that reaches the sibling GovernanceMixin._audit
    from .service import BopService


class InsightsMixin:
    """Variant / performance / root-cause / SLA / prediction behaviour."""

    _store: ProcessStore

    async def _filtered_log(
        self, tenant: str, process_id: str, filters: EventFilter | None
    ) -> list[Event]:
        """Fetch the stored event log and apply an optional case filter."""
        events = await self._store.get_event_log(tenant, process_id)
        return filter_events(events, filters)

    async def variant_report(
        self, process_id: str, filters: EventFilter | None = None
    ) -> VariantReport | None:
        """Variant breakdown of the stored log; None when the process is unknown."""
        tenant = current_tenant()
        process = await self._store.get_process(tenant, process_id)
        if process is None:
            return None
        events = await self._filtered_log(tenant, process_id, filters)
        return analyze_variants(process, events)

    async def variant_diff(
        self,
        process_id: str,
        a_id: str,
        b_id: str,
        filters: EventFilter | None = None,
    ) -> VariantDiff | None:
        """Compare two variants; None if process unknown or an id is absent."""
        report = await self.variant_report(process_id, filters)
        if report is None:
            return None
        return diff_variants(report, a_id, b_id)

    async def performance_report(
        self, process_id: str, filters: EventFilter | None = None
    ) -> PerformanceReport | None:
        """Throughput + SLA report over the stored log; None if process unknown."""
        tenant = current_tenant()
        process = await self._store.get_process(tenant, process_id)
        if process is None:
            return None
        events = await self._filtered_log(tenant, process_id, filters)
        slas = await self._store.list_slas(tenant, process_id)
        return analyze_performance(process_id, events, slas)

    async def root_cause_report(
        self,
        process_id: str,
        threshold_seconds: float | None = None,
        filters: EventFilter | None = None,
    ) -> RootCauseReport | None:
        """Rank factors behind slow cases; None when the process is unknown."""
        tenant = current_tenant()
        process = await self._store.get_process(tenant, process_id)
        if process is None:
            return None
        events = await self._filtered_log(tenant, process_id, filters)
        return analyze_root_cause(process_id, events, threshold_seconds)

    # -- Predictive monitoring (case-level) --------------------------------

    async def predictor_model(self, process_id: str) -> PredictorModel | None:
        """The learned predictor card over history; None if process unknown."""
        tenant = current_tenant()
        process = await self._store.get_process(tenant, process_id)
        if process is None:
            return None
        events = await self._store.get_event_log(tenant, process_id)
        return build_predictor(process_id, events).model()

    async def predict_case(
        self, process_id: str, running_trace: list[Event]
    ) -> CasePrediction | None:
        """Forecast a running case from the learned model; None if unknown/empty."""
        tenant = current_tenant()
        process = await self._store.get_process(tenant, process_id)
        if process is None or not running_trace:
            return None
        events = await self._store.get_event_log(tenant, process_id)
        slas = await self._store.list_slas(tenant, process_id)
        return build_predictor(process_id, events).predict(running_trace, slas)

    # -- SLA definitions (persisted, audited) ------------------------------

    async def create_sla(self, sla: SlaDefinition) -> SlaDefinition:
        """Persist a service-level agreement and audit its creation."""
        tenant = current_tenant()
        saved = await self._store.save_sla(tenant, sla)
        await cast("BopService", self)._audit(
            tenant, AuditAction.SLA_CREATE, "sla", sla.id, sla.process_id, sla.name
        )
        return saved

    async def list_slas(self, process_id: str | None = None) -> list[SlaDefinition]:
        """List SLA definitions, optionally filtered to one process."""
        return await self._store.list_slas(current_tenant(), process_id)

    async def delete_sla(self, sla_id: str) -> bool:
        """Delete an SLA definition; audit the deletion when it existed."""
        tenant = current_tenant()
        sla = await self._store.get_sla(tenant, sla_id)
        deleted = await self._store.delete_sla(tenant, sla_id)
        if deleted:
            await cast("BopService", self)._audit(
                tenant,
                AuditAction.SLA_DELETE,
                "sla",
                sla_id,
                sla.process_id if sla else "",
                sla.name if sla else "",
            )
        return deleted


__all__ = ["InsightsMixin"]
