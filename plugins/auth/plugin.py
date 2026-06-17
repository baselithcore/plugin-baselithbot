"""
Auth Plugin - Main Entry Point.

Professional authentication system with email/password login,
MFA (TOTP), and role-based access control.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from core.di.container import ServiceRegistry
from core.plugins import RouterPlugin
from core.observability.logging import get_logger
from core.auth.manager import AuthManager, get_auth_manager
from plugins.auth.admin_router import admin_router
from plugins.auth.audit import AuditLogger, get_audit_logger
from plugins.auth.config import AuthConfig, get_auth_config
from plugins.auth.middleware import AuthMiddleware
from plugins.auth.persistence import AuthPersistence, get_auth_persistence
from plugins.auth.rbac import RBACService, get_rbac_service
from plugins.auth.rbac_router import rbac_admin_router, rbac_me_router
from plugins.auth.router import router as auth_router

logger = get_logger(__name__)


class AuthPlugin(RouterPlugin):
    """
    Authentication Plugin.

    Provides:
    - Email/password login
    - MFA with TOTP
    - Role-based access control (admin, user, guest, job)
    - HttpOnly cookie refresh tokens
    - Account lockout protection
    """

    def __init__(self) -> None:
        super().__init__()
        self._config: Optional[AuthConfig] = None

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the auth plugin and register services in DI."""
        if self.is_initialized():
            return

        await super().initialize(config or {})

        self._config = get_auth_config()
        ServiceRegistry.register(AuthConfig, self._config)

        logger.info(
            f"Initializing Auth Plugin (auth_required={self._config.auth_required}, "
            f"session_lifetime={self._config.session_lifetime}, "
            f"mfa_enabled={self._config.mfa_enabled})"
        )

        # Initialize persistence and register in DI
        try:
            persistence = get_auth_persistence()
            persistence.create_tables()
            ServiceRegistry.register(AuthPersistence, persistence)
            logger.info("Auth database persistence registered in DI")
            # Seed the initial admin (idempotent; no-op unless configured).
            from plugins.auth.bootstrap_admin import bootstrap_admin

            bootstrap_admin(self._config, persistence)
        except Exception as e:
            logger.error(f"Failed to initialize auth database: {e}")

        # Register AuthManager in DI
        auth_manager = get_auth_manager()
        ServiceRegistry.register(AuthManager, auth_manager)

        # Register AuditLogger in DI
        audit_logger = get_audit_logger()
        ServiceRegistry.register(AuditLogger, audit_logger)

        # Register WebAuthnManager in DI (if available)
        try:
            from plugins.auth.webauthn import get_webauthn_manager, WebAuthnManager

            webauthn_manager = get_webauthn_manager()
            ServiceRegistry.register(WebAuthnManager, webauthn_manager)
        except (ImportError, Exception):
            pass

        # Register AccountRecoveryManager in DI
        from plugins.auth.account_recovery import (
            get_recovery_manager,
            AccountRecoveryManager,
        )

        recovery_manager = get_recovery_manager()
        ServiceRegistry.register(AccountRecoveryManager, recovery_manager)

        # Register CSRFProtection in DI
        from plugins.auth.csrf import get_csrf_protection, CSRFProtection

        csrf = get_csrf_protection()
        ServiceRegistry.register(CSRFProtection, csrf)

        # Register RBAC service and seed built-in permissions/roles. Tab
        # discovery happens lazily on first use (all plugins may not be loaded
        # yet) and via the /admin/rbac/tabs/refresh endpoint.
        try:
            rbac = get_rbac_service()
            rbac.bootstrap()
            ServiceRegistry.register(RBACService, rbac)
            logger.info("Auth RBAC service registered and seeded")
        except Exception as e:
            logger.error(f"Failed to initialize RBAC service: {e}")

        logger.info("Auth plugin core and internal services registered in DI")

    async def shutdown(self) -> None:
        """Shutdown the auth plugin."""
        logger.info("Shutting down Auth Plugin")
        await super().shutdown()
        self._initialized = False

    # =========================================================================
    # RouterPlugin Interface
    # =========================================================================

    def create_router(self) -> APIRouter:
        """Create the auth API router."""
        # Create a parent router that includes both auth and admin routes
        combined_router = APIRouter()
        combined_router.include_router(auth_router)
        combined_router.include_router(admin_router)
        combined_router.include_router(rbac_admin_router)
        combined_router.include_router(rbac_me_router)
        return combined_router

    def get_router_prefix(self) -> str:
        """Router will be mounted at /api/auth."""
        return "/api"

    def get_router_tags(self) -> List[str]:
        """OpenAPI tags for auth routes."""
        return ["Authentication"]

    # =========================================================================
    # Middleware
    # =========================================================================

    def get_middleware(self) -> Optional[type]:
        """Return the auth middleware class."""
        return AuthMiddleware

    @classmethod
    def setup_app_middleware(cls, app: Any) -> None:
        """Register the central plugin-access enforcement middleware.

        Hooked at app-construction time (the middleware stack freezes before
        lifespan), so the gateway gate is in place for every plugin route.
        """
        from plugins.auth.access_middleware import PluginAccessMiddleware

        app.add_middleware(PluginAccessMiddleware)

    # =========================================================================
    # Static Assets
    # =========================================================================

    def get_static_assets_path(self) -> Optional[Path]:
        """Return the absolute path to static assets."""
        return Path(__file__).parent / "static"

    def get_ui_tabs(self) -> List[Dict[str, str]]:
        """Register auth-related sidebar tabs.

        Returns:
            List of tab definition dicts with 'id' and 'label'.
        """
        return [
            {"id": "login", "label": "Login"},
            {"id": "admin-users", "label": "User Management"},
        ]


# Plugin factory function (required by plugin loader)
def create_plugin() -> AuthPlugin:
    """Create an instance of the auth plugin."""
    return AuthPlugin()
