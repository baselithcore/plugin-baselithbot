"""Export endpoints — download a note as Markdown or the vault as a zip."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response

from ..export_service import export_note, export_vault
from ..index_state import get_index

router = APIRouter(tags=["export"])


def _attachment(filename: str) -> dict[str, str]:
    return {"Content-Disposition": f'attachment; filename="{filename}"'}


@router.get("/api/notes/{note_id}/export")
async def export_one(note_id: str) -> Response:
    idx = get_index()
    if not idx.notes.exists(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    name, raw = export_note(idx, note_id)
    return Response(content=raw, media_type="text/markdown", headers=_attachment(name))


@router.get("/api/export")
async def export_all(
    workspace: str | None = Query(None, description="narrow to one workspace"),
) -> Response:
    name, data = export_vault(get_index(), workspace=workspace)
    return Response(content=data, media_type="application/zip", headers=_attachment(name))
