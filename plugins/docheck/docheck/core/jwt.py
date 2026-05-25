"""Local JWT issuer/validator.

MVP: HS256 with secret derived from Ed25519 master key bytes.
F4 hardening: swap to EdDSA via PyJWT (supports natively) or external IdP.
OIDC dispatch: when DOCHECK_OIDC_ISSUER set, defers to OIDC verifier.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from jose import jwt
from jose.exceptions import JWTError

from ..services.audit import _signing_key  # reuse Ed25519 key as secret source
from .config import settings
from .logging import log

_ALGORITHM = "HS256"
_AUDIENCE = "docheck-engine"
_ISSUER = "docheck-local"
_DEFAULT_TTL = 8 * 3600  # 8h


def _hmac_secret() -> str:
    """Derive HMAC secret from Ed25519 private key bytes (deterministic per deploy)."""
    raw = _signing_key.encode()  # 32 bytes
    return hashlib.sha256(b"docheck.jwt.hs256\x00" + raw).hexdigest()


def issue_token(
    *,
    user_id: str,
    email: str,
    roles: list[str],
    tenant_id: str = "default",
    ttl: int = _DEFAULT_TTL,
) -> str:
    now = int(time.time())
    claims = {
        "sub": user_id,
        "email": email,
        "roles": roles,
        "tid": tenant_id,
        "iss": _ISSUER,
        "aud": _AUDIENCE,
        "iat": now,
        "exp": now + ttl,
    }
    encoded: str = jwt.encode(claims, _hmac_secret(), algorithm=_ALGORITHM)
    return encoded


def verify_local_token(token: str) -> dict[str, Any]:
    try:
        decoded: dict[str, Any] = jwt.decode(
            token,
            _hmac_secret(),
            algorithms=[_ALGORITHM],
            audience=_AUDIENCE,
            issuer=_ISSUER,
        )
        return decoded
    except JWTError as exc:
        log.info("jwt.invalid", error=str(exc))
        raise


async def verify_token(token: str) -> dict[str, Any]:
    """Dispatch: OIDC if configured, else local HS256."""
    if settings.oidc_issuer:
        from .oidc import verify_id_token

        return await verify_id_token(token)
    return verify_local_token(token)
