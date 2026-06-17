"""Server-Sent Events route: live lifecycle/health deltas for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..service import control_sse
from ..service.deps import get_config
from ._guards import read_guard


def build_stream_router() -> APIRouter:
    """Build the SSE sub-router (authenticated; EventSource carries the session cookie)."""
    router = APIRouter(
        tags=["baselithcontrol:stream"], dependencies=[Depends(read_guard)]
    )

    @router.get("/stream")
    async def stream(request: Request) -> StreamingResponse:
        """Stream control-plane events as Server-Sent Events."""
        heartbeat = get_config(request.app).sse_heartbeat_seconds
        return StreamingResponse(
            control_sse(heartbeat_seconds=heartbeat),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router


__all__ = ["build_stream_router"]
