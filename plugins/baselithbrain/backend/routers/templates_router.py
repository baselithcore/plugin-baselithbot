"""Note-template CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..index_state import get_index
from ..models import Template, TemplateCreate, TemplateMeta

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateMeta])
async def list_templates() -> list[TemplateMeta]:
    return get_index().templates.list()


@router.post("", response_model=Template, status_code=201)
async def create_template(payload: TemplateCreate) -> Template:
    return get_index().templates.create(payload)


@router.get("/{template_id}", response_model=Template)
async def get_template(template_id: str) -> Template:
    tpl = get_index().templates.get(template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="template not found")
    return tpl


@router.delete("/{template_id}")
async def delete_template(template_id: str) -> dict[str, bool]:
    if not get_index().templates.delete(template_id):
        raise HTTPException(status_code=404, detail="template not found")
    return {"deleted": True}
