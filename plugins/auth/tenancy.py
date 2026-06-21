"""User → tenant resolution.

Single source of truth for the tenant an authenticated session is scoped to.
The resolved ``tenant_id`` is embedded as a JWT claim at token-issue time
(see :func:`plugins.auth.router._helpers.issue_tokens`) and read back by
:func:`core.auth.jwt.JWTHandler.verify_token` → ``AuthUser.tenant_id`` →
the tenant context var (``core.context.set_tenant_context``) that every
tenant-aware plugin reads through ``get_current_tenant_id()``.

This is what makes tenancy **identity-derived** rather than client-supplied:
the tenant comes from *who is logged in*, never from a request header a caller
could forge.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from plugins.auth.config import AuthConfig

if TYPE_CHECKING:  # avoid a runtime import cycle (persistence imports config too)
    from plugins.auth.persistence import AuthPersistence


def resolve_user_tenant(
    user_id: str,
    config: AuthConfig,
    persistence: Optional["AuthPersistence"] = None,
) -> str:
    """Resolve the tenant a user's session works in.

    Precedence (first match wins):

    1. ``AuthConfig.tenant_id`` (``AUTH_TENANT_ID``) — pins the **whole
       deployment** to a single shared tenant. This is the classic
       single-tenant install: every user collaborates in one tenant.
    2. the user's **default tenant membership** (``auth_user_tenants``), when
       ``persistence`` is supplied and the user belongs to one or more tenants.
       This is the enterprise SaaS model: an admin provisions tenants and
       assigns users, so members of an org share that org's tenant.
    3. the ``user_id`` itself — each user gets an isolated **personal tenant**.
       The default for any user with no membership, so existing installs are
       unchanged ("every logged-in user works in their own tenant").

    Args:
        user_id: The authenticated user's identifier.
        config: The resolved auth configuration.
        persistence: Optional auth persistence; when given, membership is
            consulted (step 2). Omitting it preserves the pre-membership
            behaviour (steps 1 and 3 only) — no regression for callers that
            cannot supply it.

    Returns:
        The tenant id to embed in the user's access token.
    """
    pinned = (config.tenant_id or "").strip()
    if pinned:
        return pinned
    if persistence is not None:
        try:
            membership_tenant = persistence.resolve_default_tenant(user_id)
        except Exception:  # noqa: BLE001 — never block login on a tenancy read
            membership_tenant = None
        if membership_tenant:
            return membership_tenant
    return user_id
