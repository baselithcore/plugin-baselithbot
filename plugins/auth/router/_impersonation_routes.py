"""Stop-impersonation endpoint, mounted under ``/api/auth``.

Reachable by the *impersonated* (typically non-admin) session, so it is guarded
by plain authentication rather than the admin role. Trust comes from the signed
``act`` actor claim embedded in the impersonation token: it names the real
administrator, who is re-validated against the database before a fresh admin
access token is minted. The impersonation token is then revoked.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth import AuthManager, AuthRole, AuthUser
from core.observability.logging import get_logger
from plugins.auth.audit import AuditAction
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_config_dep,
    get_auth_manager_dep,
    get_auth_persistence_dep,
    require_auth,
)
from plugins.auth.impersonation import extract_actor
from plugins.auth.persistence import AuthPersistence
from plugins.auth.router._helpers import client_ip
from plugins.auth.router._models import TokenResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/impersonation")

_bearer = HTTPBearer(auto_error=False)


@router.post("/stop", response_model=TokenResponse)
async def stop_impersonation(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    user: AuthUser = Depends(require_auth),
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    auth_manager: AuthManager = Depends(get_auth_manager_dep),
    audit=Depends(get_audit_logger_dep),
):
    """End the current impersonation session and restore the administrator.

    Returns a fresh admin access token. The admin's own refresh session was
    never altered, so even if this call is missed a plain refresh still
    restores the administrator.
    """
    actor = extract_actor(user)
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active impersonation session",
        )

    admin_id = str(actor["sub"])
    admin_user = persistence.get_user_by_id(admin_id)

    # Revoke the impersonation token regardless of the outcome below so it
    # cannot be reused after the session is torn down.
    if credentials and credentials.credentials:
        await auth_manager.revoke_token(credentials.credentials)

    if (
        not admin_user
        or not admin_user.is_active
        or admin_user.is_locked()
        or AuthRole.ADMIN not in admin_user.roles
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator can no longer be restored; please log in again",
        )

    admin_token = await auth_manager.create_token(admin_user.id, admin_user.roles)

    audit.log(
        action=AuditAction.IMPERSONATION_ENDED,
        actor_id=admin_id,
        target_id=user.user_id,
        ip_address=client_ip(request),
    )
    logger.info("Admin %s stopped impersonating user %s", admin_id, user.user_id)

    return TokenResponse(
        access_token=admin_token,
        expires_in=config.session_lifetime,
    )
