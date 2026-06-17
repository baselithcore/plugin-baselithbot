"""
Privacy / DSR management router (scope-gated).

Exposes the :mod:`core.privacy` data-subject-request framework over HTTP:
list registered providers, export a subject's data (right to access),
erase a subject (right to erasure), and trigger a retention sweep. Every
route requires the ``privacy:manage`` capability scope — the ``ADMIN`` role
holds the ``*`` wildcard and therefore satisfies it implicitly.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.auth.types import AuthUser, InsufficientScopeError
from core.middleware import require_user
from core.observability.logging import get_logger
from core.privacy import SubjectExport, get_data_subject_service

logger = get_logger(__name__)

router = APIRouter(prefix="/privacy", tags=["privacy"])

_MANAGE_SCOPE = "privacy:manage"


def require_privacy_scope(
    request: Request, _: str = Depends(require_user)
) -> AuthUser:
    """Authenticated identity must hold the ``privacy:manage`` capability."""
    user = getattr(request.state, "user", None)
    if not isinstance(user, AuthUser) or not user.has_scope(_MANAGE_SCOPE):
        raise InsufficientScopeError(
            f"Scope '{_MANAGE_SCOPE}' is required to manage privacy requests."
        )
    return user


class SubjectRef(BaseModel):
    """A single data-subject identifier."""

    subject_id: str = Field(..., min_length=1)


class RetentionSweepRequest(BaseModel):
    """Parameters for a retention sweep."""

    older_than_days: int = Field(..., ge=0)


@router.get("/providers")
async def list_providers(_: AuthUser = Depends(require_privacy_scope)) -> dict:
    """List the names of every registered data provider."""
    service = get_data_subject_service()
    return {"providers": [p.name for p in service.registry.all()]}


@router.post("/export")
async def export_subject(
    body: SubjectRef, _: AuthUser = Depends(require_privacy_scope)
) -> SubjectExport:
    """Aggregate every provider's data for the subject (right to access)."""
    service = get_data_subject_service()
    return await service.export_subject(body.subject_id)


@router.post("/erase")
async def erase_subject(
    body: SubjectRef, _: AuthUser = Depends(require_privacy_scope)
) -> dict:
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
    body: RetentionSweepRequest, _: AuthUser = Depends(require_privacy_scope)
) -> JSONResponse:
    """Purge records older than ``older_than_days`` across providers."""
    service = get_data_subject_service()
    report = await service.purge_expired(body.older_than_days * 86_400)
    return JSONResponse(
        status_code=202,
        content={
            "older_than_seconds": report.older_than_seconds,
            "purged": report.purged,
            "total": report.total,
        },
    )
