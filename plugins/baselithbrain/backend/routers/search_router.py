"""Search endpoints — keyword (BM25) and, when enabled, hybrid semantic."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..index_state import get_index
from ..models import SearchHit

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[SearchHit])
async def search(
    q: str = Query("", description="query string"),
    top_k: int = Query(20, ge=1, le=100),
    workspace: str | None = Query(None, description="narrow to one workspace"),
) -> list[SearchHit]:
    idx = get_index()
    return await idx.search.search(q, top_k=top_k, scope=idx.note_ids(workspace))
