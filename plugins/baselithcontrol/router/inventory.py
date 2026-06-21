"""Read-only inventory routes: the plugin catalog, UI surfaces, and whoami."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from core.auth.types import AuthUser

from ..api_models import EmbedSurface, InventoryView
from ..service import get_aggregator
from ._guards import current_principal, is_admin, read_guard


def build_inventory_router() -> APIRouter:
    """Build the inventory sub-router (authenticated reads)."""
    router = APIRouter(
        tags=["baselithcontrol:inventory"], dependencies=[Depends(read_guard)]
    )

    @router.get("/me")
    async def whoami(user: AuthUser = Depends(current_principal)) -> dict[str, Any]:
        """Identity + capabilities of the caller, so the UI can gate actions."""
        email = user.email
        username: str | None = None
        # Best-effort enrichment so the UI shows real credentials, not a UUID.
        try:
            from core.di.container import ServiceRegistry
            from plugins.auth.persistence import AuthPersistence

            persistence = ServiceRegistry.get(AuthPersistence)
            if persistence is not None and user.is_authenticated:
                db_user = persistence.get_user_by_id(user.user_id)
                if db_user is not None:
                    email = db_user.email or email
                    username = db_user.username
        except Exception:  # noqa: BLE001 — identity enrichment is optional
            pass
        return {
            "user_id": user.user_id,
            "email": email,
            "username": username,
            "display_name": username or email or user.user_id,
            "roles": [r.value for r in user.roles],
            "is_admin": is_admin(user),
            "authenticated": user.is_authenticated,
        }

    @router.get("/inventory", response_model=InventoryView)
    async def inventory(
        request: Request, user: AuthUser = Depends(current_principal)
    ) -> InventoryView:
        """Merged plugin catalog, scoped to the caller.

        Ordinary users only see **active** plugins; admins additionally see
        disabled/failed/discovered plugins (the operational state they alone
        can act on via the lifecycle routes).
        """
        return get_aggregator(request.app).inventory(include_disabled=is_admin(user))

    @router.get("/ui-registry", response_model=list[EmbedSurface])
    async def ui_registry(
        request: Request, user: AuthUser = Depends(current_principal)
    ) -> list[EmbedSurface]:
        """Embeddable UI surfaces for the dashboard shell.

        Surfaces are filtered by the auth plugin's central per-tab access
        policy: admins see everything; other users only see tabs they may
        access (default-allow for unmanaged/unrestricted tabs).
        """
        allow = _tab_access_predicate(user)
        return get_aggregator(request.app).ui_registry(
            allow=allow, include_disabled=is_admin(user)
        )

    return router


def _tab_access_predicate(user: AuthUser):
    """Build a ``(plugin, tab_id) -> bool`` filter from the central tab policy.

    Returns ``None`` (no filtering) for admins or whenever the RBAC service is
    unavailable, so a missing/auth-disabled deployment keeps current behaviour.
    """
    if is_admin(user):
        return None
    try:
        from plugins.auth.rbac.service import get_rbac_service

        tabs = get_rbac_service().accessible_tabs(user.user_id, user.roles)
    except Exception:  # noqa: BLE001 - never block the shell on RBAC errors
        return None
    blocked = {(t["plugin"], t["tab_id"]) for t in tabs if not t.get("allowed", True)}
    if not blocked:
        return None
    return lambda plugin, tab_id: (plugin, tab_id) not in blocked


__all__ = ["build_inventory_router"]
