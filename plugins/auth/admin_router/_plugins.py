"""Admin endpoints for per-plugin tenancy-mode overrides.

List every loaded plugin with its manifest-declared tenancy and any runtime
override, and set / clear the override. ``shared`` scopes data by the
deployment-derived tenant (1 tenant ⇒ N users); ``personal`` forces 1 user ⇒ 1
tenant regardless of the deployment. Changing a plugin that already holds data
is a data-*visibility* migration (existing rows stay under their old tenant key)
— callers surface that warning in the UI. All routes are gated on the
``plugins.tenancy.manage`` permission (the admin wildcard satisfies it) and
audited; writes invalidate the resolver cache so the change takes effect within
seconds, fleet-wide.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.admin_router._helpers import get_client_ip
from plugins.auth.audit import AuditAction
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_persistence_dep,
    require_permission,
)
from plugins.auth.persistence import AuthPersistence
from plugins.auth.persistence._plugin_tenancy import VALID_MODES
from plugins.auth.rbac.permissions import Permission
from plugins.auth.tenancy_overrides import invalidate_override_cache

logger = get_logger(__name__)

# Granular gate: any identity holding the manage permission (or the admin
# wildcard) — never a literal role check, so effective-admins always pass.
_require_manage = require_permission(Permission.PLUGINS_TENANCY_MANAGE)

router = APIRouter(prefix="/plugins", tags=["Admin"])


class PluginTenancyRow(BaseModel):
    """One plugin's declared + effective tenancy for the admin table."""

    plugin_name: str
    version: Optional[str] = None
    system: bool = False
    declared_tenancy: str
    override: Optional[str] = None
    effective_tenancy: str
    # System plugins are infrastructure (e.g. auth, the tenancy source itself):
    # their tenancy is NOT overridable — changing it would break tenant/system.
    locked: bool = False


class PluginTenancyList(BaseModel):
    """Response: every loaded plugin and its tenancy state."""

    plugins: list[PluginTenancyRow]


class TenancyOverrideUpdate(BaseModel):
    """Request body: the override mode, or ``null`` to clear (inherit manifest)."""

    mode: Optional[str] = None


def _loaded_plugins() -> list[tuple[str, Optional[str], bool, str]]:
    """``(name, version, system, declared_tenancy)`` for each loaded plugin.

    Reads the live registry; returns an empty list if the plugin system is not
    yet initialised, so the admin table degrades to empty rather than 500-ing.
    """
    try:
        from core.plugins.api import get_controller

        controller = get_controller()
    except Exception:  # noqa: BLE001 — plugin system not ready
        return []
    rows: list[tuple[str, Optional[str], bool, str]] = []
    for name, _state in controller.lifecycle.get_all_states().items():
        plugin = controller.registry.get(name)
        if plugin is None:
            continue
        try:
            md = plugin.metadata
        except Exception:  # noqa: BLE001 — a broken manifest must not sink the list
            continue
        rows.append((md.name, md.version, bool(md.system), md.tenancy))
    return rows


@router.get("/tenancy", response_model=PluginTenancyList)
async def list_plugin_tenancy(
    _: AuthUser = Depends(_require_manage),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> PluginTenancyList:
    """List loaded plugins with declared tenancy + any runtime override."""
    try:
        overrides = persistence.get_plugin_tenancy_overrides()
    except Exception:  # noqa: BLE001 — show declared modes if the table is down
        overrides = {}
    rows = [
        PluginTenancyRow(
            plugin_name=name,
            version=version,
            system=system,
            declared_tenancy=declared,
            # A system plugin can never hold an override (writes are rejected and
            # core ignores any stray row) — pin its override/effective to declared.
            override=None if system else overrides.get(name),
            effective_tenancy=declared if system else (overrides.get(name) or declared),
            locked=system,
        )
        for name, version, system, declared in sorted(_loaded_plugins())
    ]
    return PluginTenancyList(plugins=rows)


@router.put("/tenancy/{plugin_name}", response_model=PluginTenancyRow)
async def set_plugin_tenancy(
    plugin_name: str,
    body: TenancyOverrideUpdate,
    request: Request,
    admin: AuthUser = Depends(_require_manage),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> PluginTenancyRow:
    """Set (``mode``) or clear (``mode=null``) a plugin's tenancy override."""
    target = next((row for row in _loaded_plugins() if row[0] == plugin_name), None)
    if target is None:
        raise HTTPException(status_code=404, detail="plugin_not_found")
    _name, _version, system, declared = target
    # Hard refuse: a system/infrastructure plugin's tenancy is not overridable —
    # re-scoping it (e.g. auth, the tenancy source) would break tenant isolation.
    if system:
        raise HTTPException(status_code=403, detail="plugin_tenancy_locked")

    mode = body.mode
    if mode is None:
        persistence.delete_plugin_tenancy_override(plugin_name)
    elif mode in VALID_MODES:
        persistence.set_plugin_tenancy_override(plugin_name, mode, admin.user_id)
    else:
        raise HTTPException(status_code=400, detail="invalid_tenancy_mode")

    invalidate_override_cache()
    # NB: auth_audit_log.target_id is a UUID column (designed for user ids). A
    # plugin name is not a UUID, so it goes in the jsonb `details`, never
    # target_id — passing it there raises "invalid input syntax for type uuid".
    audit.log(
        action=AuditAction.PLUGIN_TENANCY_CHANGED,
        actor_id=admin.user_id,
        target_id=None,
        details={"plugin": plugin_name, "mode": mode},
        ip_address=get_client_ip(request),
    )
    return PluginTenancyRow(
        plugin_name=plugin_name,
        declared_tenancy=declared,
        override=mode,
        effective_tenancy=mode or declared,
    )


__all__ = ["router"]
