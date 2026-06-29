"""Bind the authenticated user/tenant context for BaselithBrain sub-app requests.

The backend is mounted as a sub-application, *outside* the host's auth
dependencies, so without this middleware every request runs with no bound
identity and per-user vault scoping is impossible (``get_current_user_id()``
returns ``None`` → everything collapses to the default vault).

This pure-ASGI middleware decodes the ``Authorization: Bearer`` token via the
**central** auth manager (the same verifier the core guards use) and binds the
user + tenant context for the duration of the request, resetting it after. It is
purely additive: a request without a (valid) token is passed through untouched —
anonymous access behaves exactly as before, so it introduces no regression. It
only acts on ``/api`` paths to avoid touching static SPA asset serving.
"""

from __future__ import annotations

from typing import Any

from core.context import (
    reset_tenant_context,
    reset_user_context,
    set_tenant_context,
    set_user_context,
)
from core.observability.logging import get_logger

logger = get_logger(__name__)


def _bearer_header(scope: dict[str, Any]) -> str | None:
    """Raw ``Authorization`` header value (case-insensitive), or ``None``."""
    for key, value in scope.get("headers") or []:
        if key.lower() == b"authorization":
            try:
                return value.decode("latin-1")
            except Exception:  # noqa: BLE001 — malformed header → treat as absent
                return None
    return None


class TenantContextBridge:
    """ASGI middleware binding identity context from the central access token."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        # When mounted (``app.mount("/baselithbrain", subapp)``) Starlette sets
        # ``root_path`` but does NOT strip it from ``path`` — the sub-app sees the
        # FULL ``/baselithbrain/api/...``. Strip ``root_path`` so the ``/api``
        # gate matches both mounted and standalone (root_path == "") serving.
        # Getting this wrong silently skips the bridge → no identity bound → every
        # user collapses to the shared default vault.
        path = scope.get("path", "") or ""
        root = scope.get("root_path", "") or ""
        rel = path[len(root) :] if root and path.startswith(root) else path
        if scope.get("type") != "http" or not rel.startswith("/api"):
            await self.app(scope, receive, send)
            return

        auth_header = _bearer_header(scope)
        t_token = u_token = None
        if auth_header:
            user = await self._authenticate(auth_header)
            if user is not None:
                t_token = set_tenant_context(user.tenant_id)
                u_token = set_user_context(user.user_id) if user.user_id else None
        try:
            await self.app(scope, receive, send)
        finally:
            if u_token is not None:
                reset_user_context(u_token)
            if t_token is not None:
                reset_tenant_context(t_token)

    @staticmethod
    async def _authenticate(auth_header: str) -> Any | None:
        """Resolve an authenticated ``AuthUser`` from the header, else ``None``.

        Degrades to ``None`` (anonymous) on any failure so a token problem never
        breaks request handling — it just means no per-user scoping for that call.
        """
        try:
            from core.auth.manager import get_auth_manager

            user = await get_auth_manager().authenticate(auth_header)
            return user if getattr(user, "is_authenticated", False) else None
        except Exception as exc:  # noqa: BLE001 — never block on an auth hiccup
            logger.debug("baselithbrain context bridge: auth skipped (%s)", exc)
            return None


__all__ = ["TenantContextBridge"]
