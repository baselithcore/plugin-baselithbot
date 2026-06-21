"""Persistence for tenants and user→tenant membership.

Backs the enterprise multi-tenancy model: an admin provisions ``auth_tenants``
and assigns users via ``auth_user_tenants`` (with a per-tenant role and a single
default tenant per user). :func:`plugins.auth.tenancy.resolve_user_tenant` reads
:meth:`resolve_default_tenant` to stamp the access-token ``tenant_id`` claim.

All writes are tenant-scoped and degrade safely: a non-UUID actor (anonymous
sentinel) normalises to ``None`` instead of raising on a UUID column.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from psycopg.rows import dict_row

from core.db.connection import get_cursor
from core.observability.logging import get_logger

logger = get_logger(__name__)


def _as_uuid(value: Any) -> Optional[str]:
    """Return ``value`` as a canonical UUID string, or ``None`` if not a UUID."""
    try:
        return str(UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


class TenancyPersistenceMixin:
    """CRUD for tenants and user membership."""

    # ----- tenants --------------------------------------------------------

    def create_tenant(self, slug: str, name: str) -> Optional[Dict[str, Any]]:
        """Create a tenant. Returns the row, or ``None`` if the slug exists."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO auth_tenants (slug, name)
                VALUES (%s, %s)
                ON CONFLICT (slug) DO NOTHING
                RETURNING id, slug, name, status, created_at
                """,
                (slug, name),
            )
            return cur.fetchone()

    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a tenant by id."""
        tid = _as_uuid(tenant_id)
        if tid is None:
            return None
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, slug, name, status, created_at FROM auth_tenants "
                "WHERE id = %s",
                (tid,),
            )
            return cur.fetchone()

    def list_tenants(self) -> List[Dict[str, Any]]:
        """All tenants, with their member count, newest first."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT t.id, t.slug, t.name, t.status, t.created_at,
                       COUNT(ut.user_id) AS member_count
                FROM auth_tenants t
                LEFT JOIN auth_user_tenants ut ON ut.tenant_id = t.id
                GROUP BY t.id
                ORDER BY t.created_at DESC
                """
            )
            return list(cur.fetchall())

    def set_tenant_status(self, tenant_id: str, status: str) -> bool:
        """Activate or suspend a tenant. Returns whether a row changed."""
        tid = _as_uuid(tenant_id)
        if tid is None:
            return False
        with get_cursor() as cur:
            cur.execute(
                "UPDATE auth_tenants SET status = %s, updated_at = NOW() WHERE id = %s",
                (status, tid),
            )
            return cur.rowcount > 0

    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant (membership cascades). Returns whether it existed."""
        tid = _as_uuid(tenant_id)
        if tid is None:
            return False
        with get_cursor() as cur:
            cur.execute("DELETE FROM auth_tenants WHERE id = %s", (tid,))
            return cur.rowcount > 0

    # ----- membership -----------------------------------------------------

    def add_member(
        self,
        tenant_id: str,
        user_id: str,
        role: str = "member",
        added_by: Optional[str] = None,
    ) -> bool:
        """Add a user to a tenant. The user's FIRST membership becomes default.

        Idempotent: re-adding updates the role.
        """
        tid, uid = _as_uuid(tenant_id), _as_uuid(user_id)
        if tid is None or uid is None:
            return False
        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_user_tenants (user_id, tenant_id, role, is_default, added_by)
                VALUES (
                    %s, %s, %s,
                    NOT EXISTS (SELECT 1 FROM auth_user_tenants WHERE user_id = %s),
                    %s
                )
                ON CONFLICT (user_id, tenant_id) DO UPDATE SET role = EXCLUDED.role
                """,
                (uid, tid, role, uid, _as_uuid(added_by)),
            )
            return True

    def remove_member(self, tenant_id: str, user_id: str) -> bool:
        """Remove a user from a tenant. Promotes another membership to default
        if the removed one was the user's default."""
        tid, uid = _as_uuid(tenant_id), _as_uuid(user_id)
        if tid is None or uid is None:
            return False
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "DELETE FROM auth_user_tenants WHERE user_id = %s AND tenant_id = %s "
                "RETURNING is_default",
                (uid, tid),
            )
            row = cur.fetchone()
            if not row:
                return False
            if row["is_default"]:
                # Promote the oldest remaining membership to default.
                cur.execute(
                    """
                    UPDATE auth_user_tenants SET is_default = TRUE
                    WHERE user_id = %s AND tenant_id = (
                        SELECT tenant_id FROM auth_user_tenants
                        WHERE user_id = %s ORDER BY added_at LIMIT 1
                    )
                    """,
                    (uid, uid),
                )
            return True

    def list_members(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Users in a tenant, with their role, joined to user identity."""
        tid = _as_uuid(tenant_id)
        if tid is None:
            return []
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT ut.user_id, ut.role, ut.is_default, ut.added_at,
                       u.email, u.username
                FROM auth_user_tenants ut
                JOIN auth_users u ON u.id = ut.user_id
                WHERE ut.tenant_id = %s
                ORDER BY ut.added_at
                """,
                (tid,),
            )
            return list(cur.fetchall())

    def list_user_tenants(self, user_id: str) -> List[Dict[str, Any]]:
        """Tenants a user belongs to (for a tenant switcher)."""
        uid = _as_uuid(user_id)
        if uid is None:
            return []
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT t.id, t.slug, t.name, t.status, ut.role, ut.is_default
                FROM auth_user_tenants ut
                JOIN auth_tenants t ON t.id = ut.tenant_id
                WHERE ut.user_id = %s
                ORDER BY ut.is_default DESC, t.name
                """,
                (uid,),
            )
            return list(cur.fetchall())

    def is_member(self, user_id: str, tenant_id: str) -> bool:
        """Whether the user belongs to the tenant (and it is active)."""
        uid, tid = _as_uuid(user_id), _as_uuid(tenant_id)
        if uid is None or tid is None:
            return False
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT 1 FROM auth_user_tenants ut
                JOIN auth_tenants t ON t.id = ut.tenant_id
                WHERE ut.user_id = %s AND ut.tenant_id = %s AND t.status = 'active'
                """,
                (uid, tid),
            )
            return cur.fetchone() is not None

    def is_member_admin(self, user_id: str, tenant_id: str) -> bool:
        """Whether the user is a tenant-scoped **admin** of an active tenant.

        Drives the tenant-admin governance check: such a user manages members
        of *their own* tenant without holding platform-wide admin.
        """
        uid, tid = _as_uuid(user_id), _as_uuid(tenant_id)
        if uid is None or tid is None:
            return False
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT 1 FROM auth_user_tenants ut
                JOIN auth_tenants t ON t.id = ut.tenant_id
                WHERE ut.user_id = %s AND ut.tenant_id = %s
                  AND ut.role = 'admin' AND t.status = 'active'
                """,
                (uid, tid),
            )
            return cur.fetchone() is not None

    def resolve_default_tenant(self, user_id: str) -> Optional[str]:
        """The user's default tenant id, or ``None`` if they have no membership.

        Suspended tenants are ignored, so a user is never landed on a tenant
        that has been turned off.
        """
        uid = _as_uuid(user_id)
        if uid is None:
            return None
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT ut.tenant_id FROM auth_user_tenants ut
                JOIN auth_tenants t ON t.id = ut.tenant_id
                WHERE ut.user_id = %s AND t.status = 'active'
                ORDER BY ut.is_default DESC, ut.added_at
                LIMIT 1
                """,
                (uid,),
            )
            row = cur.fetchone()
            return str(row["tenant_id"]) if row else None

    def set_default_tenant(self, user_id: str, tenant_id: str) -> bool:
        """Set the user's active/default tenant (must be an existing membership).

        Atomic single-statement flip honours the one-default-per-user index.
        """
        uid, tid = _as_uuid(user_id), _as_uuid(tenant_id)
        if uid is None or tid is None:
            return False
        with get_cursor() as cur:
            cur.execute(
                """
                UPDATE auth_user_tenants
                SET is_default = (tenant_id = %s)
                WHERE user_id = %s
                """,
                (tid, uid),
            )
            return cur.rowcount > 0
