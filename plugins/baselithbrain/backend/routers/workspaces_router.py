"""Workspace endpoints — CRUD over the logical note groupings.

A workspace is a named namespace over the flat vault. Deleting one never loses
notes: its members are re-homed into the default workspace first, then the
registry entry is dropped.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..index_state import get_index
from ..models import Workspace, WorkspaceCreate, WorkspaceInfo, WorkspaceUpdate
from ..workspaces import DEFAULT_WORKSPACE_ID

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceInfo])
async def list_workspaces() -> list[WorkspaceInfo]:
    idx = get_index()
    counts = _counts(idx)
    return [
        WorkspaceInfo(**ws.model_dump(), note_count=counts.get(ws.id, 0))
        for ws in idx.workspaces.list()
    ]


@router.post("", response_model=Workspace, status_code=201)
async def create_workspace(payload: WorkspaceCreate) -> Workspace:
    return get_index().workspaces.create(payload)


@router.put("/{ws_id}", response_model=Workspace)
async def update_workspace(ws_id: str, patch: WorkspaceUpdate) -> Workspace:
    ws = get_index().workspaces.update(ws_id, patch)
    if ws is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    return ws


@router.delete("/{ws_id}")
async def delete_workspace(ws_id: str) -> dict[str, object]:
    if ws_id == DEFAULT_WORKSPACE_ID:
        raise HTTPException(status_code=400, detail="cannot delete default workspace")
    idx = get_index()
    if not idx.workspaces.exists(ws_id):
        raise HTTPException(status_code=404, detail="workspace not found")
    moved = idx.notes.reassign_workspace(ws_id, DEFAULT_WORKSPACE_ID)
    idx.workspaces.delete(ws_id)
    await idx.rebuild()
    return {"deleted": True, "reassigned": moved}


def _counts(idx) -> dict[str, int]:
    """Notes per workspace — kept private; counts are derived client-side too."""
    out: dict[str, int] = {}
    for meta in idx.notes.list_meta():
        out[meta.workspace] = out.get(meta.workspace, 0) + 1
    return out
