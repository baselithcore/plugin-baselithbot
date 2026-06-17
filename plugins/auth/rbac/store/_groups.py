"""Persistence for groups, group membership, and group-role grants."""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from psycopg.rows import dict_row

from core.db.connection import get_connection, get_cursor
from core.observability.logging import get_logger

logger = get_logger(__name__)


class GroupStoreMixin:
    """CRUD for groups plus member and role management."""

    # ----- groups ---------------------------------------------------------

    def list_groups(self) -> List[Dict]:
        """All groups with member count and granted role slugs."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT g.id, g.slug, g.name, g.description, g.is_system,
                       COUNT(DISTINCT gm.user_id) AS member_count,
                       COALESCE(
                           ARRAY_AGG(DISTINCT r.slug)
                           FILTER (WHERE r.slug IS NOT NULL),
                           ARRAY[]::text[]
                       ) AS roles
                FROM auth_groups g
                LEFT JOIN auth_group_members gm ON gm.group_id = g.id
                LEFT JOIN auth_group_roles grr ON grr.group_id = g.id
                LEFT JOIN auth_roles r ON r.id = grr.role_id
                GROUP BY g.id
                ORDER BY g.is_system DESC, g.slug
                """
            )
            return [self._group_row(r) for r in cur.fetchall()]

    def get_group(self, group_id: str) -> Optional[Dict]:
        """Single group with member count and role slugs by id."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT g.id, g.slug, g.name, g.description, g.is_system,
                       COUNT(DISTINCT gm.user_id) AS member_count,
                       COALESCE(
                           ARRAY_AGG(DISTINCT r.slug)
                           FILTER (WHERE r.slug IS NOT NULL),
                           ARRAY[]::text[]
                       ) AS roles
                FROM auth_groups g
                LEFT JOIN auth_group_members gm ON gm.group_id = g.id
                LEFT JOIN auth_group_roles grr ON grr.group_id = g.id
                LEFT JOIN auth_roles r ON r.id = grr.role_id
                WHERE g.id = %s
                GROUP BY g.id
                """,
                (group_id,),
            )
            row = cur.fetchone()
            return self._group_row(row) if row else None

    def get_group_by_slug(self, slug: str) -> Optional[Dict]:
        """Fetch a group by its unique slug."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id FROM auth_groups WHERE slug = %s", (slug,))
            row = cur.fetchone()
            return self.get_group(str(row["id"])) if row else None

    def create_group(self, slug: str, name: str, description: str = "") -> Dict:
        """Create a custom group."""
        group_id = str(uuid.uuid4())
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO auth_groups (id, slug, name, description, is_system) "
                    "VALUES (%s, %s, %s, %s, FALSE)",
                    (group_id, slug, name, description),
                )
            conn.commit()
        return {
            "id": group_id,
            "slug": slug,
            "name": name,
            "description": description,
            "is_system": False,
            "member_count": 0,
            "roles": [],
        }

    def update_group(
        self, group_id: str, name: str, description: str
    ) -> Optional[Dict]:
        """Update a group's name/description."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_groups SET name = %s, description = %s, "
                    "updated_at = NOW() WHERE id = %s",
                    (name, description, group_id),
                )
            conn.commit()
        return self.get_group(group_id)

    def delete_group(self, group_id: str) -> bool:
        """Delete a custom group (system groups are protected)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_groups WHERE id = %s AND is_system = FALSE",
                    (group_id,),
                )
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    # ----- membership -----------------------------------------------------

    def add_member(
        self, group_id: str, user_id: str, added_by: Optional[str] = None
    ) -> None:
        """Add a user to a group (idempotent)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO auth_group_members (group_id, user_id, added_by) "
                    "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (group_id, user_id, added_by),
                )
            conn.commit()

    def remove_member(self, group_id: str, user_id: str) -> None:
        """Remove a user from a group."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_group_members "
                    "WHERE group_id = %s AND user_id = %s",
                    (group_id, user_id),
                )
            conn.commit()

    def list_members(self, group_id: str) -> List[Dict]:
        """Members of a group with basic identity fields."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT u.id, u.email, u.username
                FROM auth_group_members gm
                JOIN auth_users u ON u.id = gm.user_id
                WHERE gm.group_id = %s
                ORDER BY u.email
                """,
                (group_id,),
            )
            return [
                {"id": str(r["id"]), "email": r["email"], "username": r.get("username")}
                for r in cur.fetchall()
            ]

    def get_user_groups(self, user_id: str) -> List[Dict]:
        """Groups a user belongs to."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT g.id, g.slug, g.name
                FROM auth_group_members gm
                JOIN auth_groups g ON g.id = gm.group_id
                WHERE gm.user_id = %s
                ORDER BY g.slug
                """,
                (user_id,),
            )
            return [
                {"id": str(r["id"]), "slug": r["slug"], "name": r["name"]}
                for r in cur.fetchall()
            ]

    # ----- group -> role grants ------------------------------------------

    def assign_group_role(self, group_id: str, role_id: str) -> None:
        """Grant a role to a group (idempotent)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO auth_group_roles (group_id, role_id) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (group_id, role_id),
                )
            conn.commit()

    def revoke_group_role(self, group_id: str, role_id: str) -> None:
        """Remove a role grant from a group."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_group_roles WHERE group_id = %s AND role_id = %s",
                    (group_id, role_id),
                )
            conn.commit()

    # ----- helpers --------------------------------------------------------

    @staticmethod
    def _group_row(row: Dict) -> Dict:
        out = dict(row)
        out["id"] = str(out["id"])
        out["roles"] = list(out.get("roles") or [])
        out["member_count"] = int(out.get("member_count") or 0)
        return out
