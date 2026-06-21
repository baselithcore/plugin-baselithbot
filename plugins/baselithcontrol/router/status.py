"""Read-only status routes: aggregated health, head-band overview, widgets."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth.types import AuthUser

from ..api_models import OverviewView, PluginStatus, StatusView, WidgetSpec
from ..service import get_aggregator
from ..service.probe import StatusProber
from ..service.widgets import resolve_widgets
from ._guards import current_principal, is_admin, read_guard


def _system_metrics() -> dict:
    """Pull the framework's aggregated plugin metrics (best-effort)."""
    try:
        from core.plugins.metrics import get_metrics_collector

        return dict(get_metrics_collector().get_system_metrics())
    except Exception:  # noqa: BLE001 — metrics are optional, never block status
        return {}


def build_status_router() -> APIRouter:
    """Build the status sub-router (read-only)."""
    router = APIRouter(
        tags=["baselithcontrol:status"], dependencies=[Depends(read_guard)]
    )

    @router.get("/status", response_model=StatusView)
    async def status(request: Request) -> StatusView:
        """Aggregated health and system metrics overview."""
        return get_aggregator(request.app).status(_system_metrics())

    @router.get("/overview", response_model=OverviewView)
    async def overview(
        request: Request, user: AuthUser = Depends(current_principal)
    ) -> OverviewView:
        """Framework-wide head-band summary (counts + tones), scoped to caller."""
        return get_aggregator(request.app).overview(include_disabled=is_admin(user))

    @router.get("/status/{plugin}", response_model=PluginStatus)
    async def plugin_status(plugin: str, request: Request) -> PluginStatus:
        """Per-plugin normalized status envelope (the status adapter output)."""
        registry = getattr(request.app.state, "plugin_registry", None)
        if registry is None or plugin not in registry:
            raise HTTPException(status_code=404, detail="not_found")
        return StatusProber(registry).probe(plugin)

    @router.get("/widgets", response_model=list[WidgetSpec])
    async def widgets(
        request: Request, user: AuthUser = Depends(current_principal)
    ) -> list[WidgetSpec]:
        """Declarative status widgets a plugin opts into via its manifest."""
        inv = get_aggregator(request.app).inventory(include_disabled=is_admin(user))
        return resolve_widgets([c.name for c in inv.plugins])

    return router


__all__ = ["build_status_router"]
