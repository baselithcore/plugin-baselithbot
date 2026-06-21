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

from plugins.auth.config import AuthConfig


def resolve_user_tenant(user_id: str, config: AuthConfig) -> str:
    """Resolve the tenant a user's session works in.

    Precedence (first match wins):

    1. ``AuthConfig.tenant_id`` (``AUTH_TENANT_ID``) — pins the **whole
       deployment** to a single shared tenant. This is the classic
       single-tenant install: every user collaborates in one tenant.
    2. the ``user_id`` itself — each user gets an isolated **personal tenant**.
       This is the default ("every logged-in user works in their own tenant")
       and applies whenever no deployment-wide tenant is configured.

    Args:
        user_id: The authenticated user's identifier.
        config: The resolved auth configuration.

    Returns:
        The tenant id to embed in the user's access token.
    """
    pinned = (config.tenant_id or "").strip()
    if pinned:
        return pinned
    return user_id
