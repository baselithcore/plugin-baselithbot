"""Permission catalog — single source of truth lato Python.

DEVE restare in sync con il seed in
``alembic/versions/007_rbac.py:SEED_PERMISSIONS``.

Convenzione naming: ``resource.action`` (singolare). Aggiungere un
permesso nuovo richiede:

1. Costante in :class:`Permission` (qui).
2. Riga corrispondente in ``SEED_PERMISSIONS`` della migration.
3. Migration di update (008+) che fa l'INSERT idempotent + grant ai
   ruoli system rilevanti.

Le funzioni helper (:func:`has_permission`, :func:`has_any`,
:func:`has_all`) leggono da ``user["perms"]`` — popolato dal lookup
DB in :func:`llm_wiki.auth.dependencies._resolve_user`. Niente cache
TTL: il refresh token scaduto forza re-login → permessi rinfrescati.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Final


class Permission:
    """Stringhe permesso. Usare costanti, non literal."""

    # Wiki content
    WIKI_READ: Final = "wiki.read"
    WIKI_WRITE: Final = "wiki.write"
    WIKI_DELETE: Final = "wiki.delete"

    # Chat / RAG
    CHAT_USE: Final = "chat.use"

    # Ingest
    INGEST_RUN: Final = "ingest.run"
    INGEST_DELETE: Final = "ingest.delete"

    # Conversations
    CONVERSATION_READ: Final = "conversation.read"
    CONVERSATION_WRITE: Final = "conversation.write"
    CONVERSATION_DELETE: Final = "conversation.delete"

    # Feedback
    FEEDBACK_WRITE: Final = "feedback.write"
    FEEDBACK_READ: Final = "feedback.read"
    FEEDBACK_DELETE: Final = "feedback.delete"
    # Workflow triage (status, tag, note) — non distruttivo, separato
    # da delete. Granted moderator+admin via mig 018.
    FEEDBACK_TRIAGE: Final = "feedback.triage"

    # Memories
    MEMORY_READ: Final = "memory.read"
    MEMORY_WRITE: Final = "memory.write"
    MEMORY_DELETE: Final = "memory.delete"

    # Admin
    ADMIN_SCAFFOLD: Final = "admin.scaffold"
    ADMIN_TENANT_MANAGE: Final = "admin.tenant.manage"
    ADMIN_USER_MANAGE: Final = "admin.user.manage"
    ADMIN_GROUP_MANAGE: Final = "admin.group.manage"
    ADMIN_RUNTIME: Final = "admin.runtime"
    ADMIN_AUDIT_READ: Final = "admin.audit.read"
    ADMIN_EMBED_MANAGE: Final = "admin.embed.manage"

    # Obsidian integration (mig 012).
    OBSIDIAN_OPEN: Final = "obsidian.open"

    # Knowledge graph (mig 013).
    GRAPH_READ: Final = "graph.read"

    # UI surface visibility (mig 014). Per-tab/modal gating per role-based
    # show/hide nella home. Pattern Notion/Linear/GitHub: ogni superficie
    # UI che non ha già un permesso CRUD naturale ottiene un ``view.*``
    # dedicato così l'admin può comporre profili stretti (es. "kiosk"
    # user che vede solo chat senza settings/help/sources).
    VIEW_SETTINGS: Final = "view.settings"
    VIEW_HELP: Final = "view.help"
    VIEW_COMMAND_PALETTE: Final = "view.command_palette"
    VIEW_SOURCES: Final = "view.sources"
    VIEW_STATUS: Final = "view.status"
    VIEW_EDITIONS: Final = "view.editions"

    # Role assignment scoping (gerarchia 008).
    # Nessuno è concedibile *via UI* per superuser: il primo nasce dal
    # bootstrap admin, gli ulteriori vanno fatti via DB.
    RBAC_ASSIGN_SUPERUSER: Final = "rbac.assign.superuser"
    RBAC_ASSIGN_ADMIN: Final = "rbac.assign.admin"
    RBAC_ASSIGN_MODERATOR: Final = "rbac.assign.moderator"
    RBAC_ASSIGN_USER: Final = "rbac.assign.user"


ALL_PERMISSIONS: Final[frozenset[str]] = frozenset(
    {
        Permission.WIKI_READ,
        Permission.WIKI_WRITE,
        Permission.WIKI_DELETE,
        Permission.CHAT_USE,
        Permission.INGEST_RUN,
        Permission.INGEST_DELETE,
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_WRITE,
        Permission.CONVERSATION_DELETE,
        Permission.FEEDBACK_WRITE,
        Permission.FEEDBACK_READ,
        Permission.FEEDBACK_DELETE,
        Permission.FEEDBACK_TRIAGE,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
        Permission.MEMORY_DELETE,
        Permission.ADMIN_SCAFFOLD,
        Permission.ADMIN_TENANT_MANAGE,
        Permission.ADMIN_USER_MANAGE,
        Permission.ADMIN_GROUP_MANAGE,
        Permission.ADMIN_RUNTIME,
        Permission.ADMIN_AUDIT_READ,
        Permission.ADMIN_EMBED_MANAGE,
        Permission.OBSIDIAN_OPEN,
        Permission.GRAPH_READ,
        Permission.VIEW_SETTINGS,
        Permission.VIEW_HELP,
        Permission.VIEW_COMMAND_PALETTE,
        Permission.VIEW_SOURCES,
        Permission.VIEW_STATUS,
        Permission.VIEW_EDITIONS,
        Permission.RBAC_ASSIGN_SUPERUSER,
        Permission.RBAC_ASSIGN_ADMIN,
        Permission.RBAC_ASSIGN_MODERATOR,
        Permission.RBAC_ASSIGN_USER,
    }
)


# Slug ruoli system — match con seed migration 008.
class SystemRole:
    SUPERUSER: Final = "superuser"
    ADMIN: Final = "admin"
    MODERATOR: Final = "moderator"
    USER: Final = "user"


# Mappa: ruolo target → permesso necessario per nominarlo.
# Usato in :mod:`llm_wiki.api.routers.rbac.assign_role` per l'enforcement.
ROLE_ASSIGN_PERMISSION: Final[dict[str, str]] = {
    SystemRole.SUPERUSER: Permission.RBAC_ASSIGN_SUPERUSER,
    SystemRole.ADMIN: Permission.RBAC_ASSIGN_ADMIN,
    SystemRole.MODERATOR: Permission.RBAC_ASSIGN_MODERATOR,
    SystemRole.USER: Permission.RBAC_ASSIGN_USER,
}


def _user_perms(user: dict[str, Any] | None) -> frozenset[str]:
    if not user:
        return frozenset()
    perms = user.get("perms")
    if not perms:
        return frozenset()
    return frozenset(perms)


def has_permission(user: dict[str, Any] | None, perm: str) -> bool:
    """True se ``user`` possiede ``perm``."""
    return perm in _user_perms(user)


def has_any(user: dict[str, Any] | None, perms: Iterable[str]) -> bool:
    """True se possiede almeno uno dei permessi richiesti."""
    user_perms = _user_perms(user)
    return any(p in user_perms for p in perms)


def has_all(user: dict[str, Any] | None, perms: Iterable[str]) -> bool:
    """True se possiede tutti i permessi richiesti."""
    user_perms = _user_perms(user)
    return all(p in user_perms for p in perms)


__all__ = [
    "Permission",
    "SystemRole",
    "ALL_PERMISSIONS",
    "ROLE_ASSIGN_PERMISSION",
    "has_permission",
    "has_any",
    "has_all",
]
