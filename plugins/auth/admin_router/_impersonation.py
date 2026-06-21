"""Admin endpoint to start impersonating a user ("log in as user").

Mounted under ``/api/auth/admin``. Issues a short-lived impersonation access
token (target ``sub`` + signed ``act`` actor claim) without touching the
admin's own refresh session — see :mod:`plugins.auth.impersonation` for the
delegation model. The matching "stop" endpoint lives in
:mod:`plugins.auth.router._impersonation_routes`.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.auth import AuthManager, AuthUser
from core.observability.logging import get_logger
from plugins.auth.admin_router._helpers import get_client_ip
from plugins.auth.audit import AuditAction
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_config_dep,
    get_auth_manager_dep,
    get_auth_persistence_dep,
    require_admin,
)
from plugins.auth.impersonation import (
    assert_target_impersonatable,
    build_actor_claim,
    issue_impersonation_token,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.tenancy import resolve_user_tenant
from plugins.auth.router._models import (
    ImpersonatedUser,
    ImpersonateRequest,
    ImpersonateResponse,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/users/{user_id}/impersonate", response_model=ImpersonateResponse)
async def start_impersonation(
    request: Request,
    user_id: str,
    body: ImpersonateRequest | None = None,
    admin: AuthUser = Depends(require_admin()),
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    auth_manager: AuthManager = Depends(get_auth_manager_dep),
    audit=Depends(get_audit_logger_dep),
):
    """Begin impersonating ``user_id``. Admin only.

    Returns a bounded-lifetime access token whose identity is the target user.
    The admin's own session/cookie is untouched, so stopping impersonation
    simply restores the admin (see ``/auth/impersonation/stop``).
    """
    target = persistence.get_user_by_id(user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Eligibility (feature flag, no self/nested, active/unlocked, admin policy).
    assert_target_impersonatable(admin, target, config)

    # Resolve the admin's email for the audit trail + UI banner display.
    admin_user = persistence.get_user_by_id(admin.user_id)
    admin_email = admin_user.email if admin_user else None
    reason = body.reason if body else None

    actor_claim = build_actor_claim(admin.user_id, admin_email, reason)
    token = await issue_impersonation_token(
        auth_manager,
        target,
        actor_claim,
        config.impersonation_lifetime,
        tenant_id=resolve_user_tenant(target.id, config),
    )

    audit.log(
        action=AuditAction.IMPERSONATION_STARTED,
        actor_id=admin.user_id,
        target_id=target.id,
        details={"target_email": target.email, "reason": reason},
        ip_address=get_client_ip(request),
    )
    logger.info("Admin %s started impersonating user %s", admin.user_id, target.id)

    return ImpersonateResponse(
        access_token=token,
        expires_in=config.impersonation_lifetime,
        impersonated=ImpersonatedUser(
            id=target.id,
            email=target.email,
            username=target.username,
            roles=[r.value for r in target.roles],
        ),
    )
