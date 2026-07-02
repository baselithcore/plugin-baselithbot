"""MFA second-factor verification endpoint (TOTP / backup code).

Split out of ``_auth_routes`` to honour the 500 LOC cap. Hardened against TOTP
replay (each accepted time-step is recorded and cannot be reused) and against
per-challenge brute force (the temp token is burned after a few wrong codes).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from core.auth import AuthManager
from core.observability.logging import get_logger
from plugins.auth.dependencies import (
    get_auth_config_dep,
    get_auth_manager_dep,
    get_auth_persistence_dep,
)
from plugins.auth.mfa import verify_totp_with_step
from plugins.auth.persistence import AuthPersistence
from plugins.auth.rate_limiting import RateLimit as RateLimiter
from plugins.auth.router._helpers import (
    issue_tokens,
    log_login_success,
    verify_backup_code,
)
from plugins.auth.router._models import MFAVerifyRequest, TokenResponse
from plugins.auth.security import add_security_headers, mfa_token_store

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/mfa/verify",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
    response_model=TokenResponse,
    responses={429: {"description": "Too many requests"}},
)
async def verify_mfa(
    mfa_request: MFAVerifyRequest,
    request: Request,
    response: Response,
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    auth_manager: AuthManager = Depends(get_auth_manager_dep),
):
    """Complete MFA verification after initial login (TOTP or backup code)."""
    # Validate temp token using secure store
    token_data = mfa_token_store.get(mfa_request.temp_token)
    if not token_data:
        logger.warning("MFA verify failed: Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired temporary token",
        )

    user = persistence.get_user_by_id(token_data["user_id"])
    if not user or not user.mfa_secret:
        mfa_token_store.delete(mfa_request.temp_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user or MFA not configured",
        )

    # Try TOTP verification first. The matched time-step is recorded so the same
    # code cannot be replayed within its (±1 step) validity window.
    code = mfa_request.code.replace("-", "").replace(" ", "")
    if len(code) == 6:
        step = verify_totp_with_step(user.mfa_secret, code)
        if step is not None:
            if not persistence.consume_totp_step(user.id, step):
                mfa_token_store.delete(mfa_request.temp_token)
                logger.warning(f"MFA TOTP replay rejected for user {user.id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="This code was already used. Wait for a new code.",
                )
            mfa_token_store.delete(mfa_request.temp_token)
            logger.info(f"MFA TOTP verification successful for user {user.id}")
            log_login_success(request, persistence, user.id, "mfa")
            add_security_headers(response)
            config = await get_auth_config_dep()
            return await issue_tokens(
                user.id, user.roles, response, persistence, auth_manager, config
            )

    # Try backup code using secure comparison
    if verify_backup_code(mfa_request.code, user.id, persistence):
        mfa_token_store.delete(mfa_request.temp_token)
        remaining = persistence.get_unused_backup_codes_count(user.id)
        logger.info(f"User used backup code. {remaining} remaining.")
        logger.info(f"MFA backup code verification successful for user {user.id}")
        log_login_success(request, persistence, user.id, "mfa")
        add_security_headers(response)
        config = await get_auth_config_dep()
        return await issue_tokens(
            user.id, user.roles, response, persistence, auth_manager, config
        )

    # Per-challenge throttle: burn the temp token after too many wrong codes so
    # the 5-minute window cannot be used to brute-force the 6-digit code (the
    # per-IP limit alone is insufficient behind spoofable proxies).
    burned = mfa_token_store.register_failure(mfa_request.temp_token, max_attempts=5)
    logger.warning(f"MFA invalid code for user {user.id} (token_burned={burned})")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Too many attempts; please sign in again." if burned else "Invalid MFA code"
        ),
    )


__all__ = ["router"]
