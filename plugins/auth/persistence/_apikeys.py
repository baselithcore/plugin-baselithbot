"""Personal access token / service API-key persistence.

Keys look like ``bsk_<prefix>_<secret>``. Only the SHA-256 hash of the full key
is stored; ``prefix`` is a short non-secret fragment for display and lookup.
"""

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from psycopg.rows import dict_row

from core.db.connection import get_connection, get_cursor
from core.observability.logging import get_logger

logger = get_logger(__name__)


def hash_api_key(raw: str) -> str:
    """SHA-256 of a raw API key."""
    return hashlib.sha256(raw.encode()).hexdigest()


class ApiKeyPersistenceMixin:
    """CRUD + validation for API keys."""

    def create_api_key(
        self,
        user_id: str,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
    ) -> Tuple[str, dict]:
        """Mint a new API key; returns ``(raw_key, record)``.

        The raw key is shown to the caller exactly once.
        """
        prefix = secrets.token_hex(4)  # 8 chars
        secret = secrets.token_urlsafe(32)
        raw = f"bsk_{prefix}_{secret}"
        key_id = str(uuid.uuid4())
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO auth_api_keys
                        (id, user_id, name, prefix, key_hash, scopes, expires_at, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, name, prefix, scopes, expires_at,
                              last_used_at, revoked_at, created_at
                    """,
                    (
                        key_id,
                        user_id,
                        name,
                        prefix,
                        hash_api_key(raw),
                        scopes or [],
                        expires_at,
                        created_by,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        logger.info("Issued API key %s for user %s", prefix, user_id)
        return raw, dict(row)

    def list_api_keys(self, user_id: Optional[str] = None) -> List[dict]:
        """List API keys, optionally scoped to one user."""
        with get_cursor(row_factory=dict_row) as cur:
            if user_id:
                cur.execute(
                    """
                    SELECT id, user_id, name, prefix, scopes, expires_at,
                           last_used_at, revoked_at, created_at
                    FROM auth_api_keys WHERE user_id = %s ORDER BY created_at DESC
                    """,
                    (user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, user_id, name, prefix, scopes, expires_at,
                           last_used_at, revoked_at, created_at
                    FROM auth_api_keys ORDER BY created_at DESC LIMIT 500
                    """
                )
            return [dict(r) for r in cur.fetchall()]

    def validate_api_key(self, raw: str) -> Optional[dict]:
        """Resolve a raw key to ``{user_id, scopes, id}`` if active."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, user_id, scopes FROM auth_api_keys
                WHERE key_hash = %s AND revoked_at IS NULL
                  AND (expires_at IS NULL OR expires_at > NOW())
                """,
                (hash_api_key(raw),),
            )
            row = cur.fetchone()
            if not row:
                return None
            self._touch_api_key(str(row["id"]))
            return dict(row)

    def _touch_api_key(self, key_id: str) -> None:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE auth_api_keys SET last_used_at = NOW() WHERE id = %s",
                        (key_id,),
                    )
                conn.commit()
        except Exception:  # pragma: no cover
            pass

    def revoke_api_key(self, key_id: str, user_id: Optional[str] = None) -> bool:
        """Revoke a key; if ``user_id`` given, scope to that owner (self-service)."""
        with get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        "UPDATE auth_api_keys SET revoked_at = NOW() "
                        "WHERE id = %s AND user_id = %s AND revoked_at IS NULL",
                        (key_id, user_id),
                    )
                else:
                    cur.execute(
                        "UPDATE auth_api_keys SET revoked_at = NOW() "
                        "WHERE id = %s AND revoked_at IS NULL",
                        (key_id,),
                    )
                ok = cur.rowcount > 0
            conn.commit()
        return ok
