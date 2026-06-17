"""WebAuthn / passkey endpoints: enrollment (authenticated) and passwordless
login (public, discoverable credentials)."""

import base64
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status

from core.auth import AuthManager, AuthUser
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import (
    get_auth_config_dep,
    get_auth_manager_dep,
    get_auth_persistence_dep,
    get_current_active_user,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.rate_limiting import RateLimit as RateLimiter
from plugins.auth.router._helpers import client_ip, issue_tokens
from plugins.auth.security import add_security_headers
from plugins.auth.webauthn import get_webauthn_manager, is_webauthn_available

logger = get_logger(__name__)

router = APIRouter(prefix="/webauthn")


def _b64url_decode(data: str) -> bytes:
    """Decode a base64url string (with or without padding) to bytes."""
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _require_enabled(config: AuthConfig) -> None:
    if not config.webauthn_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Passkeys are disabled."
        )
    if not is_webauthn_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebAuthn library not installed on the server.",
        )


# ---- Enrollment (authenticated) -------------------------------------------


@router.post("/register/options")
async def register_options(
    user: AuthUser = Depends(get_current_active_user),
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Start passkey registration for the current user."""
    _require_enabled(config)
    db_user = persistence.get_user_by_id(user.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = persistence.list_webauthn_credentials(db_user.id)
    manager = get_webauthn_manager()
    return manager.generate_registration_options(
        user_id=db_user.id,
        username=db_user.email,
        display_name=db_user.full_name or db_user.username or db_user.email,
        existing_credentials=existing,
    )


@router.post("/register/verify")
async def register_verify(
    payload: Dict[str, Any] = Body(...),
    user: AuthUser = Depends(get_current_active_user),
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Verify a registration response and store the credential."""
    _require_enabled(config)
    credential = payload.get("credential")
    name = (payload.get("name") or "Passkey").strip()[:100]
    if not credential:
        raise HTTPException(status_code=400, detail="Missing credential")
    manager = get_webauthn_manager()
    try:
        cred = manager.verify_registration(user.user_id, credential)
    except Exception as exc:
        logger.warning("Passkey registration failed: %s", exc)
        raise HTTPException(status_code=400, detail="Passkey registration failed")
    persistence.add_webauthn_credential(cred, name=name)
    persistence.record_login_event(user.user_id, "passkey_registered", method="passkey")
    return {"status": "ok", "name": name}


@router.get("/credentials")
async def list_credentials(
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """List the current user's passkeys."""
    creds = persistence.list_webauthn_credentials(user.user_id)
    return [
        {
            "id": c.id,
            "name": c.name or "Passkey",
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "last_used": c.last_used.isoformat() if c.last_used else None,
        }
        for c in creds
    ]


@router.patch("/credentials/{cred_id}")
async def rename_credential(
    cred_id: str,
    payload: Dict[str, Any] = Body(...),
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Rename one of the current user's passkeys."""
    name = (payload.get("name") or "").strip()[:100]
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    if not persistence.rename_webauthn_credential(user.user_id, cred_id, name):
        raise HTTPException(status_code=404, detail="Passkey not found")
    return {"status": "ok"}


@router.delete("/credentials/{cred_id}")
async def delete_credential(
    cred_id: str,
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Delete one of the current user's passkeys."""
    if not persistence.delete_webauthn_credential(user.user_id, cred_id):
        raise HTTPException(status_code=404, detail="Passkey not found")
    persistence.record_login_event(user.user_id, "passkey_removed", method="passkey")
    return {"status": "ok"}


# ---- Passwordless login (public, discoverable credentials) ----------------


@router.post("/authenticate/options")
async def authenticate_options(
    config: AuthConfig = Depends(get_auth_config_dep),
):
    """Start a passkey login (discoverable credential flow)."""
    _require_enabled(config)
    manager = get_webauthn_manager()
    return manager.generate_authentication_options(user_credentials=None)


@router.post(
    "/authenticate/verify",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def authenticate_verify(
    request: Request,
    response: Response,
    payload: Dict[str, Any] = Body(...),
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    auth_manager: AuthManager = Depends(get_auth_manager_dep),
):
    """Verify a passkey assertion and issue a session."""
    _require_enabled(config)
    credential = payload.get("credential")
    challenge_id = payload.get("challenge_id")
    if not credential or not challenge_id:
        raise HTTPException(status_code=400, detail="Missing credential or challenge")

    raw_id = credential.get("rawId") or credential.get("id")
    if not raw_id:
        raise HTTPException(status_code=400, detail="Malformed credential")
    stored = persistence.get_webauthn_by_credential_id(_b64url_decode(raw_id))
    if not stored:
        raise HTTPException(status_code=401, detail="Unknown passkey")

    db_user = persistence.get_user_by_id(stored.user_id)
    if not db_user or not db_user.is_active or db_user.is_locked():
        raise HTTPException(status_code=403, detail="Account unavailable")

    manager = get_webauthn_manager()
    try:
        updated = manager.verify_authentication(credential, challenge_id, stored)
    except Exception as exc:
        logger.warning("Passkey assertion failed: %s", exc)
        persistence.record_login_event(
            stored.user_id,
            "login_failure",
            success=False,
            ip_address=client_ip(request),
            method="passkey",
        )
        raise HTTPException(status_code=401, detail="Passkey verification failed")

    persistence.update_webauthn_sign_count(updated.id, updated.sign_count)
    persistence.record_login_event(
        db_user.id,
        "login_success",
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
        method="passkey",
    )
    add_security_headers(response)
    return await issue_tokens(
        db_user.id, db_user.roles, response, persistence, auth_manager, config
    )
