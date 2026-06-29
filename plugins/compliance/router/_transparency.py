"""EU AI Act Art. 50 transparency routes (consume ``core.transparency``).

Read-only disclosure status/notice for any authenticated reader; producing a
provenance tag (content marking, Art. 50(2)/(4)) requires effective-admin.
Console over :func:`core.transparency.get_transparency_service`.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.auth.types import AuthUser
from core.transparency import ContentClass, Modality, get_transparency_service

from ._guards import admin_principal, read_guard

router = APIRouter(prefix="/transparency", tags=["compliance:transparency"])


class MarkRequest(BaseModel):
    """Produce a provenance tag for a piece of AI-generated content."""

    content: str = Field(..., min_length=1)
    content_class: ContentClass = ContentClass.AI_GENERATED
    modality: Modality = Modality.TEXT
    model: Optional[str] = None


@router.get("/status", dependencies=[Depends(read_guard)])
async def transparency_status() -> Dict[str, Any]:
    """Report whether disclosure is enabled and the notice that would be shown."""
    service = get_transparency_service()
    enabled = service.enabled
    notice = service.disclosure_notice().to_dict() if enabled else None
    return {
        "enabled": enabled,
        "should_disclose": service.should_disclose(),
        "notice": notice,
    }


@router.post("/mark", status_code=201)
async def mark_content(
    body: MarkRequest, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Produce a (optionally signed) provenance tag for AI output, C2PA-aligned."""
    service = get_transparency_service()
    tag = service.mark_content(
        body.content,
        content_class=body.content_class,
        modality=body.modality,
        model=body.model,
    )
    header_name, header_value = service.provenance_header(tag)
    return {"tag": tag.to_dict(), "header": {header_name: header_value}}


__all__ = ["router"]
