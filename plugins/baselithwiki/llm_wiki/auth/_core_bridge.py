"""Bridge: central platform ``auth`` plugin → baselithwiki engine identity.

baselithwiki originally shipped its **own** JWT / login / RBAC stack. The
plugin now delegates *all* identity to the ecosystem ``auth`` plugin: the
React SPA authenticates through the shared ``@auth`` context, sends the
central access token as ``Authorization: Bearer <token>``, and this module
turns that token into the user-dict + tenant the vendored engine expects —
so every existing router keeps working unchanged behind the seam.

Why a sync decoder
==================
``core.auth.jwt.JWTHandler.verify_token`` is async (it does a Redis blacklist
round-trip). The wiki engine is sync-first (handlers run in the threadpool),
so we verify the token's signature + expiry synchronously here, mirroring the
central handler minus the blacklist hop — access tokens are short-lived and
the wiki already sits behind the central ``PluginAccessMiddleware``.

Tenancy (per user request 2026-06-21)
=====================================
The wiki's knowledge base (filesystem + Qdrant collection) is **shared
globally**; only private data (conversations, memories, feedback) is isolated,
and there the engine's native invariant is **1 tenant = 1 user**. So the wiki
tenant == the authenticated ``user_id`` — each user owns a personal workspace.
This honours both the engine's 1:1 ``users↔tenants`` schema and the platform's
identity-derived tenancy. JIT-provisioning mirrors a ``tenants`` + ``users``
row per central identity so existing FK constraints + RLS keep working.
"""

from __future__ import annotations

import logging
from typing import Any

import jwt

from core.auth.types import AuthRole
from core.config.security import get_security_config
from llm_wiki.auth.permissions import ALL_PERMISSIONS, Permission

logger = logging.getLogger(__name__)

# Permissions a normal authenticated user receives inside the wiki: read the
# shared KB, chat, and full control over their OWN private data + the UI
# surfaces. Elevated perms (ingest, wiki-write, admin.*, rbac.*, feedback
# read/triage/delete) require effective-admin OR an explicit central RBAC grant
# of the matching slug — see :func:`build_user_dict`.
DEFAULT_USER_PERMS: frozenset[str] = frozenset(
    {
        Permission.WIKI_READ,
        Permission.CHAT_USE,
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_WRITE,
        Permission.CONVERSATION_DELETE,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
        Permission.MEMORY_DELETE,
        Permission.FEEDBACK_WRITE,
        Permission.GRAPH_READ,
        Permission.OBSIDIAN_OPEN,
        Permission.VIEW_SETTINGS,
        Permission.VIEW_HELP,
        Permission.VIEW_COMMAND_PALETTE,
        Permission.VIEW_SOURCES,
        Permission.VIEW_STATUS,
        Permission.VIEW_EDITIONS,
    }
)

# Provisioned identities cached per-process so the idempotent mirror upsert
# only touches the DB once per user per worker.
_provisioned: set[str] = set()


def _decoder_params() -> tuple[str, str, dict[str, Any]]:
    """Resolve secret / algorithm / iss-aud from the SAME config the central
    auth manager mints tokens with (``core.config.security``)."""
    cfg = get_security_config()
    secret_raw = cfg.secret_key
    secret = (
        secret_raw.get_secret_value()
        if hasattr(secret_raw, "get_secret_value")
        else str(secret_raw or "")
    )
    algorithm = getattr(cfg, "jwt_algorithm", None) or "HS256"
    opts: dict[str, Any] = {}
    issuer = getattr(cfg, "jwt_issuer", None)
    audience = getattr(cfg, "jwt_audience", None)
    if issuer:
        opts["issuer"] = issuer
    if audience:
        opts["audience"] = audience
    return secret, algorithm, opts


def decode_core_token(token: str | None) -> dict[str, Any] | None:
    """Verify a central access token (signature + exp) and return its claims.

    Returns ``None`` when the token is absent / invalid / expired.
    """
    if not token:
        return None
    secret, algorithm, opts = _decoder_params()
    if not secret:
        logger.warning("[wiki-auth] SECRET_KEY not configured — cannot verify token")
        return None
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"require": ["exp"]},
            **opts,
        )
    except jwt.InvalidTokenError as exc:
        logger.debug("[wiki-auth] core token rejected: %s", exc)
        return None


