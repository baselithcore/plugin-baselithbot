"""FastAPI surface for the BaselithControl plugin.

Sub-routers are assembled into a single ``APIRouter`` that the plugin mounts at
``/api/baselithcontrol``. Each sub-router owns one responsibility seam:

* :mod:`inventory` — read-only catalog + embeddable UI surfaces.
* :mod:`status`    — read-only health + system metrics.
* :mod:`resources` — read-only resource gauges + per-plugin request load.
* :mod:`timeline`  — retained request-volume trend + lifecycle activity feed.
* :mod:`stream`    — SSE live deltas.
* :mod:`actions`   — gated lifecycle mutations (admin only).
* :mod:`news`      — read-only public RSS/Atom ticker snapshot.
"""

from __future__ import annotations

from fastapi import APIRouter

from .actions import build_actions_router
from .cli import build_cli_router
from .inventory import build_inventory_router
from .news import build_news_router
from .resources import build_resources_router
from .status import build_status_router
from .stream import build_stream_router
from .timeline import build_timeline_router


def build_control_router() -> APIRouter:
    """Compose all control-plane sub-routers into one router."""
    router = APIRouter()
    router.include_router(build_inventory_router())
    router.include_router(build_status_router())
    router.include_router(build_resources_router())
    router.include_router(build_timeline_router())
    router.include_router(build_stream_router())
    router.include_router(build_actions_router())
    router.include_router(build_cli_router())
    router.include_router(build_news_router())
    return router


__all__ = ["build_control_router"]
