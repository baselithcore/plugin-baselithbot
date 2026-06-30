"""Daily-note endpoint — open (or create) a dated journal entry."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..dailynotes import ensure_daily
from ..index_state import get_index
from ..models import DailyRequest, Note

router = APIRouter(prefix="/api/daily", tags=["daily"])


@router.post("", response_model=Note)
async def open_daily(payload: DailyRequest) -> Note:
    """Idempotently get-or-create the daily note for a date (today if null)."""
    idx = get_index()
    try:
        note, created = ensure_daily(
            idx.notes, idx.templates, payload.date, payload.template
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if created:
        await idx.rebuild()
    return idx.hydrate(note.id)
