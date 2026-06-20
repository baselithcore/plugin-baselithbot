"""Read-only retained-telemetry routes: request-volume trend + lifecycle feed.

* ``/resources/history`` — the server-retained aggregate request-rate series
  (survives reloads, spans the full window). Polling it also keeps the
  background sampler alive.
* ``/timeline``          — recent plugin-lifecycle events (newest first).

Both are read-only and share the dashboard's resilient ``read_guard``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..api_models import LifecycleEvent, RequestVolumeSample
from ..service.lifecycle import get_lifecycle_buffer
from ..service.volume import get_volume_sampler
from ._guards import read_guard


def build_timeline_router() -> APIRouter:
    """Build the retained-telemetry sub-router (read-only)."""
    router = APIRouter(
        tags=["baselithcontrol:timeline"], dependencies=[Depends(read_guard)]
    )

    @router.get("/resources/history", response_model=list[RequestVolumeSample])
    async def request_volume() -> list[RequestVolumeSample]:
        """Retained aggregate request-rate series (oldest→newest)."""
        sampler = get_volume_sampler()
        sampler.ensure_started()  # idempotent; starts the loop on first poll
        return [RequestVolumeSample.model_validate(s) for s in sampler.history()]

    @router.get("/timeline", response_model=list[LifecycleEvent])
    async def lifecycle_timeline(
        limit: int = Query(default=50, ge=1, le=200),
    ) -> list[LifecycleEvent]:
        """Recent plugin-lifecycle events, newest first."""
        rows = get_lifecycle_buffer().tail(limit)
        return [LifecycleEvent.model_validate(r) for r in rows]

    return router


__all__ = ["build_timeline_router"]
