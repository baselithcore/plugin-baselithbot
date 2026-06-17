"""Note CRUD endpoints.

The vault is the source of truth; every write triggers an incremental rebuild
of the derived index so links/backlinks/search stay consistent. Rebuild is
cheap for typical personal vaults (pure-Python, in-memory).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..index_state import get_index
from ..models import (
    Note,
    NoteAssign,
    NoteCreate,
    NoteMeta,
    NoteMove,
    NoteUpdate,
    TreeNode,
)
from ..tree import build_tree

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("", response_model=list[NoteMeta])
async def list_notes(
    workspace: str | None = Query(None, description="narrow to one workspace"),
) -> list[NoteMeta]:
    return get_index().notes.list_meta(workspace=workspace)


# Static path declared before ``/{note_id}`` so it is not shadowed.
@router.get("/tree", response_model=list[TreeNode])
async def note_tree(
    workspace: str | None = Query(None, description="narrow to one workspace"),
) -> list[TreeNode]:
    return build_tree(get_index().notes.list_meta(workspace=workspace))


@router.post("", response_model=Note, status_code=201)
async def create_note(payload: NoteCreate) -> Note:
    idx = get_index()
    note = idx.notes.create(payload)
    await idx.rebuild()
    return idx.hydrate(note.id)


@router.get("/{note_id}", response_model=Note)
async def get_note(note_id: str) -> Note:
    idx = get_index()
    if not idx.notes.exists(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    return idx.hydrate(note_id)


@router.put("/{note_id}", response_model=Note)
async def update_note(note_id: str, patch: NoteUpdate) -> Note:
    idx = get_index()
    if not idx.notes.exists(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    idx.notes.update(note_id, patch)
    await idx.rebuild()
    return idx.hydrate(note_id)


@router.post("/{note_id}/move", response_model=Note)
async def move_note(note_id: str, payload: NoteMove) -> Note:
    idx = get_index()
    if not idx.notes.exists(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    idx.notes.move(note_id, payload)
    await idx.rebuild()
    return idx.hydrate(note_id)


@router.post("/{note_id}/workspace", response_model=Note)
async def assign_workspace(note_id: str, payload: NoteAssign) -> Note:
    """Re-home a note (and its subtree) into another workspace."""
    idx = get_index()
    if not idx.notes.exists(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    if not idx.workspaces.exists(payload.workspace):
        raise HTTPException(status_code=404, detail="workspace not found")
    idx.notes.set_workspace(note_id, payload.workspace)
    await idx.rebuild()
    return idx.hydrate(note_id)


@router.delete("/{note_id}")
async def delete_note(note_id: str) -> dict[str, bool]:
    idx = get_index()
    if not idx.notes.delete(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    await idx.rebuild()
    return {"deleted": True}
