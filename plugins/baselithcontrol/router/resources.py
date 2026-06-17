"""Read-only resource routes: framework-wide gauges + per-plugin request load.

* ``/resources``          — whole-process + host resource snapshot (psutil).
* ``/resources/plugins``  — per-plugin HTTP request telemetry (the meter).

Both are read-only and share the dashboard's resilient ``read_guard``. The
sampler/meter are process-wide singletons, so these handlers are cheap polls.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..api_models import PluginRuntime, SystemResources
from ..service.plugin_meter import get_plugin_meter
from ..service.resources import get_resource_sampler
from ._guards import read_guard


def build_resources_router() -> APIRouter:
    """Build the resource-telemetry sub-router (read-only)."""
    router = APIRouter(
        tags=["baselithcontrol:resources"], dependencies=[Depends(read_guard)]
    )

    @router.get("/resources", response_model=SystemResources)
    async def resources() -> SystemResources:
        """Framework-wide resource snapshot (CPU, RAM, network, threads, uptime)."""
        return SystemResources.model_validate(get_resource_sampler().sample())

    @router.get("/resources/plugins", response_model=list[PluginRuntime])
    async def plugin_resources() -> list[PluginRuntime]:
        """Per-plugin request telemetry, ordered by busiest (most requests)."""
        snap = get_plugin_meter().snapshot()
        rows = [
            PluginRuntime.model_validate({"plugin": name, **stat})
            for name, stat in snap.items()
        ]
        rows.sort(key=lambda r: r.requests, reverse=True)
        return rows

    return router


__all__ = ["build_resources_router"]
