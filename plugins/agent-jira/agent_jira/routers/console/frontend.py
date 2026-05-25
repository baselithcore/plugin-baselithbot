from __future__ import annotations

from typing import Dict

from fastapi import HTTPException, status
from fastapi.responses import FileResponse

from agent_jira.tenant_context import get_current_tenant_id
from agent_jira.ui.documents import SUPPORTED_UPLOAD_TYPES
from agent_jira.config import (
    AUTH_REQUIRED,
    CONSOLE_ANALYSIS_ENABLED,
    CONSOLE_CHAT_ENABLED,
    JIRA_PROJECT_KEY,
    MULTI_TENANT_ENABLED,
    POSTGRES_ENABLED,
)

from . import public_router
from .common import FRONTEND_INDEX


def _tenant_jira_configured() -> tuple[bool, str]:
    """Returns (configured, project_key) for the current tenant's Jira settings."""
    if not (MULTI_TENANT_ENABLED and POSTGRES_ENABLED):
        return False, ""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return False, ""
    try:
        from agent_jira.db.tenants import get_tenant_by_id

        tenant = get_tenant_by_id(tenant_id)
        if not tenant:
            return False, ""
        jira = (tenant.get("settings") or {}).get("jira") or {}
        configured = bool(
            jira.get("base_url")
            and jira.get("email")
            and jira.get("api_token")
            and (jira.get("default_project_key") or jira.get("project_key"))
        )
        pk = jira.get("default_project_key") or jira.get("project_key") or ""
        return configured, pk
    except Exception:
        return False, ""


@public_router.get("/config")
def console_config() -> Dict[str, object]:
    import importlib

    ui_services = importlib.import_module("app.ui.services")
    chat_service = ui_services.get_chat_service()
    project_planner = getattr(chat_service, "project_planner", None)
    jira_client = getattr(chat_service, "jira_client", None)

    jira_enabled = bool(jira_client and jira_client.is_ready())
    jira_project_key = JIRA_PROJECT_KEY
    if not jira_enabled:
        tenant_configured, tenant_pk = _tenant_jira_configured()
        if tenant_configured:
            jira_enabled = True
            if tenant_pk:
                jira_project_key = tenant_pk

    return {
        "chat_enabled": bool(CONSOLE_CHAT_ENABLED),
        "analysis_enabled": bool(
            CONSOLE_ANALYSIS_ENABLED and project_planner is not None
        ),
        "jira_enabled": jira_enabled,
        "supported_upload_types": SUPPORTED_UPLOAD_TYPES,
        "jira_manual_required": bool(
            getattr(chat_service, "jira_manual_approval", False)
        ),
        "jira_project_key": jira_project_key,
        "auth_required": bool(AUTH_REQUIRED and MULTI_TENANT_ENABLED),
    }


@public_router.get("/", include_in_schema=False)
def console_frontend() -> FileResponse:
    if not FRONTEND_INDEX.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UI React non trovata: esegui npm install && npm run build in /frontend.",
        )
    return FileResponse(FRONTEND_INDEX)
