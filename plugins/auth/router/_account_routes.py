"""Current-user info and self-service MFA management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.dependencies import (
    forbid_while_impersonating,
    get_auth_persistence_dep,
    get_current_active_user,
    require_admin,
)
from plugins.auth.mfa import (
    generate_backup_codes,
    generate_secret,
    get_provisioning_uri,
    get_qr_code_base64,
    verify_totp,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.router._models import (
    ImpersonatorInfo,
    MessageResponse,
    MFASetupResponse,
    UserInfoResponse,
)

logger = get_logger(__name__)

router = APIRouter()


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    Get current authenticated user info.
    """
    db_user = persistence.get_user_by_id(user.user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Surface impersonation context so the UI can render a banner + Stop control.
    from plugins.auth.impersonation import extract_actor

    actor = extract_actor(user)
    impersonator = (
        ImpersonatorInfo(
            id=str(actor.get("sub")),
            email=actor.get("email"),
            since=actor.get("ts"),
        )
        if actor
        else None
    )

    return UserInfoResponse(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        roles=[r.value for r in db_user.roles],
        mfa_enabled=db_user.mfa_enabled,
        allowed_tabs=db_user.allowed_tabs,
        is_impersonating=impersonator is not None,
        impersonator=impersonator,
    )


@router.post(
    "/mfa/setup",
    response_model=MFASetupResponse,
    dependencies=[Depends(forbid_while_impersonating)],
)
async def setup_mfa(
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    Initialize MFA setup for current user.

    Returns secret, QR code, and backup codes.
    User must complete setup by verifying a code.
    """
    db_user = persistence.get_user_by_id(user.user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate new secret
    secret = generate_secret()
    provisioning_uri = get_provisioning_uri(db_user.email, secret)

    # Generate QR code
    try:
        qr_code = get_qr_code_base64(db_user.email, secret)
    except ImportError:
        qr_code = None

    # Generate backup codes
    plain_codes, hashed_codes = generate_backup_codes(10)

    # Store secret (not yet enabled) and backup codes
    db_user.mfa_secret = secret
    persistence.update_user(db_user)
    persistence.store_backup_codes(db_user.id, hashed_codes)

    return MFASetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        qr_code=qr_code,
        backup_codes=plain_codes,
    )


@router.post(
    "/mfa/enable",
    response_model=MessageResponse,
    dependencies=[Depends(forbid_while_impersonating)],
)
async def enable_mfa(
    code: str,
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    Enable MFA after verifying setup code.
    """
    db_user = persistence.get_user_by_id(user.user_id)

    if not db_user or not db_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not set up. Call /mfa/setup first.",
        )

    if not verify_totp(db_user.mfa_secret, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    db_user.mfa_enabled = True
    persistence.update_user(db_user)

    logger.info(f"MFA enabled for user {db_user.email}")
    return MessageResponse(message="MFA enabled successfully")


@router.post("/mfa/disable", response_model=MessageResponse)
async def disable_mfa(
    user: AuthUser = Depends(require_admin()),
    target_user_id: Optional[str] = None,
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    Disable MFA for a user (admin only).

    If target_user_id is not provided, disables for current user.
    """
    user_id = target_user_id or user.user_id
    db_user = persistence.get_user_by_id(user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db_user.mfa_enabled = False
    db_user.mfa_secret = None
    persistence.update_user(db_user)

    logger.info(f"MFA disabled for user {db_user.email} by admin {user.user_id}")
    return MessageResponse(message="MFA disabled successfully")