def _role_enums(roles: list[str]) -> set[AuthRole]:
    out: set[AuthRole] = set()
    for r in roles:
        try:
            out.add(AuthRole(r))
        except ValueError:
            continue
    return out


def _effective_central_perms(user_id: str, roles: list[str]) -> set[str]:
    """Resolved central RBAC permission slugs for the user (empty on failure)."""
    try:
        from plugins.auth.rbac.service import get_rbac_service

        return set(
            get_rbac_service().effective_permissions(user_id, _role_enums(roles))
        )
    except Exception as exc:  # noqa: BLE001 — RBAC optional; degrade gracefully
        logger.debug("[wiki-auth] central perms lookup failed: %s", exc)
        return set()


def _is_effective_admin(roles: list[str], central: set[str]) -> bool:
    """Admin is an *effective* privilege, mirroring the central gates: literal
    ``admin`` role OR the wildcard permission (custom RBAC admin). Falls back to
    the literal role when the RBAC service is unavailable (degrade closed)."""
    if AuthRole.ADMIN.value in roles:
        return True
    try:
        from plugins.auth.rbac.permissions import WILDCARD, has_permission

        return has_permission(central, WILDCARD)
    except Exception:  # noqa: BLE001
        return False


def build_user_dict(claims: dict[str, Any]) -> dict[str, Any]:
    """Map verified central JWT claims → the engine's user-dict contract.

    Admin ⇒ every wiki permission. Normal user ⇒ the default interactive set
    plus any central RBAC grant whose slug matches a wiki permission (lets a
    platform admin hand out e.g. ``ingest.run`` centrally with no wiki RBAC).
    """
    user_id = str(claims.get("sub") or claims.get("uid") or "")
    roles = [str(r) for r in (claims.get("roles") or ["user"])]
    central = _effective_central_perms(user_id, roles)
    admin = _is_effective_admin(roles, central)
    if admin:
        perms: set[str] = set(ALL_PERMISSIONS)
    else:
        perms = set(DEFAULT_USER_PERMS) | (central & ALL_PERMISSIONS)
    email = str(claims.get("email") or f"{user_id}@core.local")
    return {
        "id": user_id,
        "email": email,
        "display_name": str(claims.get("name") or email.split("@", 1)[0]),
        # 1 tenant = 1 user: the wiki workspace is the authenticated identity.
        "tenant_id": user_id,
        "role": "admin" if admin else "user",
        "is_active": True,
        "perms": sorted(perms),
        "roles": roles,
        "domains": [],
        "active_domain": None,
        "_token_role": claims.get("role"),
        # Central auth owns credentials; the wiki never forces a password change.
        "password_must_change": False,
    }


def ensure_mirror_rows(user: dict[str, Any]) -> None:
    """Idempotently mirror a ``tenants`` + ``users`` row for a central identity.

    The vendored engine's private-data tables FK to ``tenants(id)`` and RLS
    filters on ``app.current_tenant_id``. Central identities have no native wiki
    row, so on first authenticated request we upsert a 1:1 tenant+user mirror
    (id == tenant_id == user_id). Cached per-process. Best-effort: a failure
    logs and is retried on the next request rather than breaking the call.
    """
    uid = user.get("id")
    if not uid or uid in _provisioned:
        return
    try:
        from llm_wiki.db.connection import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO tenants (id, name, slug) VALUES (%s, %s, %s) "
                    "ON CONFLICT (id) DO NOTHING",
                    (uid, user["email"], f"u-{uid}"),
                )
                cur.execute(
                    "INSERT INTO users (id, email, password_hash, display_name, "
                    "tenant_id, role) VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (id) DO UPDATE SET "
                    "role = EXCLUDED.role, is_active = TRUE",
                    (
                        uid,
                        user["email"],
                        "external:core-auth",
                        user["display_name"],
                        uid,
                        user["role"],
                    ),
                )
            conn.commit()
        _provisioned.add(uid)
    except Exception as exc:  # noqa: BLE001 — never break the request on mirror
        logger.warning("[wiki-auth] mirror provisioning failed for %s: %s", uid, exc)


__all__ = [
    "DEFAULT_USER_PERMS",
    "decode_core_token",
    "build_user_dict",
    "ensure_mirror_rows",
]
