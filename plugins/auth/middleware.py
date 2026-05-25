"""
Auth Plugin - Middleware.

Provides global authentication middleware for FastAPI.
"""

from core.observability.logging import get_logger
from typing import Callable, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.di.container import ServiceRegistry
from core.auth import AuthRole, AuthUser, AuthManager
from plugins.auth.config import AuthConfig
from plugins.auth.persistence import AuthPersistence

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Global authentication middleware.

    Extracts JWT from Authorization header or refresh_token cookie,
    validates the token, and attaches AuthUser to request.state.
    """

    def __init__(
        self,
        app: ASGIApp,
        public_paths: Optional[List[str]] = None,
    ) -> None:
        super().__init__(app)
        self._config = ServiceRegistry.get(AuthConfig)
        self._public_paths = public_paths or self._config.public_paths

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and attach user to state."""
        # Always allow OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check if path is public
        path = request.url.path
        if self._is_public_path(path):
            request.state.user = AuthUser(
                user_id="anonymous", roles={AuthRole.ANONYMOUS}
            )
            return await call_next(request)

        # Try to authenticate
        user = await self._authenticate(request)
        request.state.user = user

        # If auth is required and user is not authenticated, return 401
        if self._config.auth_required and not user.is_authenticated:
            # Allow the request to proceed - dependencies will handle 401
            # This allows fine-grained control in route handlers
            pass

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is in public paths list."""
        for public_path in self._public_paths:
            if path.startswith(public_path):
                return True
            # Exact match
            if path == public_path:
                return True
        # Static files are always public
        if path.startswith("/static/") or path.startswith("/assets/"):
            return True
        return False

    async def _authenticate(self, request: Request) -> AuthUser:
        """Authenticate request from header or cookie."""
        auth_manager = ServiceRegistry.get(AuthManager)

        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header:
            user = await auth_manager.authenticate(auth_header)
            if user.is_authenticated:
                return user

        # Fallback to refresh_token cookie
        refresh_token = request.cookies.get(self._config.cookie_name)
        if refresh_token:
            persistence = ServiceRegistry.get(AuthPersistence)
            user_id = persistence.validate_refresh_token(refresh_token)
            if user_id:
                db_user = persistence.get_user_by_id(user_id)
                if db_user and db_user.is_active and not db_user.is_locked():
                    return AuthUser(
                        user_id=db_user.id,
                        email=db_user.email,
                        roles=db_user.roles,
                        metadata={"allowed_tabs": db_user.allowed_tabs},
                    )

        # No valid auth
        return AuthUser(user_id="anonymous", roles={AuthRole.ANONYMOUS})


def get_auth_middleware(app: ASGIApp) -> AuthMiddleware:
    """Factory function to create auth middleware."""
    return AuthMiddleware(app)
