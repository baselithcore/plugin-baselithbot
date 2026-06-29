"""Compliance console API — aggregates the per-regulation sub-routers.

Each domain wraps a framework primitive: NIS2/DORA incidents
(``core.incidents``), GDPR DSR (``core.privacy``), the DORA Register of
Information (``core.thirdparty``), and AI-Act transparency
(``core.transparency``). Mounted under ``/api/compliance``.
"""

from __future__ import annotations

from fastapi import APIRouter

from ._dora import router as dora_router
from ._dsr import router as dsr_router
from ._incidents import router as incidents_router
from ._meta import router as meta_router
from ._overview import router as overview_router
from ._thirdparty import router as thirdparty_router
from ._transparency import router as transparency_router


def build_compliance_router() -> APIRouter:
    """Assemble the full compliance API from its per-domain sub-routers."""
    router = APIRouter()
    router.include_router(meta_router)
    router.include_router(overview_router)
    router.include_router(incidents_router)
    router.include_router(dora_router)
    router.include_router(dsr_router)
    router.include_router(thirdparty_router)
    router.include_router(transparency_router)
    return router


__all__ = ["build_compliance_router"]
