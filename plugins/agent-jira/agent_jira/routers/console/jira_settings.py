"""
API endpoints for Jira settings management (multi-tenant aware).

GET  /console/jira/settings          — read current Jira config for the tenant
PUT  /console/jira/settings          — update Jira config for the tenant
POST /console/jira/settings/test     — test Jira connection with given credentials
POST /console/jira/settings/projects — preview available Jira projects (before saving)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from agent_jira.tenant_context import get_current_tenant_id
from agent_jira.config import (
    JIRA_API_TOKEN,
    JIRA_BASE_URL,
    JIRA_EMAIL,
    JIRA_ISSUE_TYPE,
    JIRA_PROJECT_KEY,
    MULTI_TENANT_ENABLED,
    POSTGRES_ENABLED,
)

from . import router

logger = logging.getLogger(__name__)


class JiraSettingsPayload(BaseModel):
    base_url: str = Field(
        ..., min_length=1, description="Jira Cloud URL (es. https://acme.atlassian.net)"
    )
    email: str = Field(..., min_length=1, description="Email dell'account Jira")
    api_token: str = Field(..., min_length=1, description="API token Jira")
    project_key: str = Field(
        ..., min_length=1, description="Chiave progetto Jira predefinito (es. PROJ)"
    )
    default_project_key: Optional[str] = Field(
        default=None,
        description="Progetto predefinito (sovrascrive project_key se presente)",
    )
    allowed_project_keys: Optional[List[str]] = Field(
        default=None, description="Lista progetti abilitati per il tenant"
    )
    issue_type: str = Field(default="Story", description="Tipo issue per le user story")
    test_case_issue_type: str = Field(
        default="Test Case", description="Tipo issue per i test case"
    )


class JiraTestPayload(BaseModel):
    base_url: str
    email: str
    api_token: str


class JiraProjectsPreviewPayload(BaseModel):
    base_url: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    api_token: str = Field(..., min_length=1)


def _get_env_jira_settings() -> Dict[str, Any]:
    """Restituisce le impostazioni Jira dall'env (single-tenant fallback)."""
    pk = JIRA_PROJECT_KEY or ""
    return {
        "base_url": JIRA_BASE_URL or "",
        "email": JIRA_EMAIL or "",
        "api_token_set": bool(JIRA_API_TOKEN),
        "project_key": pk,
        "default_project_key": pk,
        "allowed_project_keys": [pk] if pk else [],
        "issue_type": JIRA_ISSUE_TYPE or "Story",
        "source": "environment",
    }


