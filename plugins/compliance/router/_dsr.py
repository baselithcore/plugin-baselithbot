"""GDPR data-subject-request routes (consume ``core.privacy``).

Exposes the data-subject framework: list registered providers, export a
subject's data (right to access), erase a subject (right to erasure), and run a
retention sweep. Every operation handles personal data, so all of them require
effective-admin (a DPO/compliance role provisioned with the wildcard). Console
over :func:`core.privacy.get_data_subject_service`.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.auth.types import AuthUser
from core.privacy import get_data_subject_service

from ._guards import admin_principal

router = APIRouter(prefix="/dsr", tags=["compliance:dsr"])


class SubjectRef(BaseModel):
    """A single data-subject identifier."""

    subject_id: str = Field(..., min_length=1)


class RetentionSweepRequest(BaseModel):
    """Parameters for a retention sweep."""

    older_than_days: int = Field(..., ge=0)


@router.get("/providers")
async def list_providers(_: AuthUser = Depends(admin_principal)) -> Dict[str, Any]:
    """List the names of every registered data provider."""
    service = get_data_subject_service()
    return {"providers": [p.name for p in service.registry.all()]}


@router.post("/export")
async def export_subject(
    body: SubjectRef, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Aggregate every provider's data for the subject (right to access)."""
    service = get_data_subject_service()
    bundle = await service.export_subject(body.subject_id)
    return {"subject_id": bundle.subject_id, "data": bundle.data}


@router.post("/erase")
async def erase_subject(
    body: SubjectRef, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Erase the subject from every provider (right to erasure)."""
    service = get_data_subject_service()
    report = await service.erase_subject(body.subject_id)
    return {
        "subject_id": report.subject_id,
        "erased": report.erased,
        "total": report.total,
    }


@router.post("/retention/sweep", status_code=202)
async def retention_sweep(
    body: RetentionSweepRequest, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Purge records older than ``older_than_days`` across providers."""
    service = get_data_subject_service()
    report = await service.purge_expired(body.older_than_days * 86_400)
    return {
        "older_than_seconds": report.older_than_seconds,
        "purged": report.purged,
        "total": report.total,
    }


__all__ = ["router"]
