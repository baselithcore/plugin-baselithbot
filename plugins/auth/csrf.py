"""
CSRF Protection Module.

Implements Double Submit Cookie pattern for CSRF protection.
Complements SameSite cookie policy with explicit token validation.

Reference: OWASP CSRF Prevention Cheat Sheet
"""

import hmac
from core.observability.logging import get_logger
import secrets
from typing import Optional

from fastapi import HTTPException, Request, status

from core.di.container import ServiceRegistry
from plugins.auth.config import AuthConfig

logger = get_logger(__name__)


class CSRFProtection:
    """
    CSRF token generation and validation.

    Uses Double Submit Cookie pattern:
    1. Generate random token on first request
    2. Store in cookie (httpOnly=False for JS access)
    3. Require token in header (X-CSRF-Token) for state-changing operations
    4. Validate token matches cookie
    """

    def __init__(self, cookie_name: str = "csrf_token") -> None:
        """
        Initialize CSRF protection.

        Args:
            cookie_name: Name of the CSRF cookie
        """
        self.cookie_name = cookie_name
        self.header_name = "X-CSRF-Token"

    def generate_token(self) -> str:
        """
        Generate a new CSRF token.

        Returns:
            URL-safe CSRF token
        """
        return secrets.token_urlsafe(32)

    def validate_token(
        self, request: Request, require_token: bool = True
    ) -> Optional[str]:
        """
        Validate CSRF token from request.

        Args:
            request: FastAPI request object
            require_token: If True, raise exception if token missing/invalid

        Returns:
            Validated token if present and valid, None otherwise

        Raises:
            HTTPException: If require_token=True and validation fails
        """
        # GET, HEAD, OPTIONS are safe methods - no CSRF check needed
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None

        # Get token from cookie
        cookie_token = request.cookies.get(self.cookie_name)

        # Get token from header
        header_token = request.headers.get(self.header_name)

        if not cookie_token or not header_token:
            if require_token:
                logger.warning(
                    f"CSRF validation failed: Missing token (cookie={bool(cookie_token)}, "
                    f"header={bool(header_token)})"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token missing",
                )
            return None

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(cookie_token, header_token):
            if require_token:
                logger.warning("CSRF validation failed: Token mismatch")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token invalid",
                )
            return None

        return cookie_token

    def set_csrf_cookie(self, response, token: Optional[str] = None) -> str:
        """
        Set CSRF token cookie in response.

        Args:
            response: FastAPI response object
            token: Optional existing token (generates new if None)

        Returns:
            The CSRF token that was set
        """
        if token is None:
            token = self.generate_token()

        config = ServiceRegistry.get(AuthConfig)

        response.set_cookie(
            key=self.cookie_name,
            value=token,
            httponly=False,  # Must be accessible to JavaScript
            secure=config.cookie_secure,
            samesite=config.cookie_samesite,
            max_age=config.session_lifetime,
            path="/",
        )

        return token


# Global instance
_csrf_protection: Optional[CSRFProtection] = None


def get_csrf_protection() -> CSRFProtection:
    """Get or create global CSRF protection instance."""
    global _csrf_protection
    if _csrf_protection is None:
        _csrf_protection = CSRFProtection()
    return _csrf_protection


def validate_csrf_token(request: Request) -> None:
    """
    Dependency to validate CSRF token.

    Usage:
        @router.post("/endpoint", dependencies=[Depends(validate_csrf_token)])
        async def endpoint():
            ...
    """
    csrf = get_csrf_protection()
    csrf.validate_token(request, require_token=True)
