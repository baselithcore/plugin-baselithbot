"""Cross-worker challenge store for WebAuthn registration/authentication.

The previous in-process ``dict`` on the ``WebAuthnManager`` singleton silently
broke passkeys under ``WEB_CONCURRENCY > 1`` (the verify request usually landed
on a different worker than the one that minted the challenge) and never expired
abandoned challenges — the same class of bug already fixed for MFA. This mirrors
:class:`plugins.auth.security.SecureTokenStore`: a Postgres tier (table
``auth_webauthn_challenges``) shared across workers plus an in-memory fast path
used alone when no DB pool exists (tests / DB-less dev). Challenges are
single-use — :meth:`take` pops from both tiers — and expire via a server-side
TTL, so a failed or abandoned attempt cannot be retried indefinitely.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from core.observability.logging import get_logger

logger = get_logger(__name__)


class WebAuthnChallengeStore:
    """In-memory fast path + shared Postgres tier for WebAuthn challenges."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._mem: Dict[str, Tuple[bytes, datetime]] = {}

    @staticmethod
    def _db_available() -> bool:
        try:
            from core.db import connection

            return connection._POOL is not None
        except Exception:
            return False

    @staticmethod
    def _key(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    def put(self, key: str, challenge: bytes) -> None:
        """Store a challenge under ``key`` with the configured TTL (both tiers)."""
        expires = datetime.now(timezone.utc) + timedelta(seconds=self._ttl)
        self._mem[key] = (challenge, expires)
        if not self._db_available():
            return
        try:
            from core.db.connection import get_connection

            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO auth_webauthn_challenges
                            (challenge_key, challenge, expires_at)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (challenge_key) DO UPDATE
                            SET challenge = EXCLUDED.challenge,
                                expires_at = EXCLUDED.expires_at
                        """,
                        (self._key(key), challenge, expires),
                    )
                conn.commit()
        except Exception as exc:  # pragma: no cover - best-effort shared tier
            logger.debug("WebAuthn challenge DB store skipped: %s", exc)

    def take(self, key: str) -> Optional[bytes]:
        """Pop the challenge for ``key`` (single-use); None if missing/expired."""
        now = datetime.now(timezone.utc)
        entry = self._mem.pop(key, None)
        mem_val = entry[0] if (entry and entry[1] > now) else None
        db_val = self._db_take(key) if self._db_available() else None
        return mem_val or db_val

    def _db_take(self, key: str) -> Optional[bytes]:
        try:
            from core.db.connection import get_connection
            from psycopg.rows import dict_row

            with get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        """
                        DELETE FROM auth_webauthn_challenges
                        WHERE challenge_key = %s AND expires_at > NOW()
                        RETURNING challenge
                        """,
                        (self._key(key),),
                    )
                    row = cur.fetchone()
                conn.commit()
            if not row:
                return None
            value = row["challenge"]
            return bytes(value) if value is not None else None
        except Exception as exc:  # pragma: no cover - best-effort shared tier
            logger.debug("WebAuthn challenge DB take skipped: %s", exc)
            return None


_store: Optional[WebAuthnChallengeStore] = None


def get_webauthn_challenge_store() -> WebAuthnChallengeStore:
    """Get or create the global WebAuthn challenge store."""
    global _store
    if _store is None:
        _store = WebAuthnChallengeStore()
    return _store


__all__ = ["WebAuthnChallengeStore", "get_webauthn_challenge_store"]
