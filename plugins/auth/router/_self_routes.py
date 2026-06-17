"""Self-service "My Account" endpoints: profile, password, sessions/devices,
security activity, and self-managed MFA. All require an authenticated, active
user and operate only on that user's own data."""

import hashlib
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, status

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import (
    forbid_while_impersonating,
    get_auth_config_dep,
    get_auth_persistence_dep,
    get_current_active_user,
)
from plugins.auth.mfa import verify_totp
from plugins.auth.password import (
    hash_password,
    validate_password_strength_async,
    verify_password,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.router._helpers import verify_backup_code
from plugins.auth.router._models import (
    AccountResponse,
    ActivityEntry,
    ChangePasswordRequest,
    MessageResponse,
    ProfileUpdateRequest,
    SelfMfaDisableRequest,
    SessionInfo,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/me")


def _account_response(persistence: AuthPersistence, user_id: str) -> AccountResponse:
    db_user = persistence.get_user_by_id(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    passkeys = persistence.list_webauthn_credentials(user_id)
    return AccountResponse(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        full_name=db_user.full_name,
        roles=[r.value for r in db_user.roles],
        mfa_enabled=db_user.mfa_enabled,
        email_verified=db_user.email_verified,
        status=db_user.status,
        passkey_count=len(passkeys),
        last_login=db_user.last_login.isoformat() if db_user.last_login else None,
        last_login_ip=db_user.last_login_ip,
    )


@router.get("/account", response_model=AccountResponse)
async def get_account(
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Rich account summary for the My Account surface."""
    return _account_response(persistence, user.user_id)


@router.patch("/profile", response_model=AccountResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Update the current user's display name and username."""
    if body.username:
        existing = persistence.get_user_by_username(body.username)
        if existing and existing.id != user.user_id:
            raise HTTPException(status_code=409, detail="Username already taken")
    persistence.update_profile(user.user_id, body.full_name, body.username)
    return _account_response(persistence, user.user_id)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    dependencies=[Depends(forbid_while_impersonating)],
)
async def change_password(
    body: ChangePasswordRequest,
    user: AuthUser = Depends(get_current_active_user),
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
):
    """Change the current user's password (requires the current password)."""
    db_user = persistence.get_user_by_id(user.user_id)
    if not db_user or not verify_password(body.current_password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    errors = await validate_password_strength_async(
        body.new_password, check_breaches=config.check_pwned_passwords
    )
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    db_user.password_hash = hash_password(body.new_password)
    persistence.update_user(db_user)
    persistence.touch_password_changed(db_user.id)
    # Keep the current session, sign out everywhere else.
    if refresh_token:
        persistence.revoke_other_user_tokens(db_user.id, refresh_token)
    persistence.record_login_event(db_user.id, "password_changed", method="password")
    return MessageResponse(message="Password updated.")


@router.get("/sessions", response_model=list[SessionInfo])
async def list_my_sessions(
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
):
    """List the current user's active sessions/devices."""
    current_hash = (
        hashlib.sha256(refresh_token.encode()).hexdigest() if refresh_token else None
    )
    out = []
    for s in persistence.get_active_sessions(user.user_id):
        out.append(
            SessionInfo(
                id=s.id,
                created_at=s.created_at.isoformat() if s.created_at else None,
                expires_at=s.expires_at.isoformat() if s.expires_at else None,
                current=bool(current_hash and s.token_hash == current_hash),
            )
        )
    return out


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_my_session(
    session_id: str,
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Revoke one of the current user's sessions."""
    if not persistence.revoke_session_by_id(user.user_id, session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return MessageResponse(message="Session revoked.")


@router.post("/sessions/revoke-others", response_model=MessageResponse)
async def revoke_my_other_sessions(
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
):
    """Sign out of every other session, keeping the current one."""
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No active session cookie")
    count = persistence.revoke_other_user_tokens(user.user_id, refresh_token)
    return MessageResponse(message=f"Signed out of {count} other session(s).")


@router.get("/activity", response_model=list[ActivityEntry])
async def my_activity(
    limit: int = 50,
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Recent login & security activity for the current user."""
    rows = persistence.get_login_history(user.user_id, limit=min(limit, 200))
    return [
        ActivityEntry(
            event=r["event"],
            method=r.get("method") or "password",
            success=bool(r.get("success", True)),
            ip_address=r.get("ip_address"),
            user_agent=r.get("user_agent"),
            risk_score=int(r.get("risk_score") or 0),
            created_at=r["created_at"].isoformat() if r.get("created_at") else None,
        )
        for r in rows
    ]


@router.post(
    "/mfa/disable",
    response_model=MessageResponse,
    dependencies=[Depends(forbid_while_impersonating)],
)
async def disable_my_mfa(
    body: SelfMfaDisableRequest,
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Self-disable MFA, confirmed with a valid TOTP or backup code."""
    db_user = persistence.get_user_by_id(user.user_id)
    if not db_user or not db_user.mfa_enabled or not db_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled")
    code = body.code.replace("-", "").replace(" ", "")
    ok = (
        len(code) == 6 and verify_totp(db_user.mfa_secret, code)
    ) or verify_backup_code(body.code, db_user.id, persistence)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code"
        )
    db_user.mfa_enabled = False
    db_user.mfa_secret = None
    persistence.update_user(db_user)
    persistence.record_login_event(db_user.id, "mfa_disabled", method="mfa")
    logger.info("User %s self-disabled MFA", db_user.id)
    return MessageResponse(message="MFA disabled.")
