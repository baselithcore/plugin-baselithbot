"""
Auth Plugin Security Utilities.

Provides security hardening functions:
- Rate limiting
- Constant-time comparisons
- Secure token storage
- Security headers
"""

import hashlib
import hmac
from core.observability.logging import get_logger
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional


logger = get_logger(__name__)


# =============================================================================
# Secure Token Storage (with TTL cleanup)
# =============================================================================


class SecureTokenStore:
    """Short-lived store for MFA challenge tokens (login temp tokens and
    forced-enrollment tokens).

    Primary backend is Postgres (table ``auth_mfa_challenges``) so a challenge
    minted on one uvicorn worker can be verified on another. The previous
    in-memory-only store silently broke MFA whenever ``WEB_CONCURRENCY > 1``:
    the verify request usually landed on a different worker than the login that
    minted the token, so ``get()`` missed and the user saw "Invalid or expired
    temporary token". An in-memory dict is kept as a fast path and as the sole
    backend when no database pool is initialized (unit tests / DB-less dev),
    where a single process makes that safe.

    DB access is best-effort: a failure degrades to the in-memory entry instead
    of turning a transient hiccup into a login-blocking 500.
    """

    def __init__(self) -> None:
        self._tokens: Dict[str, Dict] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Every minute

    def _cleanup(self) -> None:
        """Remove expired tokens from the in-memory tier."""
        now = datetime.now(timezone.utc)
        if time.time() - self._last_cleanup < self._cleanup_interval:
            return

        expired = [
            token
            for token, data in self._tokens.items()
            if data.get("expires_at", now) < now
        ]

        for token in expired:
            del self._tokens[token]

        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired MFA tokens")

        self._last_cleanup = time.time()

    # -- shared (cross-worker) Postgres tier -------------------------------
    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _db_available() -> bool:
        """True only once the core Postgres pool is initialized (i.e. the app
        runs with a DB). Keeps DB-less unit tests on the in-memory path without
        ever attempting a connection."""
        try:
            from core.db import connection

            return connection._POOL is not None
        except Exception:
            return False

    def _db_store(self, token: str, data: Dict, expires_at: datetime) -> None:
        if not self._db_available():
            return
        try:
            from core.db.connection import get_connection
            from psycopg.types.json import Json

            purpose = "enroll" if "secret" in data else "login"
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO auth_mfa_challenges
                            (token_hash, user_id, purpose, data, expires_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (token_hash) DO UPDATE
                            SET data = EXCLUDED.data, expires_at = EXCLUDED.expires_at
                        """,
                        (
                            self._hash(token),
                            data.get("user_id"),
                            purpose,
                            Json(data),
                            expires_at,
                        ),
                    )
                conn.commit()
        except Exception as exc:  # pragma: no cover - best-effort shared tier
            logger.debug("MFA challenge DB store skipped: %s", exc)

    def _db_get(self, token: str) -> Optional[Dict]:
        if not self._db_available():
            return None
        try:
            from core.db.connection import get_cursor
            from psycopg.rows import dict_row

            with get_cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT data FROM auth_mfa_challenges
                    WHERE token_hash = %s AND expires_at > NOW()
                    """,
                    (self._hash(token),),
                )
                row = cur.fetchone()
                return dict(row["data"]) if row else None
        except Exception as exc:  # pragma: no cover - best-effort shared tier
            logger.debug("MFA challenge DB get skipped: %s", exc)
            return None

    def _db_delete(self, token: str) -> None:
        if not self._db_available():
            return
        try:
            from core.db.connection import get_connection

            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM auth_mfa_challenges WHERE token_hash = %s",
                        (self._hash(token),),
                    )
                conn.commit()
        except Exception as exc:  # pragma: no cover - best-effort shared tier
            logger.debug("MFA challenge DB delete skipped: %s", exc)

    # -- public API (in-memory fast path + shared tier) --------------------
    def store(
        self,
        token: str,
        data: Dict,
        ttl_seconds: int = 300,  # 5 minutes
    ) -> None:
        """Store a challenge token with expiration in both tiers."""
        self._cleanup()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        self._tokens[token] = {**data, "expires_at": expires_at}
        self._db_store(token, data, expires_at)

    def get(self, token: str) -> Optional[Dict]:
        """Get token data if valid (in-memory first, then the shared tier)."""
        self._cleanup()
        data = self._tokens.get(token)

        if data is not None:
            if data.get("expires_at", datetime.now(timezone.utc)) < datetime.now(
                timezone.utc
            ):
                del self._tokens[token]
                self._db_delete(token)
                return None
            return data

        # In-memory miss (e.g. another worker minted it) -> shared tier.
        return self._db_get(token)

    def delete(self, token: str) -> bool:
        """Delete a token from both tiers."""
        existed = self._tokens.pop(token, None) is not None
        self._db_delete(token)
        return existed

    def register_failure(self, token: str, max_attempts: int = 5) -> bool:
        """Count a failed challenge attempt; burn the token past ``max_attempts``.

        Returns True when the token is now invalid (deleted) and the caller must
        force a fresh login. This bounds MFA/TOTP brute force to a handful of
        guesses per 5-minute challenge instead of the full ~10^6 code space that
        an IP-only rate limit (bypassable via header spoofing) allowed. The
        bumped counter is persisted in both tiers, preserving the original TTL.
        """
        data = self.get(token)
        if data is None:
            return True
        attempts = int(data.get("attempts", 0)) + 1
        if attempts >= max_attempts:
            self.delete(token)
            return True
        exp = data.get("expires_at")
        now = datetime.now(timezone.utc)
        ttl = (
            max(1, int((exp - now).total_seconds()))
            if isinstance(exp, datetime)
            else 120
        )
        payload = {k: v for k, v in data.items() if k != "expires_at"}
        payload["attempts"] = attempts
        self.store(token, payload, ttl_seconds=ttl)
        return False

    def size(self) -> int:
        """Get current number of in-memory tokens."""
        self._cleanup()
        return len(self._tokens)


