"""DataOps sub-router: process mining, conformance, and automation rules.

Kept separate from the core CRUD/monitoring router so neither file approaches the
size cap. Mounted into the main router via ``include_router``. Thin and async:
validates, delegates to :class:`BopService`, shapes HTTP responses.
"""

from __future__ import annotations

import uuid
from typing import Any

from .anomaly import Anomaly, BreachForecast
from .api_models import (
    ApplyRequest,
    ConformanceRequest,
    ConnectorPullRequest,
    ConnectorTextRequest,
    CreateRuleRequest,
    MineRequest,
    RegisterProcessRequest,
)
from .apply_models import AppliedChange
from .connectors import ConnectorParseError
from .automation_models import AutomationRule, RuleFiring
from .cost import CostReport
from .event_models import ConformanceReport, MiningResult
from .models import ProcessGraph
from .service import BopService
from .simulation import SimulationComparison, SimulationResult
from .validation import ProcessValidationError
from .versioning_models import AuditEvent, ProcessVersion
from .webhook_security import WebhookValidationError


def build_ops_router(
    service: BopService, viewer: Any, editor: Any, approver: Any
) -> Any:
    """Build the DataOps APIRouter bound to the BOP service.

    Args:
        service: The shared BOP service.
        viewer: A FastAPI ``Depends(...)`` read gate (no-op unless RBAC is on).
        editor: A FastAPI ``Depends(...)`` write gate (no-op unless RBAC is on).
        approver: A FastAPI ``Depends(...)`` privileged gate (apply / rollback).
    """
    from fastapi import APIRouter, HTTPException

    router = APIRouter(tags=["bop-dataops"])

    # -- Process mining (Celonis-style) ------------------------------------

    @router.post(
        "/processes/mine",
        response_model=MiningResult,
        status_code=201,
        dependencies=[editor],
    )
    async def mine(body: MineRequest) -> MiningResult:
        """Discover a process + analytics from an event log and persist it."""
        try:
            return await service.import_event_log(
                body.id, body.events, body.name, body.min_frequency
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get(
        "/processes/{process_id}/mining",
        response_model=MiningResult,
        dependencies=[viewer],
    )
    async def mining_result(process_id: str) -> MiningResult:
        """Return the latest mining analytics (variants, activity stats)."""
        result = await service.get_mining_result(process_id)
        if result is None:
            raise HTTPException(status_code=404, detail="no mining result")
        return result

    @router.get(
        "/processes/{process_id}/model",
        response_model=ProcessGraph,
        dependencies=[viewer],
    )
    async def discovered_model(process_id: str) -> ProcessGraph:
        """Return the (possibly mined) process model."""
        process = await service.get_process(process_id)
        if process is None:
            raise HTTPException(status_code=404, detail="process not found")
        return process

    # -- Conformance (Signavio/Celonis governance) -------------------------

    @router.post(
        "/processes/{process_id}/conformance",
        response_model=ConformanceReport,
        dependencies=[viewer],
    )
    async def conformance(
        process_id: str, body: ConformanceRequest
    ) -> ConformanceReport:
        """Score an event log against the process model."""
        report = await service.run_conformance(process_id, body.events)
        if report is None:
            raise HTTPException(status_code=404, detail="process not found")
        return report

    # -- Automation rules (Appian/Pega) ------------------------------------

    @router.post(
        "/processes/{process_id}/rules",
        response_model=AutomationRule,
        status_code=201,
        dependencies=[editor],
    )
    async def create_rule(process_id: str, body: CreateRuleRequest) -> AutomationRule:
        """Create an automation rule for a process."""
        if await service.get_process(process_id) is None:
            raise HTTPException(status_code=404, detail="process not found")
        rule = AutomationRule(
            id=uuid.uuid4().hex,
            process_id=process_id,
            name=body.name,
            trigger=body.trigger,
            action=body.action,
            enabled=body.enabled,
        )
        try:
            return await service.create_rule(rule)
        except WebhookValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get(
        "/processes/{process_id}/rules",
        response_model=list[AutomationRule],
        dependencies=[viewer],
    )
    async def list_rules(process_id: str) -> list[AutomationRule]:
        """List a process's automation rules."""
        return await service.list_rules(process_id)

    @router.delete("/rules/{rule_id}", dependencies=[editor])
    async def delete_rule(rule_id: str) -> dict[str, str]:
        """Delete an automation rule."""
        if not await service.delete_rule(rule_id):
            raise HTTPException(status_code=404, detail="rule not found")
        return {"deleted": rule_id}

    @router.get(
        "/processes/{process_id}/firings",
        response_model=list[RuleFiring],
        dependencies=[viewer],
    )
    async def list_firings(process_id: str) -> list[RuleFiring]:
        """Return recent automation-rule firings for a process."""
        return await service.list_firings(process_id)

    # -- Versioning & audit (governance) -----------------------------------

    @router.get(
        "/processes/{process_id}/versions",
        response_model=list[ProcessVersion],
        dependencies=[viewer],
    )
    async def list_versions(process_id: str) -> list[ProcessVersion]:
        """List a process's immutable version snapshots, newest first."""
        return await service.list_versions(process_id)

    @router.get(
        "/processes/{process_id}/versions/{version}",
        response_model=ProcessVersion,
        dependencies=[viewer],
    )
    async def get_version(process_id: str, version: int) -> ProcessVersion:
        """Fetch one numbered version snapshot of a process."""
        snapshot = await service.get_version(process_id, version)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="version not found")
        return snapshot

    @router.get(
        "/processes/{process_id}/audit",
        response_model=list[AuditEvent],
        dependencies=[viewer],
    )
    async def process_audit(process_id: str, limit: int = 100) -> list[AuditEvent]:
        """Return the audit trail for a single process, newest first."""
        return await service.list_audit(process_id, limit)

    @router.get("/audit", response_model=list[AuditEvent], dependencies=[viewer])
    async def tenant_audit(limit: int = 100) -> list[AuditEvent]:
        """Return the tenant-wide audit trail, newest first."""
        return await service.list_audit(None, limit)

    # -- Cost / ROI --------------------------------------------------------

    @router.get(
        "/processes/{process_id}/cost",
        response_model=CostReport,
        dependencies=[viewer],
    )
    async def cost_report(process_id: str) -> CostReport:
        """Roll up the process's node costs into per-case and annual totals."""
        report = await service.cost_report(process_id)
        if report is None:
            raise HTTPException(status_code=404, detail="process not found")
        return report

    # -- Anomaly detection + breach forecasting ----------------------------

    @router.get(
        "/processes/{process_id}/anomalies",
        response_model=list[Anomaly],
        dependencies=[viewer],
    )
    async def anomalies(process_id: str) -> list[Anomaly]:
        """Statistical KPI outliers across the process's recent samples."""
        return await service.anomalies(process_id)

    @router.get(
        "/processes/{process_id}/forecast",
        response_model=list[BreachForecast],
        dependencies=[viewer],
    )
    async def forecast(process_id: str) -> list[BreachForecast]:
        """Breach forecasts (trend projected toward target) per KPI."""
        return await service.forecasts(process_id)

    # -- Data connectors (CSV/JSON text or remote pull) --------------------

    async def _ingest(
        process_id: str, kind: str, name: str, min_frequency: int, text: str
    ) -> dict[str, Any]:
        """Dispatch parsed text to mining (events) or sample ingestion (metrics)."""
        if kind == "metrics":
            accepted = await service.ingest_metric_text(process_id, text)
            return {"kind": "metrics", "accepted": accepted}
        result = await service.ingest_event_text(process_id, text, name, min_frequency)
        return {"kind": "events", "mining": result.model_dump(mode="json")}

    @router.post("/processes/{process_id}/ingest", dependencies=[editor])
    async def ingest_text(
        process_id: str, body: ConnectorTextRequest
    ) -> dict[str, Any]:
        """Ingest an inline CSV/JSON event log or metric stream."""
        try:
            return await _ingest(
                process_id, body.kind, body.name, body.min_frequency, body.text
            )
        except (ConnectorParseError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/processes/{process_id}/pull", dependencies=[editor])
    async def pull_source(
        process_id: str, body: ConnectorPullRequest
    ) -> dict[str, Any]:
        """Pull a remote CSV/JSON source (SSRF-guarded) and ingest it."""
        try:
            if body.kind == "metrics":
                accepted = await service.pull_metrics(process_id, body.url)
                return {"kind": "metrics", "accepted": accepted}
            result = await service.pull_events(
                process_id, body.url, body.name, body.min_frequency
            )
            return {"kind": "events", "mining": result.model_dump(mode="json")}
        except (ConnectorParseError, WebhookValidationError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    # -- Executive report --------------------------------------------------

    @router.get("/processes/{process_id}/report", dependencies=[viewer])
    async def report(process_id: str, format: str = "markdown") -> Any:
        """Render an executive report as Markdown (default) or CSV."""
        from fastapi.responses import PlainTextResponse

        fmt = "csv" if format == "csv" else "markdown"
        rendered = await service.report(process_id, fmt)
        if rendered is None:
            raise HTTPException(status_code=404, detail="process not found")
        media = "text/csv" if fmt == "csv" else "text/markdown"
        ext = "csv" if fmt == "csv" else "md"
        return PlainTextResponse(
            rendered,
            media_type=media,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{process_id}-report.{ext}"'
                )
            },
        )

    # -- What-if simulation ------------------------------------------------

    @router.get(
        "/processes/{process_id}/simulate",
        response_model=SimulationResult,
        dependencies=[viewer],
    )
    async def simulate_current(process_id: str) -> SimulationResult:
        """Predict the current process's cycle time and cost-per-case."""
        result = await service.simulate(process_id)
        if result is None:
            raise HTTPException(status_code=404, detail="process not found")
        return result

    @router.post(
        "/processes/{process_id}/simulate",
        response_model=SimulationComparison,
        dependencies=[viewer],
    )
    async def simulate_variant(
        process_id: str, body: RegisterProcessRequest
    ) -> SimulationComparison:
        """What-if: compare a candidate redesign against the stored baseline."""
        comparison = await service.simulate_variant(process_id, body)
        if comparison is None:
            raise HTTPException(status_code=404, detail="process not found")
        return comparison

    # -- Governed apply + rollback -----------------------------------------

    @router.post(
        "/processes/{process_id}/apply",
        response_model=AppliedChange,
        status_code=201,
        dependencies=[approver],
    )
    async def apply_change(process_id: str, body: ApplyRequest) -> AppliedChange:
        """Apply a candidate redesign as a governed, reversible change."""
        try:
            change = await service.apply_change(
                process_id, body, body.proposal_id, body.guard
            )
        except ProcessValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if change is None:
            raise HTTPException(status_code=404, detail="process not found")
        return change

    @router.get(
        "/processes/{process_id}/changes",
        response_model=list[AppliedChange],
        dependencies=[viewer],
    )
    async def list_changes(process_id: str) -> list[AppliedChange]:
        """List a process's applied changes, newest first."""
        return await service.list_changes(process_id)

    @router.post(
        "/changes/{change_id}/rollback",
        response_model=AppliedChange,
        dependencies=[approver],
    )
    async def rollback_change(change_id: str) -> AppliedChange:
        """Revert an applied change to its prior version."""
        change = await service.rollback_change(change_id)
        if change is None:
            raise HTTPException(status_code=404, detail="change not reversible")
        return change

    @router.post(
        "/processes/{process_id}/rollback/{version}",
        response_model=ProcessGraph,
        dependencies=[approver],
    )
    async def rollback_to_version(process_id: str, version: int) -> ProcessGraph:
        """Manually restore a named prior version as the live process."""
        restored = await service.rollback_to_version(process_id, version)
        if restored is None:
            raise HTTPException(status_code=404, detail="version not found")
        return restored

    return router


__all__ = ["build_ops_router"]
