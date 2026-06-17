"""FastAPI surface for the Agents Platform.

A thin, fully-async adapter over :class:`AgentPlatformService`. The router owns
no business logic: it validates inbound payloads, delegates, and shapes HTTP
status codes. The bundled dashboard is mounted under ``/ui`` via
:func:`mount_dashboard_ui`.
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger

from .api_models import (
    CreateBlueprintRequest,
    HealthResponse,
    RunAgentRequest,
    ScheduleRequest,
)
from .service import AgentPlatformService
from .types import AgentBlueprint, AgentRunResult, DocCitation, ScheduleSpec
from .ui_static import mount_dashboard_ui

logger = get_logger(__name__)

__all__ = ["create_router"]


def create_router(plugin_instance: Any) -> Any:
    """Build the plugin's API router bound to its service.

    Args:
        plugin_instance: The owning plugin, exposing ``.service`` and metadata.

    Returns:
        A configured ``APIRouter``.
    """
    from fastapi import APIRouter, HTTPException, Query

    service: AgentPlatformService = plugin_instance.service
    router = APIRouter(prefix="", tags=["agents-platform"])

    # -- Health ------------------------------------------------------------

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Report liveness and documentation index size."""
        namespaces = await service.doc_namespaces()
        return HealthResponse(
            plugin=plugin_instance.metadata.name,
            version=plugin_instance.metadata.version,
            doc_namespaces=len(namespaces),
        )

    # -- Blueprints --------------------------------------------------------

    @router.post("/blueprints", response_model=AgentBlueprint, status_code=201)
    async def create_blueprint(body: CreateBlueprintRequest) -> AgentBlueprint:
        """Synthesise and register an agent from natural language."""
        return await service.create_blueprint(body.description)

    @router.get("/blueprints", response_model=list[AgentBlueprint])
    async def list_blueprints() -> list[AgentBlueprint]:
        """List all registered blueprints."""
        return await service.list_blueprints()

    @router.get("/blueprints/{blueprint_id}", response_model=AgentBlueprint)
    async def get_blueprint(blueprint_id: str) -> AgentBlueprint:
        """Fetch a single blueprint by id."""
        blueprint = await service.get_blueprint(blueprint_id)
        if blueprint is None:
            raise HTTPException(status_code=404, detail="blueprint not found")
        return blueprint

    @router.delete("/blueprints/{blueprint_id}")
    async def delete_blueprint(blueprint_id: str) -> dict[str, str]:
        """Delete a blueprint by id."""
        if not await service.delete_blueprint(blueprint_id):
            raise HTTPException(status_code=404, detail="blueprint not found")
        return {"deleted": blueprint_id}

    # -- Runs --------------------------------------------------------------

    @router.post("/blueprints/{blueprint_id}/runs", response_model=AgentRunResult)
    async def run_agent(blueprint_id: str, body: RunAgentRequest) -> AgentRunResult:
        """Execute a capability of a registered agent."""
        result = await service.run_agent(
            blueprint_id, body.capability, body.task, body.code
        )
        if result is None:
            raise HTTPException(status_code=404, detail="blueprint not found")
        return result

    @router.get("/runs", response_model=list[AgentRunResult])
    async def list_runs(
        blueprint_id: str | None = Query(default=None),
    ) -> list[AgentRunResult]:
        """List recent runs, optionally filtered by blueprint."""
        return await service.list_runs(blueprint_id)

    # -- Schedules ---------------------------------------------------------

    @router.post("/blueprints/{blueprint_id}/schedules", response_model=ScheduleSpec)
    async def create_schedule(blueprint_id: str, body: ScheduleRequest) -> ScheduleSpec:
        """Register a recurring run for an agent."""
        spec = await service.create_schedule(
            blueprint_id, body.capability, body.task, body.interval_seconds
        )
        if spec is None:
            raise HTTPException(status_code=404, detail="blueprint not found")
        return spec

    @router.get("/schedules", response_model=list[ScheduleSpec])
    async def list_schedules() -> list[ScheduleSpec]:
        """List all recurring schedules."""
        return service.list_schedules()

    @router.delete("/schedules/{schedule_id}")
    async def delete_schedule(schedule_id: str) -> dict[str, str]:
        """Cancel a schedule."""
        if not service.delete_schedule(schedule_id):
            raise HTTPException(status_code=404, detail="schedule not found")
        return {"deleted": schedule_id}

    @router.get("/tools", response_model=list[str])
    async def tools() -> list[str]:
        """List the built-in runtime tools available to operate agents."""
        return service.describe_tools()

    # -- Documentation (MCP-grounded) -------------------------------------

    @router.get("/docs/search", response_model=list[DocCitation])
    async def search_docs(
        q: str = Query(..., min_length=1),
        prefix: str = Query(default=""),
        top_k: int = Query(default=4, ge=1, le=20),
    ) -> list[DocCitation]:
        """Keyword-search the framework documentation index."""
        namespaces = [prefix] if prefix else None
        return await service.search_docs(q, namespaces, top_k)

    @router.get("/docs/namespaces", response_model=list[str])
    async def doc_namespaces() -> list[str]:
        """List indexed documentation namespaces."""
        return await service.doc_namespaces()

    @router.get("/docs/content")
    async def doc_content(
        namespace: str = Query(..., min_length=1),
    ) -> dict[str, str]:
        """Return the full text of a single indexed document."""
        text = await service.get_doc(namespace)
        if text is None:
            raise HTTPException(status_code=404, detail="document not found")
        return {"namespace": namespace, "content": text}

    # -- Models ------------------------------------------------------------

    @router.get("/models")
    async def models() -> list[dict[str, Any]]:
        """Return the provider/model catalogue."""
        return service.describe_models()

    mount_dashboard_ui(router)
    return router
