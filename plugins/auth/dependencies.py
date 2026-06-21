"""
Auth Plugin FastAPI Dependencies.

Provides dependency injection for route authentication and service resolution.
"""

from core.observability.logging import get_logger
from typing import Callable, Optional

from fastapi import Cookie, Depends, HTTPException, Request, status, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.context import set_tenant_context
from core.di.container import ServiceRegistry, ServiceNotFoundError
from core.auth import AuthRole, AuthUser, AuthManager
from plugins.auth.config import AuthConfig
from plugins.auth.persistence import AuthPersistence

logger = get_logger(__name__)

# Optional bearer auth (doesn't fail if missing)
_optional_bearer = HTTPBearer(auto_error=False)


def _bind_tenant(user: AuthUser) -> AuthUser:
    """Bind the tenant context to the authenticated user's tenant.

    Tenancy is identity-derived: the tenant a request works in comes from *who
    is logged in* (``user.tenant_id``, carried by the JWT), never a
    client-supplied header. ``get_current_user`` is the single chokepoint for
    every plugin guard (``require_auth`` / ``require_roles`` /
    ``require_permission`` / ``require_tab``), so binding here gives every
    guarded plugin route ``get_current_tenant_id() == user.tenant_id``.

    Mirrors the core SecurityMiddleware: ``TenantMiddleware`` pre-set the
    context to ``"default"`` before dependencies ran and restores it in its
    ``finally`` block; this intermediate set is what the route handler and
    everything downstream observe.
    """
    set_tenant_context(user.tenant_id)
    return user


# =============================================================================
# Service Dependency Injection Functions
# =============================================================================


async def get_auth_config_dep() -> AuthConfig:
    """FastAPI dependency for obtaining AuthConfig from DI container.

    Returns:
        AuthConfig: The auth configuration instance

    Raises:
        HTTPException: If config is not initialized or not found
    """
    try:
        config = ServiceRegistry.get(AuthConfig)
        if config is None:
            raise HTTPException(status_code=503, detail="Auth config not initialized")
        return config
    except ServiceNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Auth config not registered. Plugin may not be initialized.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Failed to resolve auth config: {str(e)}"
        )


async def get_auth_persistence_dep() -> AuthPersistence:
    """FastAPI dependency for obtaining AuthPersistence from DI container.

    Returns:
        AuthPersistence: The auth persistence instance

    Raises:
        HTTPException: If persistence is not initialized or not found
    """
    try:
        persistence = ServiceRegistry.get(AuthPersistence)
        if persistence is None:
            raise HTTPException(
                status_code=503, detail="Auth persistence not initialized"
            )
        return persistence
    except ServiceNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Auth persistence not registered. Plugin may not be initialized.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Failed to resolve auth persistence: {str(e)}"
        )


async def get_auth_manager_dep() -> AuthManager:
    """FastAPI dependency for obtaining AuthManager from DI container.

    Returns:
        AuthManager: The auth manager instance

    Raises:
        HTTPException: If manager is not initialized or not found
    """
    try:
        manager = ServiceRegistry.get(AuthManager)
        if manager is None:
            raise HTTPException(status_code=503, detail="Auth manager not initialized")
        return manager
    except ServiceNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Auth manager not registered. Plugin may not be initialized.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Failed to resolve auth manager: {str(e)}"
        )


