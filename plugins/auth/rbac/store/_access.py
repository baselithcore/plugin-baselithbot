"""Effective-permission resolution, tab policy, and discovery seeding."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set
from uuid import UUID

from psycopg.rows import dict_row

from core.auth.types import AuthRole
from core.db.connection import get_connection, get_cursor
from core.observability.logging import get_logger
from plugins.auth.rbac.permissions import (
    BUILTIN_PERMISSIONS,
    PLUMBING_ROLE_SLUGS,
    SYSTEM_ROLE_DEFAULTS,
    WILDCARD,
    has_permission,
    tab_permission,
)

logger = get_logger(__name__)


class AccessStoreMixin:
    """Resolves effective permissions and enforces the per-tab access policy."""

    # ----- resolution -----------------------------------------------------

    def effective_permissions(
        self, user_id: str, system_roles: Iterable[AuthRole]
    ) -> Set[str]:
        """Union of all permission slugs granted to a user.

        Combines grants from the user's system roles (matched by slug to
        ``auth_users.roles[]``) and any custom roles in ``auth_user_roles``.
        """
        roles = list(system_roles)
        # The admin system role always resolves to the wildcard, even if the
        # RBAC tables were never seeded (fresh DB) or its grant was removed —
        # this guarantees an admin can never be locked out of the RBAC console.
        if AuthRole.ADMIN in roles:
            return {WILDCARD}
        role_slugs = [r.value for r in roles]
        # ``user_id`` columns are uuid; anonymous/unauthenticated callers carry
        # a sentinel ("anonymous") that Postgres can't cast. Normalise to NULL
        # so the user/group sub-selects simply match nothing — role-slug grants
        # (e.g. the anonymous role) still resolve.
        uid = self._as_uuid(user_id)
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT DISTINCT rp.permission_slug AS slug
                FROM auth_role_permissions rp
                JOIN auth_roles r ON r.id = rp.role_id
                WHERE r.slug = ANY(%s)
                   OR rp.role_id IN (
                        SELECT role_id FROM auth_user_roles WHERE user_id = %s
                   )
                   OR rp.role_id IN (
                        SELECT gr.role_id
                        FROM auth_group_roles gr
                        JOIN auth_group_members gm ON gm.group_id = gr.group_id
                        WHERE gm.user_id = %s
                   )
                """,
                (role_slugs, uid, uid),
            )
            return {row["slug"] for row in cur.fetchall()}

    @staticmethod
    def _as_uuid(user_id: str) -> Optional[str]:
        """Return ``user_id`` if it is a valid UUID, else ``None``.

        Anonymous callers carry a non-uuid sentinel; passing it straight to a
        uuid column raises ``invalid input syntax for type uuid`` in Postgres.
        """
        try:
            return str(UUID(str(user_id)))
        except (ValueError, AttributeError, TypeError):
            return None

    # ----- tab policy -----------------------------------------------------

    def list_tab_policies(self) -> List[Dict]:
        """All persisted tab policy rows."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT plugin, tab_id, label, restricted FROM auth_tab_policy "
                "ORDER BY plugin, tab_id"
            )
            return [dict(r) for r in cur.fetchall()]

    def get_tab_policy(self, plugin: str, tab_id: str) -> Optional[Dict]:
        """Single tab policy row, or None when the tab is unmanaged."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT plugin, tab_id, label, restricted FROM auth_tab_policy "
                "WHERE plugin = %s AND tab_id = %s",
                (plugin, tab_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def set_tab_restricted(self, plugin: str, tab_id: str, restricted: bool) -> None:
        """Toggle whether a tab requires its permission to access."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_tab_policy (plugin, tab_id, restricted)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (plugin, tab_id) DO UPDATE
                        SET restricted = EXCLUDED.restricted, updated_at = NOW()
                    """,
                    (plugin, tab_id, restricted),
                )
            conn.commit()

    def can_access_tab(
        self,
        user_id: str,
        system_roles: Iterable[AuthRole],
        plugin: str,
        tab_id: str,
    ) -> bool:
        """Default-allow: unmanaged/unrestricted tabs are open to everyone.

        A restricted tab requires the ``tab:<plugin>:<tab_id>`` permission
        (wildcard/admin always passes).
        """
        policy = self.get_tab_policy(plugin, tab_id)
        if not policy or not policy.get("restricted"):
            return True
        perms = self.effective_permissions(user_id, system_roles)
        return has_permission(perms, tab_permission(plugin, tab_id))

    # ----- seeding --------------------------------------------------------

    def seed_builtin(self) -> None:
        """Seed built-in permissions and system roles with default grants.

        Idempotent. Default grants are applied only when a system role is
        first created, so admin customisations are never clobbered.
        """
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                for slug, (desc, category) in BUILTIN_PERMISSIONS.items():
                    cur.execute(
                        "INSERT INTO auth_permissions (slug, description, category) "
                        "VALUES (%s, %s, %s) ON CONFLICT (slug) DO NOTHING",
                        (slug, desc, category),
                    )
                for role, defaults in SYSTEM_ROLE_DEFAULTS.items():
                    cur.execute(
                        """
                        INSERT INTO auth_roles (slug, name, is_system)
                        VALUES (%s, %s, TRUE)
                        ON CONFLICT (slug) DO NOTHING
                        RETURNING id
                        """,
                        (role.value, role.value.capitalize()),
                    )
                    created = cur.fetchone()
                    if created is None:
                        continue  # already existed -> keep admin's grants
                    for slug in defaults:
                        cur.execute(
                            "INSERT INTO auth_role_permissions "
                            "(role_id, permission_slug) VALUES (%s, %s) "
                            "ON CONFLICT DO NOTHING",
                            (created["id"], slug),
                        )
                # Prune internal plumbing roles so only business roles + custom
                # ones are ever surfaced in the admin console.
                cur.execute(
                    "DELETE FROM auth_roles WHERE is_system = TRUE AND slug = ANY(%s)",
                    (list(PLUMBING_ROLE_SLUGS),),
                )
            conn.commit()

    def register_tabs(self, tabs: List[Dict[str, str]]) -> None:
        """Register discovered plugin tabs.

        Ensures a permission exists for each tab and a (default-allow) policy
        row is present. Existing ``restricted`` flags are preserved; only the
        label is refreshed.
        """
        if not tabs:
            return
        with get_connection() as conn:
            with conn.cursor() as cur:
                for tab in tabs:
                    plugin = tab["plugin"]
                    tab_id = tab["tab_id"]
                    label = tab.get("label", tab_id)
                    cur.execute(
                        "INSERT INTO auth_permissions (slug, description, category) "
                        "VALUES (%s, %s, 'tab') ON CONFLICT (slug) DO NOTHING",
                        (tab_permission(plugin, tab_id), f"Access tab '{label}'"),
                    )
                    cur.execute(
                        """
                        INSERT INTO auth_tab_policy (plugin, tab_id, label)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (plugin, tab_id) DO UPDATE
                            SET label = EXCLUDED.label
                        """,
                        (plugin, tab_id, label),
                    )
            conn.commit()
