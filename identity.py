"""Central-identity → dbview gateway-identity bridge.

The proxy router authenticates every request against the platform's central
``auth`` plugin (shared ``get_current_user`` chokepoint). This module maps the
resolved :class:`core.auth.types.AuthUser` to the trusted identity contract the
embedded dbview NestJS API consumes in gateway mode (see
``dbview/apps/api/src/auth/gateway.ts``):

* ``x-dbview-gateway-user``   — base64url JSON ``{id, email, displayName,
  role, tenantKey}``
* ``x-dbview-gateway-secret`` — per-boot shared secret owned by the supervisor

Conventions honoured (CLAUDE.md):

* **Admin is an effective privilege** — the dbview ``admin`` role is derived
  from :func:`plugins.auth.rbac.service.is_effective_admin` (wildcard-aware),
  falling back to the literal ``AuthRole.ADMIN`` check when the RBAC service
  is unavailable (degrade closed for elevation).
* **Tenancy is identity-derived** — the ``tenantKey`` comes from
  :func:`core.context.resolve_plugin_tenant_key` (honours the runtime
  admin override of the manifest mode), never from a client header.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Iterable

from core.auth.types import AuthRole, AuthUser
from core.context import resolve_plugin_tenant_key

logger = logging.getLogger(__name__)

PLUGIN_NAME = "dbview"
DECLARED_TENANCY = "shared"
TAB_ID = "dbview"

GATEWAY_USER_HEADER = "x-dbview-gateway-user"
GATEWAY_SECRET_HEADER = "x-dbview-gateway-secret"

# Effective-admin verdicts are cached briefly: the proxy sits on the hot path
# of every dbview request and the RBAC store is a database round-trip.
_ADMIN_CACHE_TTL_S = 30.0
_admin_cache: dict[str, tuple[float, bool]] = {}

# Central-directory profile lookups (email / display name) share the same
# hot-path concern; access tokens don't carry an email claim, so the profile
# comes from the auth plugin's user store.
_PROFILE_CACHE_TTL_S = 60.0
_profile_cache: dict[str, tuple[float, tuple[str | None, str | None]]] = {}


def _cache_key(user_id: str, roles: Iterable[AuthRole]) -> str:
    return f"{user_id}|{'|'.join(sorted(r.value for r in roles))}"


def is_effective_admin_cached(user: AuthUser) -> bool:
    """Wildcard-aware admin check with a short TTL cache.

    Falls back to the literal role when the central RBAC service cannot be
    reached (degrade closed: an outage never elevates a non-admin, it can only
    demote a wildcard-only admin to ``user`` for the cache window).
    """
    key = _cache_key(user.user_id, user.roles)
    now = time.monotonic()
    hit = _admin_cache.get(key)
    if hit is not None and now - hit[0] < _ADMIN_CACHE_TTL_S:
        return hit[1]
    try:
        from plugins.auth.rbac.service import is_effective_admin

        verdict = is_effective_admin(user.user_id, user.roles)
    except Exception:  # noqa: BLE001 — auth plugin absent / store down
        verdict = user.has_role(AuthRole.ADMIN)
    if len(_admin_cache) > 2048:  # unbounded-growth guard
        _admin_cache.clear()
    _admin_cache[key] = (now, verdict)
    return verdict


def can_access_dbview_tab(user: AuthUser) -> bool:
    """Central per-tab policy for the single ``dbview`` surface.

    Mirrors ``plugins.auth.dependencies.require_tab`` semantics (default-allow
    for unrestricted tabs). Fails open on RBAC outage — tab gating is
    visibility policy, not privilege elevation, and this matches the central
    ``PluginAccessMiddleware`` fail-open stance.
    """
    try:
        from plugins.auth.rbac.service import get_rbac_service

        return bool(
            get_rbac_service().can_access_tab(
                user.user_id, user.roles, PLUGIN_NAME, TAB_ID
            )
        )
    except Exception:  # noqa: BLE001
        return True


def lookup_central_profile(user_id: str) -> tuple[str | None, str | None]:
    """(email, display name) from the central auth user store, TTL-cached.

    Access tokens do not embed an email claim, so the mirror row would
    otherwise degrade to a placeholder address. Degrades to ``(None, None)``
    when the auth plugin / store is unavailable — never raises on the proxy
    hot path.
    """
    now = time.monotonic()
    hit = _profile_cache.get(user_id)
    if hit is not None and now - hit[0] < _PROFILE_CACHE_TTL_S:
        return hit[1]
    email: str | None = None
    name: str | None = None
    try:
        from plugins.auth.persistence import get_auth_persistence

        record = get_auth_persistence().get_user_by_id(user_id)
        if record is not None:
            email = record.email or None
            name = getattr(record, "username", None) or None
    except Exception:  # noqa: BLE001 — degrade to token-derived identity
        pass
    if len(_profile_cache) > 2048:  # unbounded-growth guard
        _profile_cache.clear()
    _profile_cache[user_id] = (now, (email, name))
    return email, name


def resolve_tenant_key() -> str:
    """Identity-derived tenancy scope key for dbview storage/sharing.

    Must be called with the request identity already bound to the context
    (the shared ``get_current_user`` dependency does that), so ``personal``
    mode resolves to the calling user, never to a stale default.
    """
    return resolve_plugin_tenant_key(PLUGIN_NAME, DECLARED_TENANCY)


def build_gateway_user_header(user: AuthUser) -> str:
    """Encode the forwarded identity as base64url JSON (no padding).

    The dbview side validates this against a Zod schema; ``email`` must be a
    syntactically valid address, so identities without one get a deterministic
    placeholder in a reserved domain.
    """
    profile_email, profile_name = lookup_central_profile(user.user_id)
    display_name = (
        user.metadata.get("display_name")
        or user.metadata.get("username")
        or user.metadata.get("name")
        or profile_name
    )
    # ``verify_token`` does not lift the email claim onto ``AuthUser.email``
    # (the raw payload lands in ``metadata``), and central access tokens don't
    # carry one anyway — prefer the directory profile, then token hints, then
    # a deterministic placeholder in a reserved domain (the dbview side
    # requires a syntactically valid address).
    email = user.email or user.metadata.get("email") or profile_email
    payload = {
        "id": user.user_id,
        "email": (
            email
            if isinstance(email, str) and email
            else f"{user.user_id}@users.central.local"
        ),
        "displayName": (
            display_name if isinstance(display_name, str) and display_name else None
        ),
        "role": "admin" if is_effective_admin_cached(user) else "user",
        "tenantKey": resolve_tenant_key(),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


__all__ = [
    "GATEWAY_SECRET_HEADER",
    "GATEWAY_USER_HEADER",
    "PLUGIN_NAME",
    "TAB_ID",
    "build_gateway_user_header",
    "can_access_dbview_tab",
    "is_effective_admin_cached",
    "lookup_central_profile",
    "resolve_tenant_key",
]
