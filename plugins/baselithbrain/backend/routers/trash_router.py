"""Trash endpoints — list, restore and purge soft-deleted notes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..index_state import get_index
from ..models import Note, NoteMeta

router = APIRouter(prefix="/api/trash", tags=["trash"])


@router.get("", response_model=list[NoteMeta])
async def list_trash() -> list[NoteMeta]:
    return get_index().notes.list_trash()


@router.post("/{note_id}/restore", response_model=Note)
async def restore_note(note_id: str) -> Note:
    idx = get_index()
    if note_id not in idx.notes.vault.list_trashed():
        raise HTTPException(status_code=404, detail="not in trash")
    note = idx.notes.restore(note_id)
    await idx.rebuild()
    return idx.hydrate(note.id)


@router.delete("/{note_id}")
async def purge_note(note_id: str) -> dict[str, bool]:
    if not get_index().notes.vault.purge(note_id):
        raise HTTPException(status_code=404, detail="not in trash")
    return {"purged": True}


@router.delete("")
async def empty_trash() -> dict[str, int]:
    return {"purged": get_index().notes.vault.purge_all()}
