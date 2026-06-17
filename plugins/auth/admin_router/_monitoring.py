"""Admin session, audit-log, and plugin-tab inspection endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.admin_router._models import (
    AuditEntryResponse,
    AuditLogResponse,
    PluginTab,
    SessionInfo,
    SessionListResponse,
)
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_persistence_dep,
    require_admin,
)
from plugins.auth.persistence import AuthPersistence

logger = get_logger(__name__)

router = APIRouter()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user_id: Optional[str] = Query(default=None),
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """
    List active sessions.

    Optionally filter by user_id.
    Admin only.
    """
    sessions = persistence.get_active_sessions(user_id=user_id)

    session_list = []
    for s in sessions:
        session_list.append(
            SessionInfo(
                id=s.id,
                user_id=s.user_id,
                user_email=getattr(s, "user_email", ""),
                created_at=s.created_at,
                expires_at=s.expires_at,
            )
        )

    return SessionListResponse(
        sessions=session_list,
        total=len(session_list),
    )


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    action: Optional[str] = Query(default=None),
    actor_id: Optional[str] = Query(default=None),
    target_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    admin: AuthUser = Depends(require_admin()),
    audit=Depends(get_audit_logger_dep),
):
    """
    Get audit log entries.

    Admin only.
    """
    entries, total = audit.get_entries(
        action=action,
        actor_id=actor_id,
        target_id=target_id,
        page=page,
        limit=limit,
    )

    return AuditLogResponse(
        entries=[
            AuditEntryResponse(
                id=e.id,
                action=e.action,
                actor_id=e.actor_id,
                target_id=e.target_id,
                details=e.details,
                ip_address=e.ip_address,
                created_at=e.created_at,
            )
            for e in entries
        ],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/plugins/tabs", response_model=List[PluginTab])
async def list_plugin_tabs(admin: AuthUser = Depends(require_admin())):
    """
    List available UI tabs from all plugins.

    Admin only.
    """
    from core.plugins.api import get_controller

    tabs = []
    try:
        controller = get_controller()
        registry = controller.registry

        # Use existing list_plugins method to get metadata
        plugins_meta = registry.list_plugins()

        for meta in plugins_meta:
            plugin_name = meta["name"]
            # Get the actual plugin instance from the registry
            plugin = registry.get(plugin_name)

            if plugin and hasattr(plugin, "get_ui_tabs"):
                # Call get_ui_tabs if it exists (it should, from interface)
                plugin_tabs = plugin.get_ui_tabs()
                for tab in plugin_tabs:
                    tabs.append(
                        PluginTab(id=tab["id"], label=tab["label"], plugin=plugin_name)
                    )

    except Exception as e:
        logger.error(f"Failed to list plugin tabs: {e}")
        # Return empty list on error to not block UI

    return tabs
