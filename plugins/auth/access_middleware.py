"""Central plugin-access enforcement (pure ASGI).

Maps each incoming request to the plugin that owns its route and enforces the
RBAC tab policy at plugin granularity. This is the single, coherent
enforcement point for every plugin — no per-plugin router changes needed.

Design guarantees:
- **Fail-open**: any resolution error, or an unknown/unrestricted plugin,
  lets the request through. Only an explicit policy denial returns 403, so
  nothing changes until an admin restricts a tab.
- **Pure ASGI** (no BaseHTTPMiddleware) per project convention.
- Never gates the auth plugin itself (avoid locking the admin console) or
  non-HTTP scopes (websockets/SSE upgrades pass through).
"""

from __future__ import annotations

import json
from typing import Any

from starlette.requests import Request

from core.auth import AuthManager, AuthRole, AuthUser
from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.persistence import AuthPersistence

logger = get_logger(__name__)


class PluginAccessMiddleware:
    """Enforce the central per-plugin access policy on plugin routes."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        try:
            allowed = await self._is_allowed(scope, receive)
        except Exception as exc:  # noqa: BLE001 - never break the app
            logger.warning("Plugin access check skipped (fail-open): %s", exc)
            allowed = True
        if not allowed:
            await self._forbidden(send)
            return
        await self.app(scope, receive, send)

    # Navigation frames — never gate their shell. The auth console must stay
    # reachable to manage access at all; the control plane is the host shell
    # impersonated/redirected users land on, and its internal tabs are gated by
    # the per-tab policy (frontend nav filter + /api/baselithcontrol gating), so
    # blocking the whole shell would lock users out of navigation.
    _UNGATED_PLUGINS = frozenset({"auth", "baselithcontrol"})

    async def _is_allowed(self, scope: Any, receive: Any) -> bool:
        if scope.get("method") == "OPTIONS":
            return True
        path = scope.get("path", "")
        app = scope.get("app")
        registry = getattr(getattr(app, "state", None), "plugin_registry", None)
        if registry is None:
            return True

        plugin, is_ui = self._resolve_plugin(path, registry)
        # Unknown route or a navigation-frame shell -> never gate here.
        if not plugin or plugin in self._UNGATED_PLUGINS:
            return True

        user = await self._authenticate(Request(scope, receive))

        # A UI-surface load (the SPA document at ``/<plugin>`` and its static
        # assets) is a browser *navigation*: it carries only the refresh cookie,
        # never the localStorage access token that is the app's primary identity.
        # When that cookie is absent (plugin opened on a different host, SameSite,
        # secure-cookie-over-http) a logged-in admin resolves as *anonymous*
        # here, and gating the shell would lock them out of a restricted plugin
        # they may legitimately use. Fail open for unauthenticated UI loads — the
        # SPA's own ProtectedRoute and the Bearer-gated ``/api/<plugin>`` routes
        # (which DO see the access token) still enforce. API routes and
        # positively-authenticated users stay strictly gated.
        if is_ui and not user.is_authenticated:
            return True

        from plugins.auth.rbac.service import get_rbac_service

        return get_rbac_service().plugin_allowed(
            user.user_id, user.roles, plugin, registry
        )

    @staticmethod
    def _resolve_plugin(path: str, registry: Any) -> tuple[str | None, bool]:
        """Resolve which plugin owns ``path`` and whether it is a UI surface.

        Returns ``(plugin_name, is_ui)``. ``is_ui`` is ``True`` for the plugin's
        UI surfaces (the SPA at ``/<plugin>`` and its assets at
        ``/plugins/<plugin>/static/...``) and ``False`` for the backend API
        (``/api/<plugin>`` via the registry route matcher). The distinction lets
        the caller fail open on anonymous UI-shell loads while keeping API routes
        strictly gated. Only names the registry actually serves static for are
        matched, so core paths (``/static``, ``/docs``, non-plugin API) fall
        through to default-allow.
        """
        matcher = getattr(registry, "match_plugin_route", None)
        plugin = matcher(path) if matcher else None
        if plugin:
            return plugin, False  # backend API route
        parts = path.strip("/").split("/")
        if not parts or not parts[0]:
            return None, False
        name = parts[1] if parts[0] == "plugins" and len(parts) > 1 else parts[0]
        try:
            static_paths = registry.get_all_static_paths()
        except Exception:  # noqa: BLE001 - fail-open on any resolution error
            return None, False
        return (name, True) if name in static_paths else (None, False)

    async def _authenticate(self, request: Request) -> AuthUser:
        """Resolve the caller from header / cookie (mirrors AuthMiddleware)."""
        auth_manager = ServiceRegistry.get(AuthManager)
        header = request.headers.get("Authorization")
        if header and auth_manager:
            user = await auth_manager.authenticate(header)
            if user.is_authenticated:
                return user

        config = ServiceRegistry.get(AuthConfig)
        cookie_name = getattr(config, "cookie_name", "refresh_token")
        token = request.cookies.get(cookie_name)
        if token:
            persistence = ServiceRegistry.get(AuthPersistence)
            user_id = persistence.validate_refresh_token(token) if persistence else None
            if user_id:
                db_user = persistence.get_user_by_id(user_id)
                if db_user and db_user.is_active and not db_user.is_locked():
                    return AuthUser(
                        user_id=db_user.id,
                        email=db_user.email,
                        roles=db_user.roles,
                    )
        return AuthUser(user_id="anonymous", roles={AuthRole.ANONYMOUS})

    @staticmethod
    async def _forbidden(send: Any) -> None:
        body = json.dumps({"detail": "Access to this plugin is not permitted"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})


__all__ = ["PluginAccessMiddleware"]
