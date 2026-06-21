"""
Admin impersonation primitives.

Implements "log in as user" for administrators following the modern delegation
model from RFC 8693 (OAuth 2.0 Token Exchange): the impersonation access token
keeps the *target* user as its ``sub`` (so every downstream check naturally
runs as the impersonated identity) while embedding a signed ``act`` (actor)
claim that records the real administrator. Because the claim lives inside the
signed JWT it cannot be forged, which makes the "stop impersonation" path
trustworthy without any server-side session bookkeeping.

Design choices (all aimed at "no regressions" + least privilege):

* The impersonation token carries **only the target's roles** — the admin
  drops their elevated powers for the duration, exactly as if they had logged
  in as that user.
* It is **short-lived** (bounded by ``AuthConfig.impersonation_lifetime``) and
  is an *access token only* — no refresh token / cookie is issued, so the
  admin's own session is never mutated and impersonation cannot be silently
  extended past its expiry.
* Eligibility is validated up front: no self-impersonation, target must be
  active/unlocked, and admins cannot be impersonated unless explicitly enabled.

This module is pure logic + a thin async token-mint helper; the HTTP wiring
lives in :mod:`plugins.auth.admin_router._impersonation` (start) and
:mod:`plugins.auth.router._impersonation_routes` (stop).
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from core.auth import AuthManager, AuthRole, AuthUser
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig

logger = get_logger(__name__)

#: JWT claim names. ``act`` is the RFC 8693 actor claim; ``imp`` is a boolean
#: marker that flags the token as an impersonation token (used to gate
#: credential-altering self-service operations and to drive the UI banner).
ACT_CLAIM = "act"
IMP_CLAIM = "imp"


def build_actor_claim(
    admin_id: str,
    admin_email: Optional[str],
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the signed ``act`` actor claim recording the real administrator.

    Args:
        admin_id: The administrator's user id (becomes ``act.sub``).
        admin_email: The administrator's email, for display in the UI banner.
        reason: Optional free-text justification (audited and embedded).

    Returns:
        A JSON-serialisable dict suitable for embedding as the ``act`` claim.
    """
    claim: Dict[str, Any] = {"sub": admin_id, "ts": int(time.time())}
    if admin_email:
        claim["email"] = admin_email
    if reason:
        claim["reason"] = reason[:280]
    return claim


def extract_actor(user: AuthUser) -> Optional[Dict[str, Any]]:
    """Return the ``act`` actor claim if ``user`` is an impersonation identity.

    A token is only treated as impersonation when it carries *both* the ``imp``
    marker and an ``act`` object, so a stray claim can never trip the logic.
    """
    meta = user.metadata or {}
    if not meta.get(IMP_CLAIM):
        return None
    actor = meta.get(ACT_CLAIM)
    return actor if isinstance(actor, dict) and actor.get("sub") else None


def is_impersonating(user: AuthUser) -> bool:
    """True when the identity is acting through an impersonation token."""
    return extract_actor(user) is not None


def assert_target_impersonatable(
    admin: AuthUser,
    target: Any,
    config: AuthConfig,
) -> None:
    """Validate that ``admin`` may impersonate ``target`` (raises otherwise).

    Args:
        admin: The authenticated administrator initiating impersonation.
        target: The target user record (``plugins.auth.models.User``).
        config: Auth configuration (feature flag + admin-impersonation policy).

    Raises:
        HTTPException: 403/409 with a precise reason when not permitted.
    """
    if not config.impersonation_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impersonation is disabled",
        )
    # No nested impersonation: an already-impersonating session must stop first.
    if is_impersonating(admin):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already impersonating; stop the current session first",
        )
    if target.id == admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot impersonate yourself",
        )
    if not target.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot impersonate an inactive user",
        )
    if target.is_locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot impersonate a locked user",
        )
    if AuthRole.ADMIN in target.roles and not config.allow_impersonate_admins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impersonating administrators is not permitted",
        )


async def issue_impersonation_token(
    auth_manager: AuthManager,
    target: Any,
    actor_claim: Dict[str, Any],
    lifetime: int,
    tenant_id: Optional[str] = None,
) -> str:
    """Mint a short-lived impersonation access token for ``target``.

    The token's ``sub`` is the target (so all authorization runs as them) with
    the target's own roles, plus the signed ``act`` actor claim and ``imp``
    marker. ``exp`` is overridden to bound the lifetime independently of the
    handler's default access-token lifetime.

    ``tenant_id`` scopes the token to the target's tenant so the admin sees
    exactly the data the target would (identity-derived tenancy). When omitted
    it falls back to the target's per-user tenant.
    """
    now = int(time.time())
    extra_claims: Dict[str, Any] = {
        ACT_CLAIM: actor_claim,
        IMP_CLAIM: True,
        "exp": now + max(60, int(lifetime)),
        "tenant_id": tenant_id or target.id,
    }
    return await auth_manager.create_token(
        target.id,
        target.roles,
        **extra_claims,
    )
