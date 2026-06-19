"""Persistence for the MFA enforcement policy.

Mandatory two-factor can be required at three levels — globally, per group, or
per user — stored on ``auth_security_policy`` (singleton), ``auth_groups``, and
``auth_users`` respectively. :meth:`is_mfa_required` collapses all three into a
single effective answer for the login flow.
"""

from __future__ import annotations

from psycopg.rows import dict_row

from core.db.connection import get_cursor
from core.observability.logging import get_logger

logger = get_logger(__name__)


class SecurityPolicyMixin:
    """Read/write the org-wide, group, and per-user MFA requirement."""

    # ----- global toggle --------------------------------------------------

    def get_mfa_required_all(self) -> bool:
        """Whether MFA is mandatory for every user (org-wide toggle)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT mfa_required_all FROM auth_security_policy WHERE id = 1"
            )
            row = cur.fetchone()
            return bool(row["mfa_required_all"]) if row else False

    def set_mfa_required_all(self, value: bool) -> None:
        """Set the org-wide MFA requirement (upserts the singleton row)."""
        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_security_policy (id, mfa_required_all, updated_at)
                VALUES (1, %s, NOW())
                ON CONFLICT (id)
                DO UPDATE SET mfa_required_all = EXCLUDED.mfa_required_all,
                              updated_at = NOW()
                """,
                (value,),
            )

    # ----- per-user / per-group flags ------------------------------------

    def set_user_mfa_required(self, user_id: str, value: bool) -> None:
        """Set the per-user MFA requirement flag."""
        with get_cursor() as cur:
            cur.execute(
                "UPDATE auth_users SET mfa_required = %s, updated_at = NOW() "
                "WHERE id = %s",
                (value, user_id),
            )

    def get_user_mfa_required(self, user_id: str) -> bool:
        """The per-user MFA requirement flag (not the effective requirement)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT mfa_required FROM auth_users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return bool(row["mfa_required"]) if row else False

    def set_group_mfa_required(self, group_id: str, value: bool) -> None:
        """Set the per-group MFA requirement flag."""
        with get_cursor() as cur:
            cur.execute(
                "UPDATE auth_groups SET mfa_required = %s, updated_at = NOW() "
                "WHERE id = %s",
                (value, group_id),
            )

    # ----- effective requirement -----------------------------------------

    def is_mfa_required(self, user_id: str) -> bool:
        """Effective MFA requirement for a user: global OR user OR any group.

        A single query so the login hot-path stays cheap.
        """
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(
                        (SELECT mfa_required_all FROM auth_security_policy WHERE id = 1),
                        FALSE
                    ) AS global_req,
                    COALESCE(u.mfa_required, FALSE) AS user_req,
                    EXISTS (
                        SELECT 1
                        FROM auth_group_members gm
                        JOIN auth_groups g ON g.id = gm.group_id
                        WHERE gm.user_id = %s AND g.mfa_required
                    ) AS group_req
                FROM auth_users u
                WHERE u.id = %s
                """,
                (user_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return False
            return bool(row["global_req"] or row["user_req"] or row["group_req"])


__all__ = ["SecurityPolicyMixin"]
