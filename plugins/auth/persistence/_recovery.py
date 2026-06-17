"""Persistence for single-use recovery tokens and admin invitations.

Tokens are random secrets; only their SHA-256 hash is stored. ``purpose``
discriminates password reset, email verification, and invite-acceptance flows.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from psycopg.rows import dict_row

from core.db.connection import get_connection, get_cursor
from core.observability.logging import get_logger

logger = get_logger(__name__)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RecoveryPersistenceMixin:
    """Recovery tokens (reset/verify) and invitations."""

    # ---- Recovery tokens (password reset, email verification) -------------

    def create_recovery_token(
        self, user_id: str, purpose: str, ttl_minutes: int = 60
    ) -> str:
        """Create a single-use recovery token, returning the raw secret."""
        raw = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_recovery_tokens
                        (id, user_id, token_hash, purpose, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (str(uuid.uuid4()), user_id, _hash(raw), purpose, expires_at),
                )
            conn.commit()
        return raw

    def consume_recovery_token(self, token: str, purpose: str) -> Optional[str]:
        """Validate and mark a recovery token used; return its user_id."""
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE auth_recovery_tokens SET used_at = NOW()
                    WHERE token_hash = %s AND purpose = %s
                      AND used_at IS NULL AND expires_at > NOW()
                    RETURNING user_id
                    """,
                    (_hash(token), purpose),
                )
                row = cur.fetchone()
            conn.commit()
        return str(row["user_id"]) if row else None

    def invalidate_recovery_tokens(self, user_id: str, purpose: str) -> int:
        """Burn all outstanding tokens of a purpose for a user."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_recovery_tokens SET used_at = NOW()
                    WHERE user_id = %s AND purpose = %s AND used_at IS NULL
                    """,
                    (user_id, purpose),
                )
                count = cur.rowcount
            conn.commit()
        return count

    # ---- Invitations -------------------------------------------------------

    def create_invitation(
        self,
        email: str,
        roles: List[str],
        invited_by: Optional[str],
        ttl_days: int = 7,
    ) -> str:
        """Create an invitation, returning the raw acceptance token."""
        raw = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_invitations
                        (id, email, roles, token_hash, invited_by, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        email.lower(),
                        roles,
                        _hash(raw),
                        invited_by,
                        expires_at,
                    ),
                )
            conn.commit()
        logger.info("Created invitation for %s", email)
        return raw

    def get_invitation(self, token: str) -> Optional[dict]:
        """Return a pending (unexpired, unaccepted) invitation by token."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, email, roles, expires_at FROM auth_invitations
                WHERE token_hash = %s AND accepted_at IS NULL AND expires_at > NOW()
                """,
                (_hash(token),),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def accept_invitation(self, token: str) -> Optional[dict]:
        """Mark an invitation accepted; return its email + roles."""
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE auth_invitations SET accepted_at = NOW()
                    WHERE token_hash = %s AND accepted_at IS NULL AND expires_at > NOW()
                    RETURNING email, roles
                    """,
                    (_hash(token),),
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row) if row else None

    def list_invitations(self, include_accepted: bool = False) -> List[dict]:
        """List invitations (pending by default)."""
        clause = "" if include_accepted else "WHERE accepted_at IS NULL"
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT id, email, roles, invited_by, expires_at, accepted_at, created_at
                FROM auth_invitations {clause}
                ORDER BY created_at DESC LIMIT 200
                """
            )
            return [dict(r) for r in cur.fetchall()]

    def revoke_invitation(self, invitation_id: str) -> bool:
        """Delete a pending invitation."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_invitations WHERE id = %s AND accepted_at IS NULL",
                    (invitation_id,),
                )
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    # ---- User lifecycle helpers (status / verification / password age) -----

    def set_email_verified(self, user_id: str, verified: bool = True) -> None:
        """Mark a user's email as verified."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_users SET email_verified = %s WHERE id = %s",
                    (verified, user_id),
                )
            conn.commit()

    def set_user_status(self, user_id: str, status: str) -> None:
        """Set lifecycle status and mirror to is_active for compat."""
        active = status == "active"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_users SET status = %s, is_active = %s WHERE id = %s",
                    (status, active, user_id),
                )
            conn.commit()

    def touch_password_changed(self, user_id: str) -> None:
        """Record the time of a password change."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_users SET password_changed_at = NOW() WHERE id = %s",
                    (user_id,),
                )
            conn.commit()

    def update_profile(
        self, user_id: str, full_name: Optional[str], username: Optional[str]
    ) -> None:
        """Update self-service profile fields."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_users SET full_name = %s, username = %s WHERE id = %s",
                    (full_name, username, user_id),
                )
            conn.commit()
