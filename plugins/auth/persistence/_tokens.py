"""Refresh-token and MFA backup-code persistence."""

import hashlib
import uuid
from datetime import datetime
from typing import List, Optional

from psycopg.rows import dict_row

from core.db.connection import get_connection, get_cursor
from core.observability.logging import get_logger
from plugins.auth.models import RefreshToken

logger = get_logger(__name__)


class TokenPersistenceMixin:
    """Refresh tokens and MFA backup codes."""

    # ==========================================================================
    # Refresh Tokens
    # ==========================================================================

    def store_refresh_token(
        self, user_id: str, token: str, expires_at: datetime
    ) -> RefreshToken:
        """Store a refresh token."""
        token_id = str(uuid.uuid4())
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_refresh_tokens (id, user_id, token_hash, expires_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (token_id, user_id, token_hash, expires_at),
                )
            conn.commit()

        return RefreshToken(
            id=token_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    def validate_refresh_token(self, token: str) -> Optional[str]:
        """
        Validate a refresh token.

        Returns:
            User ID if valid, None otherwise
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT user_id FROM auth_refresh_tokens
                WHERE token_hash = %s
                  AND revoked_at IS NULL
                  AND expires_at > NOW()
                """,
                (token_hash,),
            )
            row = cur.fetchone()
            return str(row["user_id"]) if row else None

    def revoke_refresh_token(self, token: str) -> bool:
        """Revoke a refresh token (logout)."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_refresh_tokens SET revoked_at = NOW()
                    WHERE token_hash = %s AND revoked_at IS NULL
                    """,
                    (token_hash,),
                )
                revoked = cur.rowcount > 0
            conn.commit()

        return revoked

    def revoke_session_by_id(self, user_id: str, session_id: str) -> bool:
        """Revoke a single refresh-token session owned by a user (self-service)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_refresh_tokens SET revoked_at = NOW()
                    WHERE id = %s AND user_id = %s AND revoked_at IS NULL
                    """,
                    (session_id, user_id),
                )
                ok = cur.rowcount > 0
            conn.commit()
        return ok

    def revoke_other_user_tokens(self, user_id: str, keep_token: str) -> int:
        """Revoke all of a user's sessions except the one matching keep_token."""
        keep_hash = hashlib.sha256(keep_token.encode()).hexdigest()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_refresh_tokens SET revoked_at = NOW()
                    WHERE user_id = %s AND revoked_at IS NULL AND token_hash <> %s
                    """,
                    (user_id, keep_hash),
                )
                count = cur.rowcount
            conn.commit()
        return count

    def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all refresh tokens for a user."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_refresh_tokens SET revoked_at = NOW()
                    WHERE user_id = %s AND revoked_at IS NULL
                    """,
                    (user_id,),
                )
                count = cur.rowcount
            conn.commit()

        logger.info(f"Revoked {count} refresh tokens for user {user_id}")
        return count

    # ==========================================================================
    # MFA Backup Codes
    # ==========================================================================

    def store_backup_codes(self, user_id: str, code_hashes: List[str]) -> None:
        """Store MFA backup codes for a user."""
        # First, delete any existing unused codes
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM auth_mfa_backup_codes WHERE user_id = %s AND used_at IS NULL",
                    (user_id,),
                )

                # Insert new codes
                for code_hash in code_hashes:
                    cur.execute(
                        """
                        INSERT INTO auth_mfa_backup_codes (id, user_id, code_hash)
                        VALUES (%s, %s, %s)
                        """,
                        (str(uuid.uuid4()), user_id, code_hash),
                    )
            conn.commit()

        logger.info(f"Stored {len(code_hashes)} backup codes for user {user_id}")

    def use_backup_code(self, user_id: str, code_hash: str) -> bool:
        """
        Mark a backup code as used.

        Returns:
            True if code was valid and marked, False otherwise
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_mfa_backup_codes SET used_at = NOW()
                    WHERE user_id = %s AND code_hash = %s AND used_at IS NULL
                    """,
                    (user_id, code_hash),
                )
                used = cur.rowcount > 0
            conn.commit()

        return used

    def get_unused_backup_codes_count(self, user_id: str) -> int:
        """Get count of remaining unused backup codes."""
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM auth_mfa_backup_codes
                WHERE user_id = %s AND used_at IS NULL
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else 0
