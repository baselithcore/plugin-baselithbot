"""Shared helper functions for auth route handlers."""

import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response

from core.auth import AuthManager
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.persistence import AuthPersistence
from plugins.auth.router._models import TokenResponse
from plugins.auth.security import generate_secure_token
from plugins.auth.tenancy import resolve_user_tenant

logger = get_logger(__name__)


def resolve_locale(request: Request) -> str:
    """Resolve the request locale ('en' default, 'it' supported) from
    ``Accept-Language``, so user-facing emails/messages are localized."""
    header = request.headers.get("accept-language", "") if request else ""
    return "it" if header.lower().lstrip().startswith("it") else "en"


def client_ip(request: Request) -> str | None:
    """Best-effort client IP.

    Forwarded headers (``X-Forwarded-For`` / ``X-Real-IP``) are spoofable, so
    they are honoured ONLY when the direct socket peer is a configured trusted
    proxy (``AUTH_TRUSTED_PROXIES``; ``*`` trusts all). Otherwise the real
    socket peer is returned, preventing an attacker from forging the IP recorded
    in audit/login history.
    """
    if not request:
        return None
    peer = request.client.host if request.client else None
    try:
        from core.di.container import ServiceRegistry

        trusted = ServiceRegistry.get(AuthConfig).trusted_proxies
    except Exception:
        trusted = []
    if peer and ("*" in trusted or peer in trusted):
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    return peer


def log_login_success(
    request: Request,
    persistence: AuthPersistence,
    user_id: str,
    method: str = "password",
):
    """Run risk assessment and append a success event to login history."""
    from plugins.auth.risk_assessment import get_risk_assessor

    assessor = get_risk_assessor()
    risk = assessor.assess_risk(request, user_id)
    assessor.record_successful_authentication(request, user_id)
    persistence.record_login_event(
        user_id,
        "login_success",
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
        risk_score=int(round(risk.score * 100)),
        method=method,
        details={"reasons": risk.reasons} if risk.reasons else None,
    )
    return risk


def log_login_failure(
    request: Request,
    persistence: AuthPersistence,
    user_id: str | None,
    reason: str,
):
    """Append a failure event to login history (best-effort)."""
    persistence.record_login_event(
        user_id,
        "login_failure",
        success=False,
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
        method="password",
        details={"reason": reason},
    )


def establish_session(
    user_id: str,
    response: Response,
    persistence: AuthPersistence,
    config: AuthConfig,
) -> None:
    """Set a fresh refresh-token cookie on ``response`` (used by redirect flows
    like SSO, where the SPA bootstraps its access token via /refresh)."""
    persistence.record_login_success(user_id)
    persistence.revoke_all_user_tokens(user_id)
    refresh_token = generate_secure_token(length=32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=config.refresh_lifetime)
    persistence.store_refresh_token(user_id, refresh_token, expires_at)
    response.set_cookie(
        key=config.cookie_name,
        value=refresh_token,
        httponly=config.cookie_httponly,
        secure=config.cookie_secure,
        samesite=config.cookie_samesite,
        max_age=config.refresh_lifetime,
        path="/api",
    )


def verify_backup_code(code: str, user_id: str, persistence: AuthPersistence) -> bool:
    """
    Verify backup code using constant-time comparison.

    Iterates through all unused codes to prevent timing attacks.
    """
    # Normalize code
    normalized = code.replace("-", "").replace(" ", "").upper()
    if len(normalized) == 8:
        formatted = f"{normalized[:4]}-{normalized[4:]}"
    else:
        formatted = code.upper()

    code_hash = hashlib.sha256(formatted.encode()).hexdigest()

    # Use persistence method which does the comparison
    return persistence.use_backup_code(user_id, code_hash)


async def issue_tokens(
    user_id: str,
    roles: set,
    response: Response,
    persistence: AuthPersistence,
    auth_manager: AuthManager,
    config: AuthConfig,
) -> TokenResponse:
    """Issue access and refresh tokens."""

    # Record successful login
    persistence.record_login_success(user_id)

    # SECURITY: Revoke all previous tokens to prevent session fixation
    # This ensures old sessions cannot be reused after successful login
    revoked_count = persistence.revoke_all_user_tokens(user_id)
    if revoked_count > 0:
        logger.info(f"Revoked {revoked_count} previous tokens for user {user_id}")

    # Create access token, scoped to the user's tenant (identity-derived: the
    # tenant comes from who is logged in, never a client-supplied header).
    tenant_id = resolve_user_tenant(user_id, config)
    access_token = await auth_manager.create_token(user_id, roles, tenant_id=tenant_id)

    # Create refresh token using secure generation
    refresh_token = generate_secure_token(length=32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=config.refresh_lifetime)
    persistence.store_refresh_token(user_id, refresh_token, expires_at)

    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key=config.cookie_name,
        value=refresh_token,
        httponly=config.cookie_httponly,
        secure=config.cookie_secure,
        samesite=config.cookie_samesite,
        max_age=config.refresh_lifetime,
        path="/api",  # Allow cookie for all API endpoints
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=config.session_lifetime,
    )
