"""Read surface: status, belief state, strategy projections, and the SSE stream.

Every endpoint is viewer-guarded (a no-op unless ``auth_enabled``), tenant- and
session-scoped through :class:`~._deps.Ctx`, and localizes its 404 text from the
request ``Accept-Language``. Recommendation history is served from the durable
store with ``limit``/``offset`` paging and an ``X-Total-Count`` header.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import StreamingResponse

from ._deps import Ctx, RouterContext, use_ctx


def register_read(router: APIRouter, rc: RouterContext) -> None:
    """Attach the read endpoints to ``router``."""
    viewer = Depends(rc.viewer())
    version = rc.plugin.metadata.version

    @router.get("/status", dependencies=[viewer])
    async def status(ctx: Ctx = use_ctx(rc)) -> dict[str, Any]:
        """Aggregate health snapshot of the resolved session's engine."""
        service = rc.plugin.manager.get_service(ctx.tenant, ctx.session_id)
        if service is None:
            return {
                "version": version,
                "running": False,
                "cars_tracked": 0,
                "frames_ingested": 0,
                "recommendations_emitted": 0,
                "queue_depth": 0,
                "swarm_agents": 0,
                "llm_enabled": rc.plugin.config.use_llm,
                "semantic_enabled": rc.plugin.config.semantic_enabled,
            }
        return service.status(version).model_dump(mode="json")

    @router.get("/cars", dependencies=[viewer])
    async def cars(ctx: Ctx = use_ctx(rc)) -> list[str]:
        """List the car ids currently tracked in the session."""
        return rc.live_service(ctx).list_cars()

    @router.get("/stint/{car_id}", dependencies=[viewer])
    async def stint(
        car_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Current derived belief state for a single car."""
        state = rc.live_service(ctx).get_stint(car_id)
        if state is None:
            raise rc.error(404, "error.unknown_car", accept_language)
        return state.model_dump(mode="json")

    @router.get("/recommendations", dependencies=[viewer])
    async def recommendations(
        response: Response,
        car_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        ctx: Ctx = use_ctx(rc),
    ) -> list[dict[str, Any]]:
        """Durable recommendation history (paged, newest first)."""
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        items, total = await rc.plugin.store.list_recommendations(
            ctx.tenant, ctx.session_id, car_id=car_id, limit=limit, offset=offset
        )
        response.headers["X-Total-Count"] = str(total)
        return [r.model_dump(mode="json") for r in items]

    @router.get("/battle/{car_id}", dependencies=[viewer])
    async def battle(
        car_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Battle forecast vs the closest rival."""
        forecast = rc.live_service(ctx).battle_forecast(car_id)
        if forecast is None:
            raise rc.error(404, "error.unknown_car", accept_language)
        return forecast.model_dump(mode="json")

    @router.get("/outcome/{car_id}", dependencies=[viewer])
    async def outcome(
        car_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Monte-Carlo outcome distribution for a car's live strategy."""
        dist = rc.live_service(ctx).outcome(car_id)
        if dist is None:
            raise rc.error(404, "error.unknown_car", accept_language)
        return dist.model_dump(mode="json")

    @router.get("/indicators/{car_id}", dependencies=[viewer])
    async def indicators(
        car_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """Fused, cross-source indicator set with provenance."""
        indicator_set = rc.live_service(ctx).indicators(car_id)
        if indicator_set is None:
            raise rc.error(404, "error.unknown_car", accept_language)
        return indicator_set.model_dump(mode="json")

    @router.get("/intel/{car_id}", dependencies=[viewer])
    async def intel(
        car_id: str,
        ctx: Ctx = use_ctx(rc),
        accept_language: str | None = Header(default=None),
    ) -> dict[str, Any]:
        """AI-synthesised intelligence brief over the fused indicators."""
        brief = await rc.live_service(ctx).intelligence(car_id)
        if brief is None:
            raise rc.error(404, "error.unknown_car", accept_language)
        return {"car_id": car_id, "brief": brief}

    @router.get("/snapshots/{car_id}", dependencies=[viewer])
    async def snapshots(
        car_id: str, limit: int = 200, ctx: Ctx = use_ctx(rc)
    ) -> list[dict[str, Any]]:
        """Persisted per-lap stint snapshots for post-race debrief."""
        limit = max(1, min(limit, 1000))
        snaps = await rc.plugin.store.list_stint_snapshots(
            ctx.tenant, ctx.session_id, car_id, limit=limit
        )
        return [s.model_dump(mode="json") for s in snaps]

    @router.get("/stream", dependencies=[viewer])
    async def stream(request: Request, ctx: Ctx = use_ctx(rc)) -> StreamingResponse:
        """SSE stream of recommendations as they are confirmed."""
        service = rc.live_service(ctx)
        queue = service.subscribe()
        heartbeat = rc.plugin.config.sse_heartbeat_seconds

        async def _events():
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        rec = await asyncio.wait_for(queue.get(), timeout=heartbeat)
                        payload = json.dumps(rec.model_dump(mode="json"))
                        yield f"event: recommendation\ndata: {payload}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            finally:
                service.unsubscribe(queue)

        return StreamingResponse(_events(), media_type="text/event-stream")


__all__ = ["register_read"]