# Global MFA token store
mfa_token_store = SecureTokenStore()


# =============================================================================
# Constant-Time Comparisons
# =============================================================================


def secure_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.

    Always compares in constant time regardless of where strings differ.
    """
    return hmac.compare_digest(a.encode(), b.encode())


def secure_hash_compare(value: str, expected_hash: str) -> bool:
    """
    Hash value and compare to expected hash in constant time.
    """
    value_hash = hashlib.sha256(value.encode()).hexdigest()
    return hmac.compare_digest(value_hash, expected_hash)


# =============================================================================
# Security Headers
# =============================================================================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store, no-cache, must-revalidate, private",
    "Pragma": "no-cache",
}


def add_security_headers(response) -> None:
    """Add security headers to response."""
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value


# =============================================================================
# Input Sanitization
# =============================================================================


def sanitize_email(email: str) -> str:
    """Sanitize email input."""
    # Lowercase and strip whitespace
    email = email.lower().strip()

    # Remove any null bytes or control characters
    email = "".join(c for c in email if c.isprintable())

    # Limit length
    return email[:255]


def sanitize_log_input(value: str, max_length: int = 100) -> str:
    """
    Sanitize input for logging to prevent log injection.

    Removes newlines, tabs, and limits length.
    """
    if not value:
        return ""

    # Remove control characters
    sanitized = "".join(c for c in value if c.isprintable() and c not in "\n\r\t")

    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


# =============================================================================
# Token Generation
# =============================================================================


def generate_secure_token(prefix: str = "", length: int = 32) -> str:
    """
    Generate a cryptographically secure token.

    Args:
        prefix: Optional prefix for token type identification
        length: Number of random bytes (token will be longer due to encoding)

    Returns:
        URL-safe base64 encoded token
    """
    token = secrets.token_urlsafe(length)
    if prefix:
        return f"{prefix}_{token}"
    return token
