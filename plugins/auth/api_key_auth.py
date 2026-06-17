"""Resolve API keys (personal access tokens) into an authenticated user.

Keys may be presented either as ``X-API-Key: bsk_...`` or as a bearer token
(``Authorization: Bearer bsk_...``). This bridges our DB-backed keys into the
existing AuthUser model so any guarded route can be called by a service token.
"""

from typing import Optional

from core.auth import AuthRole, AuthUser
from core.observability.logging import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "bsk_"


def extract_api_key(headers) -> Optional[str]:
    """Pull an API key from request headers, if present."""
    direct = headers.get("x-api-key")
    if direct and direct.startswith(_KEY_PREFIX):
        return direct.strip()
    auth = headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token.startswith(_KEY_PREFIX):
            return token
    return None


def authenticate_api_key(persistence, key: str) -> Optional[AuthUser]:
    """Validate an API key and return the owning user as an AuthUser."""
    record = persistence.validate_api_key(key)
    if not record:
        return None
    db_user = persistence.get_user_by_id(str(record["user_id"]))
    if not db_user or not db_user.is_active or db_user.is_locked():
        return None
    return AuthUser(
        user_id=db_user.id,
        email=db_user.email,
        roles=db_user.roles,
        metadata={
            "auth_method": "api_key",
            "api_key_id": str(record["id"]),
            "scopes": list(record.get("scopes") or []),
            "allowed_tabs": db_user.allowed_tabs,
        },
    )


def maybe_authenticate_api_key(persistence, headers) -> Optional[AuthUser]:
    """Convenience: extract + authenticate in one step (None if no/invalid key)."""
    key = extract_api_key(headers)
    if not key:
        return None
    try:
        return authenticate_api_key(persistence, key)
    except Exception as exc:  # pragma: no cover - never block on key errors
        logger.warning("API key authentication error: %s", exc)
        return None


# Re-exported for callers that only need the role enum.
__all__ = [
    "extract_api_key",
    "authenticate_api_key",
    "maybe_authenticate_api_key",
    "AuthRole",
]
