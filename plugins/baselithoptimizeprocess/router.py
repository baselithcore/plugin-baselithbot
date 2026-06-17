"""FastAPI surface for BaselithOptimizeProcess.

A thin, fully-async adapter over :class:`BopService`. The router owns no business
logic: it validates inbound payloads, delegates, and shapes HTTP responses. The
real-time monitoring endpoint streams Server-Sent Events framed from the
service's metrics broker.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import Response  # module-level so string annotations resolve

from core.observability.logging import get_logger

from .api_models import (
    DecisionRequest,
    HealthResponse,
    ImportProcessRequest,
    IngestMetricsRequest,
    OptimizeRequest,
    RegisterProcessRequest,
)
from .models import (
    Bottleneck,
    KpiSnapshot,
    OptimizationProposal,
    ProcessGraph,
)
from .router_insights import build_insights_router
from .router_ops import build_ops_router
from .router_resources import build_resources_router
from .security import require_approver, require_editor, require_viewer
from .service import BopService, ProcessValidationError
from .tenancy import DEFAULT_TENANT_HEADER, tenant_binder
from .ui_static import mount_dashboard_ui
from .xml_import import ProcessImportError

logger = get_logger(__name__)

__all__ = ["create_router"]


def create_router(plugin_instance: Any) -> Any:
    """Build the plugin's API router bound to its service.

    Args:
        plugin_instance: The owning plugin, exposing ``.service`` and metadata.

    Returns:
        A configured ``APIRouter``.
    """
    from fastapi import APIRouter, Depends, Header, HTTPException, Query
    from fastapi.responses import StreamingResponse

    from .idempotency import IdempotencyCache
    from .ratelimit import RateLimiter
    from .tenancy import current_tenant

    service: BopService = plugin_instance.service
    cfg = getattr(plugin_instance, "_config", {}) or {}
    auth_enabled = bool(cfg.get("auth_enabled", False))
    header = str(cfg.get("tenant_header", DEFAULT_TENANT_HEADER))
    limiter = RateLimiter(int(cfg.get("rate_limit_per_min", 0)))
    idempotency = IdempotencyCache()

    # Tenant binding runs for every route (always on, header- or auth-derived).
    tenant_dep = Depends(tenant_binder(auth_enabled=auth_enabled, header=header))
    # Role gates are no-ops unless auth_enabled (and the auth plugin is loaded).
    viewer = Depends(require_viewer(auth_enabled))
    editor = Depends(require_editor(auth_enabled))
    approver = Depends(require_approver(auth_enabled))

    def _rate_limit() -> None:
        """Throttle when rate limiting is enabled; 429 once the window is full."""
        if not limiter.allow(current_tenant()):
            raise HTTPException(status_code=429, detail="rate limit exceeded")

    router = APIRouter(prefix="", tags=["bop"], dependencies=[tenant_dep])

    # -- Health ------------------------------------------------------------

    @router.get("/health", response_model=HealthResponse, dependencies=[viewer])
    async def health(response: Response) -> HealthResponse:
        """Report liveness and the number of mapped processes."""
        response.headers["X-API-Version"] = plugin_instance.metadata.version
        processes = await service.list_processes()
        return HealthResponse(
            plugin=plugin_instance.metadata.name,
            version=plugin_instance.metadata.version,
            processes=len(processes),
        )

    # -- Process mapping ---------------------------------------------------

    @router.post(
        "/processes",
        response_model=ProcessGraph,
        status_code=201,
        dependencies=[editor],
    )
    async def register_process(body: RegisterProcessRequest) -> ProcessGraph:
        """Register or replace a process from a JSON DAG."""
        try:
            return await service.register_process(body)
        except ProcessValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post(
        "/processes/import",
        response_model=ProcessGraph,
        status_code=201,
        dependencies=[editor],
    )
    async def import_process(body: ImportProcessRequest) -> ProcessGraph:
        """Register a process imported from a BPMN/XML document."""
        try:
            return await service.import_process_xml(body.id, body.xml, body.kpis)
        except (ProcessImportError, ProcessValidationError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/processes", response_model=list[ProcessGraph], dependencies=[viewer])
    async def list_processes(
        response: Response,
        limit: int | None = Query(default=None, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> list[ProcessGraph]:
        """List mapped processes (paginated; total in ``X-Total-Count``)."""
        return _page(await service.list_processes(), limit, offset, response)

    @router.get(
        "/processes/{process_id}",
        response_model=ProcessGraph,
        dependencies=[viewer],
    )
    async def get_process(process_id: str) -> ProcessGraph:
        """Fetch a single process by id."""
        process = await service.get_process(process_id)
        if process is None:
            raise HTTPException(status_code=404, detail="process not found")
        return process

    @router.delete("/processes/{process_id}", dependencies=[editor])
    async def delete_process(process_id: str) -> dict[str, str]:
        """Delete a process and its derived state."""
        if not await service.delete_process(process_id):
            raise HTTPException(status_code=404, detail="process not found")
        return {"deleted": process_id}

    # -- Monitoring --------------------------------------------------------

    @router.post("/processes/{process_id}/metrics", dependencies=[editor])
    async def ingest_metrics(
        process_id: str,
        body: IngestMetricsRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, int]:
        """Ingest a batch of KPI samples (rate-limited; idempotent on retry)."""
        tenant = current_tenant()
        if idempotency_key is not None:
            cached = idempotency.get(tenant, idempotency_key)
            if cached is not None:
                return cached  # replayed retry — no rate budget consumed
        _rate_limit()
        if await service.get_process(process_id) is None:
            raise HTTPException(status_code=404, detail="process not found")
        accepted = await service.ingest_metrics(
            [s for s in body.samples if s.process_id == process_id]
        )
        result = {"accepted": accepted}
        if idempotency_key is not None:
            idempotency.put(tenant, idempotency_key, result)
        return result

    @router.get(
        "/processes/{process_id}/snapshots",
        response_model=list[KpiSnapshot],
        dependencies=[viewer],
    )
    async def snapshots(process_id: str) -> list[KpiSnapshot]:
        """Return the current KPI snapshots for a process."""
        return await service.snapshots(process_id)

    @router.get(
        "/processes/{process_id}/bottlenecks",
        response_model=list[Bottleneck],
        dependencies=[viewer],
    )
    async def bottlenecks(process_id: str) -> list[Bottleneck]:
        """Return the latest detected bottlenecks for a process."""
        return await service.list_bottlenecks(process_id)

    @router.get("/processes/{process_id}/stream", dependencies=[viewer])
    async def stream(process_id: str) -> StreamingResponse:
        """Stream live metric/bottleneck updates as Server-Sent Events."""
        if await service.get_process(process_id) is None:
            raise HTTPException(status_code=404, detail="process not found")
        return StreamingResponse(
            _sse(service.stream(process_id)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # -- Optimization (human-in-the-loop) ----------------------------------

    @router.post(
        "/processes/{process_id}/optimize",
        response_model=list[OptimizationProposal],
        dependencies=[editor],
    )
    async def optimize(
        process_id: str, body: OptimizeRequest
    ) -> list[OptimizationProposal]:
        """Run an advisory optimization pass and return proposals."""
        _rate_limit()
        proposals = await service.optimize(process_id, body.context, body.max_proposals)
        if proposals is None:
            raise HTTPException(status_code=404, detail="process not found")
        return proposals

    @router.get(
        "/proposals",
        response_model=list[OptimizationProposal],
        dependencies=[viewer],
    )
    async def list_proposals(
        response: Response,
        process_id: str | None = Query(default=None),
        limit: int | None = Query(default=None, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> list[OptimizationProposal]:
        """List proposals (paginated; total in ``X-Total-Count``)."""
        proposals = await service.list_proposals(process_id)
        return _page(proposals, limit, offset, response)

    @router.post(
        "/proposals/{proposal_id}/approve",
        response_model=OptimizationProposal,
        dependencies=[approver],
    )
    async def approve(proposal_id: str, body: DecisionRequest) -> OptimizationProposal:
        """Approve a proposal (human-in-the-loop)."""
        return await _decide(service, proposal_id, approve=True)

    @router.post(
        "/proposals/{proposal_id}/reject",
        response_model=OptimizationProposal,
        dependencies=[approver],
    )
    async def reject(proposal_id: str, body: DecisionRequest) -> OptimizationProposal:
        """Reject a proposal (human-in-the-loop)."""
        return await _decide(service, proposal_id, approve=False)

    router.include_router(
        build_ops_router(service, viewer, editor, approver),
        dependencies=[tenant_dep],
    )
    router.include_router(
        build_insights_router(service, viewer, editor, approver),
        dependencies=[tenant_dep],
    )
    router.include_router(
        build_resources_router(service, viewer, editor, approver),
        dependencies=[tenant_dep],
    )
    mount_dashboard_ui(router)
    return router


def _page(items: list[Any], limit: int | None, offset: int, response: Any) -> list[Any]:
    """Slice a list for pagination and expose the full count via a header."""
    response.headers["X-Total-Count"] = str(len(items))
    window = items[offset:] if offset else items
    return window[:limit] if limit is not None else window


async def _decide(
    service: BopService, proposal_id: str, approve: bool
) -> OptimizationProposal:
    """Apply a decision, translating an unknown id into a 404."""
    from fastapi import HTTPException

    decided = await service.decide_proposal(proposal_id, approve)
    if decided is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    return decided


async def _sse(
    events: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[str]:
    """Frame broker events as Server-Sent Events ``data:`` lines."""
    async for event in events:
        yield f"data: {json.dumps(event)}\n\n"


__all__ = ["create_router"]