def _get_tenant_jira_settings(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Restituisce le impostazioni Jira dal DB per il tenant."""
    if not POSTGRES_ENABLED:
        return None
    try:
        from agent_jira.db.tenants import get_tenant_by_id

        tenant = get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        settings = tenant.get("settings") or {}
        jira = settings.get("jira") or {}
        if not jira:
            return None
        pk = jira.get("project_key", "")
        dpk = jira.get("default_project_key") or pk
        apk = jira.get("allowed_project_keys") or ([dpk] if dpk else [])
        return {
            "base_url": jira.get("base_url", ""),
            "email": jira.get("email", ""),
            "api_token_set": bool(jira.get("api_token")),
            "project_key": pk,
            "default_project_key": dpk,
            "allowed_project_keys": apk,
            "issue_type": jira.get("issue_type", "Story"),
            "test_case_issue_type": jira.get("test_case_issue_type", "Test Case"),
            "source": "tenant",
        }
    except Exception as exc:
        logger.warning("[jira_settings] Error reading tenant settings: %s", exc)
        return None


@router.get("/jira/settings")
def get_jira_settings() -> Dict[str, Any]:
    """Restituisce le impostazioni Jira correnti (da tenant DB o env)."""
    tenant_id = get_current_tenant_id()

    if tenant_id and MULTI_TENANT_ENABLED:
        tenant_settings = _get_tenant_jira_settings(tenant_id)
        if tenant_settings:
            return {"status": "ok", "settings": tenant_settings, "configurable": True}

    env_settings = _get_env_jira_settings()
    configurable = MULTI_TENANT_ENABLED and POSTGRES_ENABLED
    return {"status": "ok", "settings": env_settings, "configurable": configurable}


@router.put("/jira/settings")
def update_jira_settings(
    payload: JiraSettingsPayload,
    request: Request = None,  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Aggiorna le impostazioni Jira per il tenant corrente."""
    if not MULTI_TENANT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multi-tenancy non abilitata. Configura Jira via variabili d'ambiente.",
        )

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nessun tenant associato alla richiesta.",
        )

    if not POSTGRES_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database non disponibile.",
        )

    try:
        from agent_jira.db.tenants import get_tenant_by_id, update_tenant

        tenant = get_tenant_by_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant non trovato.",
            )

        current_settings = tenant.get("settings") or {}

        # Normalizza: default_project_key ha priorità su project_key
        dpk = (payload.default_project_key or payload.project_key).upper()
        apk = (
            [k.upper() for k in payload.allowed_project_keys]
            if payload.allowed_project_keys
            else [dpk]
        )
        # Assicura che il default sia sempre incluso negli allowed
        if dpk and dpk not in apk:
            apk.insert(0, dpk)

        # Cifra api_token prima di persistere (Sprint 6).
        # In caso di SECRETS_KEY non configurata, rifiuta il salvataggio anziché
        # persistere un segreto in chiaro.
        try:
            from agent_jira.crypto import encrypt as crypto_encrypt

            encrypted_token = crypto_encrypt(payload.api_token)
        except Exception as exc:
            logger.error("[jira_settings] Cifratura api_token fallita: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Servizio di cifratura non disponibile: imposta SECRETS_KEY "
                    "nell'environment del backend prima di salvare credenziali."
                ),
            )

        current_settings["jira"] = {
            "base_url": payload.base_url.rstrip("/"),
            "email": payload.email,
            "api_token": encrypted_token,
            "project_key": dpk,
            "default_project_key": dpk,
            "allowed_project_keys": apk,
            "issue_type": payload.issue_type,
            "test_case_issue_type": payload.test_case_issue_type,
        }

        update_tenant(tenant_id, settings=current_settings)

        # Invalida la cache del client Jira per questo tenant
        try:
            from agent_jira.integrations.jira.tenant_resolver import invalidate_tenant_client

            invalidate_tenant_client(tenant_id)
        except Exception:
            pass

        # Audit log (Sprint 6): modifica credenziali è evento sensibile.
        # NON loggare mai il token cifrato o in chiaro nel metadata.
        try:
            from agent_jira.audit import record as audit_record

            audit_record(
                action="jira_settings.update",
                resource_type="jira_config",
                resource_id=tenant_id,
                tenant_id=tenant_id,
                metadata={
                    "base_url": payload.base_url,
                    "email": payload.email,
                    "default_project_key": dpk,
                    "api_token_changed": True,
                },
                request=request,
            )
        except Exception:
            pass

        return {
            "status": "ok",
            "message": "Impostazioni Jira aggiornate con successo.",
            "settings": {
                "base_url": payload.base_url,
                "email": payload.email,
                "api_token_set": True,
                "project_key": dpk,
                "default_project_key": dpk,
                "allowed_project_keys": apk,
                "issue_type": payload.issue_type,
                "test_case_issue_type": payload.test_case_issue_type,
                "source": "tenant",
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[jira_settings] Error updating settings: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante il salvataggio: {exc}",
        )


@router.post("/jira/settings/test")
def test_jira_connection(payload: JiraTestPayload) -> Dict[str, Any]:
    """Testa la connessione Jira con le credenziali fornite."""
    import httpx

    base_url = payload.base_url.rstrip("/")
    try:
        response = httpx.get(
            f"{base_url}/rest/api/3/myself",
            auth=(payload.email, payload.api_token),
            timeout=10.0,
        )
        if response.status_code == 200:
            user_data = response.json()
            return {
                "status": "ok",
                "message": "Connessione riuscita.",
                "user": {
                    "displayName": user_data.get("displayName", ""),
                    "emailAddress": user_data.get("emailAddress", ""),
                    "accountId": user_data.get("accountId", ""),
                },
            }
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Credenziali non valide. Verifica email e API token.",
            }
        elif response.status_code == 403:
            return {
                "status": "error",
                "message": "Accesso negato. L'API token potrebbe non avere i permessi necessari.",
            }
        else:
            return {
                "status": "error",
                "message": f"Errore imprevisto (HTTP {response.status_code}).",
            }
    except httpx.ConnectError:
        return {
            "status": "error",
            "message": "Impossibile raggiungere il server Jira. Verifica l'URL.",
        }
    except httpx.TimeoutException:
        return {
            "status": "error",
            "message": "Timeout nella connessione al server Jira.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Errore: {exc}",
        }


@router.post("/jira/settings/projects")
def preview_jira_projects(payload: JiraProjectsPreviewPayload) -> Dict[str, Any]:
    """Fetch available Jira projects using provided credentials (before saving)."""
    import httpx

    base_url = payload.base_url.rstrip("/")
    try:
        response = httpx.get(
            f"{base_url}/rest/api/3/project/search",
            params={"maxResults": 200},
            auth=(payload.email, payload.api_token),
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        raw = data.get("values") if isinstance(data, dict) else data
        projects = [
            {"key": (p.get("key") or "").strip(), "name": (p.get("name") or "").strip()}
            for p in (raw or [])
            if (p.get("key") or "").strip()
        ]
        return {"status": "ok", "projects": projects}
    except httpx.ConnectError:
        return {
            "status": "error",
            "message": "Impossibile raggiungere il server Jira.",
            "projects": [],
        }
    except httpx.TimeoutException:
        return {
            "status": "error",
            "message": "Timeout nella connessione al server Jira.",
            "projects": [],
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc), "projects": []}
