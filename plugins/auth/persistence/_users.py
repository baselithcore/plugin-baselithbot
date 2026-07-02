"""User CRUD, session listing, and login-tracking persistence."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set

from psycopg.rows import dict_row

from core.auth.types import AuthRole
from core.db.connection import get_connection, get_cursor
from core.observability.logging import get_logger
from plugins.auth.models import RefreshToken, User
from plugins.auth.persistence._helpers import row_to_user, serialize_roles

logger = get_logger(__name__)


class UserPersistenceMixin:
    """User records, active sessions, and login tracking."""

    # ==========================================================================
    # User CRUD
    # ==========================================================================

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM auth_users WHERE email = %s",
                (email.lower(),),
            )
            row = cur.fetchone()
            return row_to_user(row) if row else None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM auth_users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return row_to_user(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (case-insensitive)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM auth_users WHERE LOWER(username) = LOWER(%s)",
                (username,),
            )
            row = cur.fetchone()
            return row_to_user(row) if row else None

    def get_user_by_identifier(self, identifier: str) -> Optional[User]:
        """
        Get user by identifier (username OR email).

        Tries both username and email lookup.
        Uses case-insensitive comparison for both.

        Args:
            identifier: Username or email

        Returns:
            User if found, None otherwise
        """
        with get_cursor(row_factory=dict_row) as cur:
            # Try both username and email in a single query
            cur.execute(
                """
                SELECT * FROM auth_users
                WHERE LOWER(username) = LOWER(%s) OR LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (identifier, identifier),
            )
            row = cur.fetchone()
            return row_to_user(row) if row else None

    def create_user(
        self,
        email: str,
        password_hash: str,
        username: Optional[str] = None,
        roles: Optional[Set[AuthRole]] = None,
        allowed_tabs: Optional[List[str]] = None,
    ) -> User:
        """Create a new user."""
        user_id = str(uuid.uuid4())
        roles = roles or {AuthRole.USER}
        now = datetime.now(timezone.utc)

        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO auth_users
                        (id, username, email, password_hash, roles, allowed_tabs, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        user_id,
                        username,
                        email.lower(),
                        password_hash,
                        serialize_roles(roles),
                        allowed_tabs,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            conn.commit()

        logger.info(
            f"Created user: {email} (username: {username}) with roles: {[r.value for r in roles]}"
        )
        return row_to_user(row)

    def update_user(self, user: User) -> User:
        """Update an existing user."""
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE auth_users SET
                        username = %s,
                        email = %s,
                        password_hash = %s,
                        roles = %s,
                        mfa_secret = %s,
                        mfa_enabled = %s,
                        is_active = %s,
                        allowed_tabs = %s,
                        last_login = %s,
                        failed_login_attempts = %s,
                        locked_until = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        user.username,
                        user.email.lower(),
                        user.password_hash,
                        serialize_roles(user.roles),
                        user.mfa_secret,
                        user.mfa_enabled,
                        user.is_active,
                        user.allowed_tabs,
                        user.last_login,
                        user.failed_login_attempts,
                        user.locked_until,
                        user.id,
                    ),
                )
                row = cur.fetchone()
            conn.commit()

        return row_to_user(row) if row else user

    def consume_totp_step(self, user_id: str, step: int) -> bool:
        """Atomically record an accepted TOTP time-step; reject replays.

        Returns True when ``step`` is newer than the last accepted step (and
        stores it), False when it was already used (a replay). Degrades **open**
        when no DB pool is initialized (single-process dev/tests) so it never
        blocks a legitimate login there — cross-worker replay defense only
        matters once a shared Postgres backend exists.
        """
        from core.db import connection

        if connection._POOL is None:
            return True
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_users SET mfa_last_totp_step = %s
                    WHERE id = %s
                      AND (mfa_last_totp_step IS NULL OR mfa_last_totp_step < %s)
                    """,
                    (step, user_id, step),
                )
                consumed = cur.rowcount > 0
            conn.commit()
        return consumed

    def update_password_hash(self, user_id: str, password_hash: str) -> None:
        """Persist a new password hash only (e.g. transparent rehash-on-login)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_users SET password_hash = %s, updated_at = NOW() "
                    "WHERE id = %s",
                    (password_hash, user_id),
                )
            conn.commit()

    def delete_user(self, user_id: str) -> bool:
        """Delete a user by ID."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_users WHERE id = %s",
                    (user_id,),
                )
                deleted = cur.rowcount > 0
            conn.commit()

        if deleted:
            logger.info(f"Deleted user: {user_id}")
        return deleted

    def count_active_admins(self) -> int:
        """Number of active users holding the admin system role."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM auth_users "
                "WHERE is_active = TRUE AND 'admin' = ANY(roles)"
            )
            row = cur.fetchone()
            return int(row["n"]) if row else 0

    def count_users(self) -> int:
        """Total number of user rows (active or not).

        Drives first-run setup detection: an empty table ⇒ show the wizard.
        """
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT COUNT(*) AS n FROM auth_users")
            row = cur.fetchone()
            return int(row["n"]) if row else 0

    def list_users(self, include_inactive: bool = False) -> List[User]:
        """List all users."""
        with get_cursor(row_factory=dict_row) as cur:
            if include_inactive:
                cur.execute("SELECT * FROM auth_users ORDER BY created_at DESC")
            else:
                cur.execute(
                    "SELECT * FROM auth_users WHERE is_active = TRUE ORDER BY created_at DESC"
                )
            rows = cur.fetchall()
            return [row_to_user(row) for row in rows]

    def list_users_paginated(
        self,
        page: int = 1,
        limit: int = 20,
        include_inactive: bool = False,
        search: Optional[str] = None,
    ) -> tuple[List[User], int]:
        """
        List users with pagination and optional search.

        Args:
            page: Page number (1-indexed)
            limit: Users per page
            include_inactive: Include disabled users
            search: Search term for email

        Returns:
            Tuple of (users, total_count)
        """
        conditions = []
        params: list = []

        if not include_inactive:
            conditions.append("is_active = TRUE")

        if search:
            conditions.append("email ILIKE %s")
            params.append(f"%{search}%")

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        with get_cursor(row_factory=dict_row) as cur:
            # Get total count
            cur.execute(
                f"SELECT COUNT(*) as count FROM auth_users WHERE {where_clause}",  # nosec B608
                params,
            )
            row = cur.fetchone()
            total = row["count"] if row else 0

            # Get paginated users
            offset = (page - 1) * limit
            cur.execute(
                f"""
                SELECT * FROM auth_users
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,  # nosec B608
                params + [limit, offset],
            )
            rows = cur.fetchall()

        return [row_to_user(row) for row in rows], total

    def unlock_user(self, user_id: str) -> bool:
        """
        Unlock a locked user account.

        Args:
            user_id: User ID to unlock

        Returns:
            True if user was unlocked, False if not found
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_users SET
                        failed_login_attempts = 0,
                        locked_until = NULL
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                updated = cur.rowcount > 0
            conn.commit()

        if updated:
            logger.info(f"Unlocked user: {user_id}")
        return updated

    # ==========================================================================
    # Sessions
    # ==========================================================================

    def get_active_sessions(self, user_id: Optional[str] = None) -> List[RefreshToken]:
        """
        Get active (non-expired, non-revoked) refresh tokens.

        Args:
            user_id: Optional filter by user

        Returns:
            List of active RefreshToken objects
        """
        with get_cursor(row_factory=dict_row) as cur:
            if user_id:
                cur.execute(
                    """
                    SELECT rt.*, u.email as user_email
                    FROM auth_refresh_tokens rt
                    JOIN auth_users u ON u.id = rt.user_id
                    WHERE rt.user_id = %s
                      AND rt.revoked_at IS NULL
                      AND rt.expires_at > NOW()
                    ORDER BY rt.created_at DESC
                    """,
                    (user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT rt.*, u.email as user_email
                    FROM auth_refresh_tokens rt
                    JOIN auth_users u ON u.id = rt.user_id
                    WHERE rt.revoked_at IS NULL
                      AND rt.expires_at > NOW()
                    ORDER BY rt.created_at DESC
                    """
                )
            rows = cur.fetchall()

        result = []
        for row in rows:
            token = RefreshToken(
                id=str(row["id"]),
                user_id=str(row["user_id"]),
                token_hash=row["token_hash"],
                expires_at=row["expires_at"],
                revoked_at=row.get("revoked_at"),
                created_at=row.get("created_at", datetime.now(timezone.utc)),
            )
            # Attach email for display purposes
            token.user_email = row.get("user_email")  # type: ignore
            result.append(token)

        return result

    def count_active_sessions(self, user_id: Optional[str] = None) -> int:
        """Count active sessions, optionally filtered by user."""
        with get_cursor() as cur:
            if user_id:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM auth_refresh_tokens
                    WHERE user_id = %s
                      AND revoked_at IS NULL
                      AND expires_at > NOW()
                    """,
                    (user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM auth_refresh_tokens
                    WHERE revoked_at IS NULL
                      AND expires_at > NOW()
                    """
                )
            row = cur.fetchone()
            return row[0] if row else 0

    # ==========================================================================
    # Login Tracking
    # ==========================================================================

    def record_login_success(self, user_id: str) -> None:
        """Record successful login."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_users SET
                        last_login = NOW(),
                        failed_login_attempts = 0,
                        locked_until = NULL
                    WHERE id = %s
                    """,
                    (user_id,),
                )
            conn.commit()

    def record_login_failure(self, user_id: str) -> int:
        """
        Record failed login attempt.

        Returns:
            New count of failed attempts
        """
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE auth_users SET
                        failed_login_attempts = failed_login_attempts + 1
                    WHERE id = %s
                    RETURNING failed_login_attempts
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                attempts = row["failed_login_attempts"] if row else 0

                # Check if lockout threshold reached
                if attempts >= self._config.max_login_attempts:
                    lockout_until = datetime.now(timezone.utc) + timedelta(
                        minutes=self._config.lockout_duration_minutes
                    )
                    cur.execute(
                        "UPDATE auth_users SET locked_until = %s WHERE id = %s",
                        (lockout_until, user_id),
                    )
                    logger.warning(
                        f"User {user_id} locked until {lockout_until} after {attempts} failed attempts"
                    )

            conn.commit()

        return attempts
