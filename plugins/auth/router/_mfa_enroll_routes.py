"""Forced MFA enrollment — used when policy mandates MFA for a user who has
not set it up yet.

At login (``_auth_routes``) a required-but-unenrolled user is handed an
enrollment challenge instead of a session: a fresh TOTP secret + QR + backup
codes and a short-lived ``enroll_token``. The client shows the QR, then posts
the first code to ``/mfa/enroll-verify`` here, which activates MFA and issues
the real session. No tokens exist until the second factor is proven, so the
mandate cannot be bypassed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from core.observability.logging import get_logger
from plugins.auth.dependencies import (
    get_auth_config_dep,
    get_auth_manager_dep,
    get_auth_persistence_dep,
)
from plugins.auth.mfa import (
    generate_backup_codes,
    generate_secret,
    get_provisioning_uri,
    get_qr_code_base64,
    verify_totp,
)
from plugins.auth.models import User
from plugins.auth.persistence import AuthPersistence
from plugins.auth.rate_limiting import RateLimit as RateLimiter
from plugins.auth.router._helpers import issue_tokens
from plugins.auth.router._models import (
    EnrollVerifyRequest,
    MFAEnrollmentRequiredResponse,
    TokenResponse,
)
from plugins.auth.security import generate_secure_token, mfa_token_store

logger = get_logger(__name__)

router = APIRouter()

# Enrollment-challenge lifetime: long enough to scan a QR + type a code.
_ENROLL_TTL_SECONDS = 600


def build_mfa_enrollment_challenge(user: User) -> MFAEnrollmentRequiredResponse:
    """Generate a pending TOTP secret + backup codes and stash them under a
    short-lived ``enroll_token`` (never persisted until verified)."""
    secret = generate_secret()
    provisioning_uri = get_provisioning_uri(user.email, secret)
    try:
        qr_code = get_qr_code_base64(user.email, secret)
    except ImportError:
        qr_code = None

    plain_codes, hashed_codes = generate_backup_codes(10)
    enroll_token = generate_secure_token("mfaenroll")
    mfa_token_store.store(
        enroll_token,
        {"user_id": user.id, "secret": secret, "backup_hashes": hashed_codes},
        ttl_seconds=_ENROLL_TTL_SECONDS,
    )
    return MFAEnrollmentRequiredResponse(
        enroll_token=enroll_token,
        secret=secret,
        provisioning_uri=provisioning_uri,
        qr_code=qr_code,
        backup_codes=plain_codes,
    )


@router.post(
    "/mfa/enroll-verify",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
    responses={
        400: {"description": "Invalid or expired enrollment / code"},
        429: {"description": "Too many requests"},
    },
)
async def enroll_verify(
    data: EnrollVerifyRequest,
    response: Response,
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    auth_manager=Depends(get_auth_manager_dep),
    config=Depends(get_auth_config_dep),
) -> TokenResponse:
    """Activate forced-enrollment MFA after verifying the first code, then log
    the user in."""
    stored = mfa_token_store.get(data.enroll_token)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment session expired. Please sign in again.",
        )

    secret = stored["secret"]
    if not verify_totp(secret, data.code.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    user = persistence.get_user_by_id(stored["user_id"])
    if not user or not user.is_active:
        mfa_token_store.delete(data.enroll_token)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account unavailable"
        )

    # Activate MFA and persist the backup codes generated with the challenge.
    user.mfa_secret = secret
    user.mfa_enabled = True
    persistence.update_user(user)
    persistence.store_backup_codes(user.id, stored["backup_hashes"])
    mfa_token_store.delete(data.enroll_token)

    persistence.record_login_event(user.id, "mfa_enrolled", method="mfa")
    logger.info("Forced MFA enrollment completed for user %s", user.id)

    return await issue_tokens(
        user.id, user.roles, response, persistence, auth_manager, config
    )


__all__ = ["router", "build_mfa_enrollment_challenge"]
