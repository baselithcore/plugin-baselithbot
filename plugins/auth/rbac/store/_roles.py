"""Persistence for permissions, roles, role-permission and user-role grants."""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from psycopg.rows import dict_row

from core.db.connection import get_connection, get_cursor
from core.observability.logging import get_logger
from plugins.auth.rbac.permissions import WILDCARD

logger = get_logger(__name__)


class RoleStoreMixin:
    """CRUD for the permission catalog, roles, and grant tables."""

    # ----- permissions ----------------------------------------------------

    def ensure_permission(
        self, slug: str, description: str = "", category: str = "general"
    ) -> None:
        """Upsert a single permission (idempotent)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_permissions (slug, description, category)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE
                        SET description = EXCLUDED.description,
                            category = EXCLUDED.category
                    """,
                    (slug, description, category),
                )
            conn.commit()

    def list_permissions(self) -> List[Dict]:
        """All known permissions ordered by category then slug."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT slug, description, category FROM auth_permissions "
                "ORDER BY category, slug"
            )
            return [dict(r) for r in cur.fetchall()]

    # ----- roles ----------------------------------------------------------

    def list_roles(self) -> List[Dict]:
        """All roles with their granted permission slugs."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT r.id, r.slug, r.name, r.description, r.is_system,
                       COALESCE(
                           ARRAY_AGG(rp.permission_slug)
                           FILTER (WHERE rp.permission_slug IS NOT NULL),
                           ARRAY[]::text[]
                       ) AS permissions
                FROM auth_roles r
                LEFT JOIN auth_role_permissions rp ON rp.role_id = r.id
                GROUP BY r.id
                ORDER BY r.is_system DESC, r.slug
                """
            )
            return [self._role_row(r) for r in cur.fetchall()]

    def get_role_by_slug(self, slug: str) -> Optional[Dict]:
        """Fetch a single role by its unique slug."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id FROM auth_roles WHERE slug = %s", (slug,))
            row = cur.fetchone()
            return self.get_role(str(row["id"])) if row else None

    def get_role(self, role_id: str) -> Optional[Dict]:
        """Fetch a single role with permissions by id."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT r.id, r.slug, r.name, r.description, r.is_system,
                       COALESCE(
                           ARRAY_AGG(rp.permission_slug)
                           FILTER (WHERE rp.permission_slug IS NOT NULL),
                           ARRAY[]::text[]
                       ) AS permissions
                FROM auth_roles r
                LEFT JOIN auth_role_permissions rp ON rp.role_id = r.id
                WHERE r.id = %s
                GROUP BY r.id
                """,
                (role_id,),
            )
            row = cur.fetchone()
            return self._role_row(row) if row else None

    def create_role(self, slug: str, name: str, description: str = "") -> Dict:
        """Create a custom (non-system) role."""
        role_id = str(uuid.uuid4())
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO auth_roles (id, slug, name, description, is_system)
                    VALUES (%s, %s, %s, %s, FALSE)
                    RETURNING id, slug, name, description, is_system
                    """,
                    (role_id, slug, name, description),
                )
                row = cur.fetchone()
            conn.commit()
        result = dict(row)
        result["permissions"] = []
        return result

    def update_role(self, role_id: str, name: str, description: str) -> Optional[Dict]:
        """Update mutable fields of a role (slug/is_system immutable)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_roles SET name = %s, description = %s, "
                    "updated_at = NOW() WHERE id = %s",
                    (name, description, role_id),
                )
            conn.commit()
        return self.get_role(role_id)

    def delete_role(self, role_id: str) -> bool:
        """Delete a custom role. System roles are protected (returns False)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_roles WHERE id = %s AND is_system = FALSE",
                    (role_id,),
                )
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    # ----- role -> permission grants -------------------------------------

    def _is_admin_role(self, role_id: str) -> bool:
        """True when role_id is the protected system admin role."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT slug, is_system FROM auth_roles WHERE id = %s", (role_id,)
            )
            row = cur.fetchone()
            return bool(row and row["is_system"] and row["slug"] == "admin")

    def set_role_permissions(self, role_id: str, slugs: List[str]) -> None:
        """Replace the full set of permissions granted to a role.

        The system admin role always keeps the wildcard (self-lockout guard).
        """
        if self._is_admin_role(role_id) and WILDCARD not in slugs:
            slugs = [*slugs, WILDCARD]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_role_permissions WHERE role_id = %s",
                    (role_id,),
                )
                for slug in slugs:
                    cur.execute(
                        "INSERT INTO auth_permissions (slug) VALUES (%s) "
                        "ON CONFLICT (slug) DO NOTHING",
                        (slug,),
                    )
                    cur.execute(
                        "INSERT INTO auth_role_permissions (role_id, permission_slug) "
                        "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (role_id, slug),
                    )
            conn.commit()

    def grant_permission(self, role_id: str, slug: str) -> None:
        """Add a single permission grant to a role (idempotent)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO auth_permissions (slug) VALUES (%s) "
                    "ON CONFLICT (slug) DO NOTHING",
                    (slug,),
                )
                cur.execute(
                    "INSERT INTO auth_role_permissions (role_id, permission_slug) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (role_id, slug),
                )
            conn.commit()

    def revoke_permission(self, role_id: str, slug: str) -> None:
        """Remove a single permission grant from a role.

        Revoking the wildcard from the system admin role is refused to prevent
        self-lockout.
        """
        if slug == WILDCARD and self._is_admin_role(role_id):
            return
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_role_permissions "
                    "WHERE role_id = %s AND permission_slug = %s",
                    (role_id, slug),
                )
            conn.commit()

    # ----- user -> role assignments --------------------------------------

    def assign_user_role(
        self, user_id: str, role_id: str, granted_by: Optional[str] = None
    ) -> None:
        """Assign a custom role to a user (idempotent)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO auth_user_roles (user_id, role_id, granted_by) "
                    "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (user_id, role_id, granted_by),
                )
            conn.commit()

    def revoke_user_role(self, user_id: str, role_id: str) -> None:
        """Remove a custom-role assignment from a user."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_user_roles WHERE user_id = %s AND role_id = %s",
                    (user_id, role_id),
                )
            conn.commit()

    def get_user_roles(self, user_id: str) -> List[Dict]:
        """Custom roles assigned to a user (system roles live on the user row)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT r.id, r.slug, r.name, r.description, r.is_system
                FROM auth_user_roles ur
                JOIN auth_roles r ON r.id = ur.role_id
                WHERE ur.user_id = %s
                ORDER BY r.slug
                """,
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    # ----- helpers --------------------------------------------------------

    @staticmethod
    def _role_row(row: Dict) -> Dict:
        out = dict(row)
        out["id"] = str(out["id"])
        out["permissions"] = list(out.get("permissions") or [])
        return out
