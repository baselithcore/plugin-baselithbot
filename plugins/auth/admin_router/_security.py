"""Admin endpoints for the org-wide security policy (MFA enforcement).

Per-user and per-group MFA requirements are managed through the existing user
(``PATCH /admin/users/{id}``) and group endpoints; this module owns the single
org-wide "require MFA for everyone" toggle.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.admin_router._helpers import get_client_ip
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_persistence_dep,
    require_admin,
)
from plugins.auth.persistence import AuthPersistence

logger = get_logger(__name__)

router = APIRouter(prefix="/security", tags=["Admin"])


class MfaPolicyResponse(BaseModel):
    """Org-wide MFA enforcement state."""

    mfa_required_all: bool


class MfaPolicyUpdate(BaseModel):
    """Toggle the org-wide MFA requirement."""

    mfa_required_all: bool


@router.get("/mfa-policy", response_model=MfaPolicyResponse)
async def get_mfa_policy(
    _: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> MfaPolicyResponse:
    """Read the org-wide MFA requirement."""
    return MfaPolicyResponse(mfa_required_all=persistence.get_mfa_required_all())


@router.put("/mfa-policy", response_model=MfaPolicyResponse)
async def set_mfa_policy(
    body: MfaPolicyUpdate,
    request: Request,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> MfaPolicyResponse:
    """Enable/disable mandatory MFA for every user (takes effect at next login)."""
    persistence.set_mfa_required_all(body.mfa_required_all)
    audit.log(
        action=AuditAction.MFA_POLICY_CHANGED,
        actor_id=admin.user_id,
        target_id="security.mfa_required_all",
        details={"mfa_required_all": body.mfa_required_all},
        ip_address=get_client_ip(request),
    )
    logger.info(
        "Admin %s set org-wide mfa_required_all=%s",
        admin.user_id,
        body.mfa_required_all,
    )
    return MfaPolicyResponse(mfa_required_all=body.mfa_required_all)


__all__ = ["router"]
