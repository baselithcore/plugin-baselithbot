"""Health + reindex endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from ..index_state import get_index

router = APIRouter(tags=["system"])


@router.get("/healthz")
async def healthz() -> dict[str, object]:
    idx = get_index()
    return {"status": "ok" if idx.ready else "warming", "ready": idx.ready}


@router.post("/api/reindex")
async def reindex() -> dict[str, object]:
    """Force a full rebuild of the derived index from the vault."""
    idx = get_index()
    await idx.rebuild()
    return {"ready": idx.ready, "notes": len(idx.notes.vault.list_ids())}