async def get_audit_logger_dep():
    """FastAPI dependency for obtaining AuditLogger from DI container.

    Returns:
        AuditLogger: The audit logger instance

    Raises:
        HTTPException: If audit logger is not initialized or not found
    """
    try:
        from plugins.auth.audit import AuditLogger

        audit_logger = ServiceRegistry.get(AuditLogger)
        if audit_logger is None:
            raise HTTPException(status_code=503, detail="Audit logger not initialized")
        return audit_logger
    except ServiceNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Audit logger not registered. Plugin may not be initialized.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Failed to resolve audit logger: {str(e)}"
        )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
    token: Optional[str] = Query(None),
    refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
    config: AuthConfig = Depends(get_auth_config_dep),
    auth_manager: AuthManager = Depends(get_auth_manager_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> AuthUser:
    """
    Get the current authenticated user.

    Checks Authorization header first, then falls back to refresh_token cookie.

    Returns:
        AuthUser object (may be anonymous if not authenticated)
    """

    # Check if path is public
    if request.url.path in config.public_paths:
        return AuthUser(user_id="anonymous", roles={AuthRole.ANONYMOUS})

    # Try an API key (X-API-Key or bearer bsk_...) first.
    from plugins.auth.api_key_auth import extract_api_key, maybe_authenticate_api_key

    if extract_api_key(request.headers):
        api_user = maybe_authenticate_api_key(persistence, request.headers)
        if api_user:
            request.state.user = api_user
            return _bind_tenant(api_user)

    # Try Bearer token from Authorization header
    if credentials:
        auth_header = f"Bearer {credentials.credentials}"
        user = await auth_manager.authenticate(auth_header)
        if user.is_authenticated:
            request.state.user = user
            return _bind_tenant(user)

    # Try token from query param (for SSE/WebSockets)
    if token:
        auth_header = f"Bearer {token}"
        user = await auth_manager.authenticate(auth_header)
        if user.is_authenticated:
            request.state.user = user
            return _bind_tenant(user)

    # Fallback to refresh_token cookie (for session-based auth)
    if refresh_token:
        user_id = persistence.validate_refresh_token(refresh_token)
        if user_id:
            db_user = persistence.get_user_by_id(user_id)
            if db_user and db_user.is_active and not db_user.is_locked():
                from plugins.auth.tenancy import resolve_user_tenant

                user = AuthUser(
                    user_id=db_user.id,
                    email=db_user.email,
                    roles=db_user.roles,
                    tenant_id=resolve_user_tenant(db_user.id, config),
                    metadata={"allowed_tabs": db_user.allowed_tabs},
                )
                request.state.user = user
                return _bind_tenant(user)

    # No valid auth found
    return AuthUser(user_id="anonymous", roles={AuthRole.ANONYMOUS})


async def require_auth(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    config: AuthConfig = Depends(get_auth_config_dep),
) -> AuthUser:
    """
    Dependency that requires a valid authenticated user.

    Raises:
        HTTPException 401 if not authenticated
    """

    # Skip auth check for public paths
    if request.url.path in config.public_paths:
        return user

    if not config.auth_required:
        # Auth not required globally, allow anonymous
        return user

    if not user.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(*roles: AuthRole) -> Callable:
    """
    Factory for role-checking dependencies.

    Usage:
        @router.get("/admin")
        async def admin_route(user: AuthUser = Depends(require_roles(AuthRole.ADMIN))):
            ...
    """

    async def _role_checker(
        user: AuthUser = Depends(require_auth),
    ) -> AuthUser:
        if not any(user.has_role(r) for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {[r.value for r in roles]}",
            )
        return user

    return _role_checker


def require_admin() -> Callable:
    """Shortcut for requiring admin role."""
    return require_roles(AuthRole.ADMIN)


async def get_current_active_user(
    user: AuthUser = Depends(require_auth),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> AuthUser:
    """
    Get current user, ensuring they are active.

    Raises:
        HTTPException 403 if user is not active
    """
    # Ensure user is authenticated
    if not user.is_authenticated or user.user_id == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # For authenticated users, verify they're still active in DB
    db_user = persistence.get_user_by_id(user.user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    if db_user.is_locked():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked",
        )

    return user


async def forbid_while_impersonating(
    user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    """Reject credential-altering actions while an admin is impersonating.

    Applied to sensitive self-service routes (password change, MFA changes,
    API-key minting) so an impersonating administrator cannot alter the
    target's credentials or create persistent grants that would outlive the
    impersonation session. A no-op for normal (non-impersonation) tokens, so it
    introduces no behaviour change on the regular auth path.
    """
    from plugins.auth.impersonation import is_impersonating

    if is_impersonating(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is not allowed while impersonating a user",
        )
    return user


def require_tab_access(tab_id: str) -> Callable:
    """
    Factory for tab access checking (for guest users).

    Usage:
        @router.get("/honeypot")
        async def honeypot_data(user: AuthUser = Depends(require_tab_access("honeypot"))):
            ...
    """

    async def _tab_checker(
        user: AuthUser = Depends(require_auth),
    ) -> AuthUser:
        # Non-guests have full access
        if not user.has_role(AuthRole.GUEST):
            return user

        # Check allowed_tabs for guests
        allowed_tabs = user.metadata.get("allowed_tabs")
        if allowed_tabs is None:
            # Guest with no restrictions
            return user

        if tab_id not in allowed_tabs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to '{tab_id}' tab is not permitted",
            )

        return user

    return _tab_checker


# =============================================================================
# Granular RBAC guards (permission- and tab-based)
# =============================================================================


def require_permission(*slugs: str, mode: str = "any") -> Callable:
    """Factory requiring one (``mode='any'``) or all (``mode='all'``) of the
    given permission slugs, resolved from the central RBAC store.

    The admin wildcard ('*') satisfies any requirement. Anonymous callers are
    rejected with 401.

    Usage:
        @router.get("/x")
        async def x(user: AuthUser = Depends(require_permission("rbac.manage"))):
            ...
    """

    async def _perm_checker(user: AuthUser = Depends(require_auth)) -> AuthUser:
        from plugins.auth.rbac.permissions import has_all, has_any
        from plugins.auth.rbac.service import get_rbac_service

        if not user.is_authenticated or user.user_id == "anonymous":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        perms = get_rbac_service().effective_permissions(user.user_id, user.roles)
        ok = has_all(perms, slugs) if mode == "all" else has_any(perms, slugs)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires permission(s): {list(slugs)}",
            )
        return user

    return _perm_checker


def require_tab(plugin: str, tab_id: str) -> Callable:
    """Factory enforcing the central per-tab access policy.

    Default-allow: an unmanaged or unrestricted tab is open to every
    authenticated user. A restricted tab requires its ``tab:<plugin>:<id>``
    permission (admin/wildcard always passes).
    """

    async def _tab_policy_checker(
        user: AuthUser = Depends(require_auth),
    ) -> AuthUser:
        from plugins.auth.rbac.service import get_rbac_service

        if not get_rbac_service().can_access_tab(
            user.user_id, user.roles, plugin, tab_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to '{plugin}:{tab_id}' is not permitted",
            )
        return user

    return _tab_policy_checker
