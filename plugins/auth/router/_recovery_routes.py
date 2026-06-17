"""Public self-service recovery: forgot/reset password, email verification,
and invitation acceptance. All endpoints are unauthenticated by design and
avoid account enumeration."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.auth import AuthRole
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import get_auth_config_dep, get_auth_persistence_dep
from plugins.auth.mailer import get_mailer
from plugins.auth.password import hash_password, validate_password_strength_async
from plugins.auth.persistence import AuthPersistence
from plugins.auth.router._helpers import client_ip, resolve_locale
from plugins.auth.router._models import (
    AcceptInviteRequest,
    ForgotPasswordRequest,
    InviteInfoResponse,
    MessageResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UserInfoResponse,
    VerifyEmailRequest,
)
from plugins.auth.security import sanitize_log_input

logger = get_logger(__name__)

router = APIRouter()

# Generic, enumeration-safe acknowledgement.
_ACK = "If an account matches, you'll receive an email with next steps."


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Start a password reset. Always returns the same acknowledgement so
    callers can't probe which accounts exist."""
    if not config.account_recovery_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account recovery is disabled. Contact your administrator.",
        )
    user = persistence.get_user_by_identifier(body.identifier)
    if user and user.is_active:
        token = persistence.create_recovery_token(
            user.id, "password_reset", ttl_minutes=60
        )
        await get_mailer().send_password_reset(
            user.email, token, resolve_locale(request)
        )
        persistence.record_login_event(
            user.id,
            "password_reset_requested",
            ip_address=client_ip(request),
            method="password",
        )
        logger.info("Password reset requested for %s", sanitize_log_input(user.email))
    return MessageResponse(message=_ACK)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Finish a password reset with a one-time token."""
    user_id = persistence.consume_recovery_token(body.token, "password_reset")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )
    errors = await validate_password_strength_async(
        body.new_password, check_breaches=config.check_pwned_passwords
    )
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors)
        )
    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.password_hash = hash_password(body.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    persistence.update_user(user)
    persistence.touch_password_changed(user.id)
    persistence.revoke_all_user_tokens(user.id)
    persistence.record_login_event(
        user.id, "password_reset", ip_address=client_ip(request), method="password"
    )
    logger.info("Password reset completed for user %s", user.id)
    return MessageResponse(message="Password updated. You can now sign in.")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest,
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Confirm an email address with a one-time token."""
    user_id = persistence.consume_recovery_token(body.token, "email_verify")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link.",
        )
    persistence.set_email_verified(user_id, True)
    return MessageResponse(message="Email verified. You can now sign in.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    body: ResendVerificationRequest,
    request: Request,
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Re-issue an email-verification link (enumeration-safe)."""
    user = persistence.get_user_by_email(body.email)
    if user and not user.email_verified:
        token = persistence.create_recovery_token(
            user.id, "email_verify", ttl_minutes=1440
        )
        await get_mailer().send_email_verification(
            user.email, token, resolve_locale(request)
        )
    return MessageResponse(message=_ACK)


@router.get("/invitations/accept", response_model=InviteInfoResponse)
async def invitation_info(
    token: str,
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Return the email/roles of a pending invitation for the accept screen."""
    invite = persistence.get_invitation(token)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or expired.",
        )
    return InviteInfoResponse(email=invite["email"], roles=list(invite["roles"]))


@router.post(
    "/invitations/accept",
    response_model=UserInfoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def accept_invitation(
    body: AcceptInviteRequest,
    request: Request,
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Accept an invitation: create the account with the invited roles."""
    invite = persistence.get_invitation(body.token)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation not found or expired.",
        )
    if persistence.get_user_by_email(invite["email"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    errors = await validate_password_strength_async(
        body.password, check_breaches=config.check_pwned_passwords
    )
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors)
        )
    roles = set()
    for r in invite["roles"]:
        try:
            roles.add(AuthRole(r))
        except ValueError:
            continue
    user = persistence.create_user(
        email=invite["email"],
        username=body.username,
        password_hash=hash_password(body.password),
        roles=roles or {AuthRole.USER},
    )
    persistence.accept_invitation(body.token)
    persistence.set_email_verified(user.id, True)
    if body.full_name:
        persistence.update_profile(user.id, body.full_name, body.username)
    persistence.record_login_event(
        user.id, "invite_accepted", ip_address=client_ip(request), method="password"
    )
    logger.info("Invitation accepted, user created: %s", user.email)
    return UserInfoResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        roles=[r.value for r in user.roles],
        mfa_enabled=user.mfa_enabled,
        allowed_tabs=user.allowed_tabs,
    )
