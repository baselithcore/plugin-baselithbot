"""Tag browser endpoint — the vault's tags with usage counts."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..index_state import get_index
from ..models import TagInfo
from ..tags import collect_tags

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagInfo])
async def list_tags(
    workspace: str | None = Query(None, description="narrow to one workspace"),
) -> list[TagInfo]:
    return collect_tags(get_index().notes.list_meta(workspace=workspace))
