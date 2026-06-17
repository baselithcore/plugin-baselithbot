"""Insights sub-router: variant explorer, performance/SLA, root cause, prediction.

Kept separate from the core and DataOps routers so no single file nears the size
cap. Mounted into the main router via ``include_router``. The analytical GETs read
the *stored* event log (persisted at mine time), accept an optional case
:class:`EventFilter` via query params (Celonis-style segmentation), and delegate
to the pure engines through :class:`BopService`. SLA writes are editor-gated and
audited in the service layer; predictions are read-only.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from .api_models import PredictRequest, SlaCreateRequest
from .filtering import EventFilter
from .prediction_models import CasePrediction, PredictorModel
from .rootcause_models import RootCauseReport
from .sla_models import PerformanceReport, SlaDefinition
from .service import BopService
from .variant_models import VariantDiff, VariantReport


def _filter(
    start_after: datetime | None,
    end_before: datetime | None,
    activity: str | None,
    resource: str | None,
    variant_id: str | None,
    min_duration_seconds: float | None,
    max_duration_seconds: float | None,
) -> EventFilter:
    """Assemble an :class:`EventFilter` from the shared query parameters."""
    return EventFilter(
        start_after=start_after,
        end_before=end_before,
        activity=activity,
        resource=resource,
        variant_id=variant_id,
        min_duration_seconds=min_duration_seconds,
        max_duration_seconds=max_duration_seconds,
    )


def build_insights_router(
    service: BopService, viewer: Any, editor: Any, approver: Any
) -> Any:
    """Build the insights APIRouter bound to the BOP service.

    Args:
        service: The shared BOP service.
        viewer: A FastAPI ``Depends(...)`` read gate (no-op unless RBAC is on).
        editor: A FastAPI ``Depends(...)`` write gate (no-op unless RBAC is on).
        approver: Unused here; accepted for a uniform builder signature.
    """
    from fastapi import APIRouter, Depends, HTTPException, Query

    router = APIRouter(tags=["bop-insights"])

    def filter_dep(
        start_after: datetime | None = Query(default=None),
        end_before: datetime | None = Query(default=None),
        activity: str | None = Query(default=None),
        resource: str | None = Query(default=None),
        variant_id: str | None = Query(default=None),
        min_duration_seconds: float | None = Query(default=None, ge=0.0),
        max_duration_seconds: float | None = Query(default=None, ge=0.0),
    ) -> EventFilter:
        """Shared case-segmentation filter, parsed from query params."""
        return _filter(
            start_after,
            end_before,
            activity,
            resource,
            variant_id,
            min_duration_seconds,
            max_duration_seconds,
        )

    flt = Depends(filter_dep)

    # -- Variant explorer --------------------------------------------------

    @router.get(
        "/processes/{process_id}/variants",
        response_model=VariantReport,
        dependencies=[viewer],
    )
    async def variants(process_id: str, filters: EventFilter = flt) -> VariantReport:
        """Variant breakdown (share, throughput, conformance, cost) of the log."""
        report = await service.variant_report(process_id, filters)
        if report is None:
            raise HTTPException(status_code=404, detail="process not found")
        return report

    @router.get(
        "/processes/{process_id}/variants/diff",
        response_model=VariantDiff,
        dependencies=[viewer],
    )
    async def variants_diff(
        process_id: str,
        a: str = Query(..., description="Reference variant id."),
        b: str = Query(..., description="Comparison variant id."),
        filters: EventFilter = flt,
    ) -> VariantDiff:
        """Compare two variants side by side (added/removed steps, Δ time/cost)."""
        diff = await service.variant_diff(process_id, a, b, filters)
        if diff is None:
            raise HTTPException(status_code=404, detail="process or variant not found")
        return diff

    # -- Performance & SLA -------------------------------------------------

    @router.get(
        "/processes/{process_id}/performance",
        response_model=PerformanceReport,
        dependencies=[viewer],
    )
    async def performance(
        process_id: str, filters: EventFilter = flt
    ) -> PerformanceReport:
        """Throughput-time percentiles, per-activity waits, and SLA breach rates."""
        report = await service.performance_report(process_id, filters)
        if report is None:
            raise HTTPException(status_code=404, detail="process not found")
        return report

    @router.post(
        "/processes/{process_id}/slas",
        response_model=SlaDefinition,
        status_code=201,
        dependencies=[editor],
    )
    async def create_sla(process_id: str, body: SlaCreateRequest) -> SlaDefinition:
        """Define a service-level agreement for the process."""
        if await service.get_process(process_id) is None:
            raise HTTPException(status_code=404, detail="process not found")
        sla = SlaDefinition(
            id=uuid.uuid4().hex,
            process_id=process_id,
            name=body.name,
            scope=body.scope,
            activity=body.activity,
            threshold_seconds=body.threshold_seconds,
        )
        return await service.create_sla(sla)

    @router.get(
        "/processes/{process_id}/slas",
        response_model=list[SlaDefinition],
        dependencies=[viewer],
    )
    async def list_slas(process_id: str) -> list[SlaDefinition]:
        """List a process's SLA definitions."""
        return await service.list_slas(process_id)

    @router.delete("/slas/{sla_id}", dependencies=[editor])
    async def delete_sla(sla_id: str) -> dict[str, str]:
        """Delete an SLA definition."""
        if not await service.delete_sla(sla_id):
            raise HTTPException(status_code=404, detail="sla not found")
        return {"deleted": sla_id}

    # -- Root-cause analysis -----------------------------------------------

    @router.get(
        "/processes/{process_id}/rootcause",
        response_model=RootCauseReport,
        dependencies=[viewer],
    )
    async def rootcause(
        process_id: str,
        threshold_seconds: float | None = Query(default=None, gt=0.0),
        filters: EventFilter = flt,
    ) -> RootCauseReport:
        """Rank the case attributes most associated with slow cases.

        Without ``threshold_seconds`` the cutoff is the (filtered) log's
        upper-quartile (P75) case duration — the slowest ~25% are the bad outcome.
        """
        report = await service.root_cause_report(process_id, threshold_seconds, filters)
        if report is None:
            raise HTTPException(status_code=404, detail="process not found")
        return report

    # -- Predictive monitoring ---------------------------------------------

    @router.get(
        "/processes/{process_id}/predictor",
        response_model=PredictorModel,
        dependencies=[viewer],
    )
    async def predictor(process_id: str) -> PredictorModel:
        """The learned predictor card (per-state remaining time + successors)."""
        model = await service.predictor_model(process_id)
        if model is None:
            raise HTTPException(status_code=404, detail="process not found")
        return model

    @router.post(
        "/processes/{process_id}/predict",
        response_model=CasePrediction,
        dependencies=[viewer],
    )
    async def predict(process_id: str, body: PredictRequest) -> CasePrediction:
        """Forecast a running case (remaining time, next activity, SLA breach)."""
        prediction = await service.predict_case(process_id, body.events)
        if prediction is None:
            raise HTTPException(status_code=404, detail="process not found")
        return prediction

    return router


__all__ = ["build_insights_router"]
