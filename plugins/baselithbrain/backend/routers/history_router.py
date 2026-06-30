"""Note version-history endpoints — list, view and restore past revisions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import frontmatter
from ..index_state import get_index
from ..models import HistoryEntry, Note, NoteUpdate

router = APIRouter(prefix="/api/notes", tags=["history"])


@router.get("/{note_id}/history", response_model=list[HistoryEntry])
async def list_history(note_id: str) -> list[HistoryEntry]:
    idx = get_index()
    if not idx.notes.exists(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    return idx.history.list(note_id)


@router.get("/{note_id}/history/{version}")
async def get_revision(note_id: str, version: str) -> dict[str, str]:
    """Return the raw text + parsed body of one revision (read-only preview)."""
    try:
        raw = get_index().history.get(note_id, version)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="revision not found") from exc
    _, body = frontmatter.parse(raw)
    return {"version": version, "raw": raw, "body": body}


@router.post("/{note_id}/history/{version}/restore", response_model=Note)
async def restore_revision(note_id: str, version: str) -> Note:
    """Roll the note back to ``version`` (snapshotting the current text first)."""
    idx = get_index()
    if not idx.notes.exists(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    try:
        raw = idx.history.get(note_id, version)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="revision not found") from exc
    idx.snapshot(note_id)  # current text stays recoverable after the rollback
    meta, body = frontmatter.parse(raw)
    idx.notes.update(
        note_id,
        NoteUpdate(
            title=str(meta.get("title")) if meta.get("title") else None,
            body=body,
            tags=list(meta.get("tags") or []),
        ),
    )
    await idx.rebuild()
    return idx.hydrate(note_id)
