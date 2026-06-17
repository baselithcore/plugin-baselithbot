"""Graph endpoints — full graph, lazy neighborhoods, MOCs, link suggestions.

The graph is an interaction surface, not a static picture: the SPA fetches a
note's neighborhood on demand (docked local graph), the full graph paginated by
edge kind, MOC cluster suggestions, and per-note unlinked/semantic suggestions.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..index_state import get_index
from ..models import GraphData, LinkSuggestion

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=GraphData)
async def full_graph(
    tags: bool = Query(True, description="include tag nodes/edges"),
    derived: bool = Query(False, description="include semantic edges"),
    workspace: str | None = Query(None, description="narrow to one workspace"),
) -> GraphData:
    idx = get_index()
    return idx.graph.full_graph(
        include_tags=tags, include_derived=derived, scope=idx.note_ids(workspace)
    )


@router.get("/neighborhood/{note_id}", response_model=GraphData)
async def neighborhood(
    note_id: str,
    hops: int = Query(1, ge=1, le=3),
) -> GraphData:
    idx = get_index()
    if not idx.notes.exists(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    return idx.graph.neighborhood(note_id, hops=hops)


@router.get("/mocs")
async def moc_candidates(min_size: int = Query(4, ge=2, le=50)) -> list[dict]:
    return get_index().graph.moc_candidates(min_size=min_size)


@router.get("/suggestions/{note_id}", response_model=list[LinkSuggestion])
async def suggestions(
    note_id: str,
    top_k: int = Query(6, ge=1, le=20),
) -> list[LinkSuggestion]:
    idx = get_index()
    if not idx.notes.exists(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    body = idx.notes.get(note_id).body
    return idx.graph.suggestions(note_id, body, top_k=top_k)
