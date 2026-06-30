"""Backlinks-with-context endpoint — inbound links plus their surrounding line."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..backlinks import backlinks_with_context
from ..index_state import get_index
from ..models import BacklinkContext

router = APIRouter(prefix="/api/notes", tags=["backlinks"])


@router.get("/{note_id}/backlinks", response_model=list[BacklinkContext])
async def note_backlinks(note_id: str) -> list[BacklinkContext]:
    idx = get_index()
    if not idx.notes.exists(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    return backlinks_with_context(idx, note_id)
