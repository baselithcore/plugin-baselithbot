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
    """
    In-memory token store with automatic expiration.

    For production with multiple instances, replace with Redis.
    """

    def __init__(self) -> None:
        self._tokens: Dict[str, Dict] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Every minute

    def _cleanup(self) -> None:
        """Remove expired tokens."""
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

    def store(
        self,
        token: str,
        data: Dict,
        ttl_seconds: int = 300,  # 5 minutes
    ) -> None:
        """Store token with expiration."""
        self._cleanup()
        self._tokens[token] = {
            **data,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        }

    def get(self, token: str) -> Optional[Dict]:
        """Get token data if valid."""
        self._cleanup()
        data = self._tokens.get(token)

        if not data:
            return None

        if data.get("expires_at", datetime.min) < datetime.now(timezone.utc):
            del self._tokens[token]
            return None

        return data

    def delete(self, token: str) -> bool:
        """Delete a token."""
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False

    def size(self) -> int:
        """Get current number of stored tokens."""
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
