"""Admin account-state actions: unlock, session revocation, MFA disable."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.admin_router._helpers import get_client_ip
from plugins.auth.admin_router._models import MessageResponse
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_persistence_dep,
    require_admin,
)
from plugins.auth.persistence import AuthPersistence

logger = get_logger(__name__)

router = APIRouter()


@router.post("/users/{user_id}/unlock", response_model=MessageResponse)
async def unlock_user(
    request: Request,
    user_id: str,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """
    Unlock a locked user account.

    Clears failed login attempts and lockout timestamp.
    Admin only.
    """

    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_locked():
        return MessageResponse(message="User account is not locked")

    persistence.unlock_user(user_id)

    audit.log(
        action=AuditAction.USER_UNLOCKED,
        actor_id=admin.user_id,
        target_id=user_id,
        details={"email": user.email},
        ip_address=get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} unlocked user {user.email}")

    return MessageResponse(message=f"User {user.email} has been unlocked")


@router.post("/users/{user_id}/revoke-sessions", response_model=MessageResponse)
async def revoke_user_sessions(
    request: Request,
    user_id: str,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """
    Revoke all active sessions for a user.

    Forces the user to log in again.
    Admin only.
    """

    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    count = persistence.revoke_all_user_tokens(user_id)

    audit.log(
        action=AuditAction.USER_SESSIONS_REVOKED,
        actor_id=admin.user_id,
        target_id=user_id,
        details={"email": user.email, "sessions_revoked": count},
        ip_address=get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} revoked {count} sessions for user {user.email}")

    return MessageResponse(message=f"Revoked {count} active sessions for {user.email}")


@router.delete("/users/{user_id}/mfa", response_model=MessageResponse)
async def disable_user_mfa(
    request: Request,
    user_id: str,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
):
    """
    Disable MFA for a user.

    Admin only.
    """

    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.mfa_enabled:
        return MessageResponse(message="MFA is not enabled for this user")

    user.mfa_enabled = False
    user.mfa_secret = None
    persistence.update_user(user)

    audit.log(
        action=AuditAction.USER_MFA_DISABLED,
        actor_id=admin.user_id,
        target_id=user_id,
        details={"email": user.email},
        ip_address=get_client_ip(request),
    )

    logger.info(f"Admin {admin.user_id} disabled MFA for user {user.email}")

    return MessageResponse(message=f"MFA disabled for {user.email}")
