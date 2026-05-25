"""OIDC stub. Verifies JWT against issuer JWKS, maps `sub` → User.

Not used in MVP. Activated when DOCHECK_OIDC_ISSUER set.
Resolves principal from JWT claims; auto-provisions User row on first sight.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .config import settings
from .logging import log


@dataclass(frozen=True)
class OIDCConfig:
    issuer: str
    audience: str
    jwks_uri: str
    enabled: bool


def get_oidc_config() -> OIDCConfig:
    issuer = getattr(settings, "oidc_issuer", "") or ""
    audience = getattr(settings, "oidc_audience", "") or "docheck"
    jwks_uri = getattr(settings, "oidc_jwks_uri", "") or ""
    return OIDCConfig(
        issuer=issuer,
        audience=audience,
        jwks_uri=jwks_uri
        or (issuer.rstrip("/") + "/.well-known/jwks.json" if issuer else ""),
        enabled=bool(issuer),
    )


_jwks_cache: dict[str, Any] = {"keys": [], "fetched_at": 0.0}
_JWKS_TTL = 3600


async def _fetch_jwks(jwks_uri: str) -> list[dict[str, Any]]:
    import httpx

    now = time.time()
    if _jwks_cache["keys"] and now - _jwks_cache["fetched_at"] < _JWKS_TTL:
        cached: list[dict[str, Any]] = _jwks_cache["keys"]
        return cached
    async with httpx.AsyncClient(timeout=5) as client:
        res = await client.get(jwks_uri)
        res.raise_for_status()
        keys: list[dict[str, Any]] = res.json().get("keys", [])
    _jwks_cache.update(keys=keys, fetched_at=now)
    return keys


async def verify_id_token(token: str) -> dict[str, Any]:
    """Verify JWT signature + claims. Returns claims dict on success."""
    cfg = get_oidc_config()
    if not cfg.enabled:
        raise RuntimeError("OIDC not configured")

    try:
        from jose import jwt  # python-jose; add to deps when activating
    except ImportError as exc:
        log.error("oidc.dep_missing", error=str(exc))
        raise

    keys = await _fetch_jwks(cfg.jwks_uri)
    decoded: dict[str, Any] = jwt.decode(
        token,
        key={"keys": keys},
        algorithms=["RS256", "ES256"],
        audience=cfg.audience,
        issuer=cfg.issuer,
    )
    return decoded


# Mapping JWT claim → User row provisioning hook (implement in F4)
async def provision_user_from_claims(claims: dict[str, Any]) -> str:
    """Create or fetch local User from OIDC claims. Returns user_id."""
    sub = claims.get("sub", "")
    raise NotImplementedError(f"OIDC provisioning gated to F4 hardening (sub={sub})")
