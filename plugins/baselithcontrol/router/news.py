"""Read-only news route: a merged, cached RSS/Atom feed for the home ticker.

The snapshot is public reference data (no per-tenant scoping) but still sits
behind the dashboard's resilient ``read_guard`` so it inherits the same
authentication posture as the rest of the control plane — it is never an
anonymous open proxy. All heavy lifting (fetch/parse/merge/cache) lives in the
news service; this router is a thin, typed boundary.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..service.deps import get_config
from ..service.news import NewsResponse
from ..service.news.provider import get_news_service
from ._guards import read_guard


def build_news_router() -> APIRouter:
    """Build the news sub-router (authenticated reads, shared snapshot)."""
    router = APIRouter(
        tags=["baselithcontrol:news"], dependencies=[Depends(read_guard)]
    )

    @router.get("/news", response_model=NewsResponse)
    async def news(request: Request) -> NewsResponse:
        """Newest-first, de-duplicated headlines for the dashboard ticker."""
        cfg = get_config(request.app)
        return await get_news_service(cfg).get_news()

    return router


__all__ = ["build_news_router"]
