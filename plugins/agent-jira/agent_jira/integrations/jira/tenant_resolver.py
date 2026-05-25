"""
Tenant-aware Jira client resolver.

Restituisce un JiraClient configurato con le credenziali del tenant corrente,
o il client globale come fallback in single-tenant mode.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import JiraClient

from agent_jira.tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)

# Cache per-tenant JiraClient (evita ricreare ad ogni request)
_tenant_clients: dict[str, "JiraClient"] = {}


def get_tenant_jira_client(
    fallback_client: Optional["JiraClient"] = None,
) -> Optional["JiraClient"]:
    """
    Restituisce il JiraClient per il tenant corrente.

    Ordine di risoluzione:
    1. Se c'è un tenant con settings Jira nel DB, crea/cache un client dedicato
    2. Altrimenti, restituisce il fallback_client (globale, dal config)
    """
    from .client import JiraClient

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return fallback_client

    # Check cache
    cached = _tenant_clients.get(tenant_id)
    if cached is not None:
        return cached

    # Prova a caricare le settings Jira dal tenant nel DB
    try:
        from agent_jira.db.tenants import get_tenant_by_id

        tenant = get_tenant_by_id(tenant_id)
        if not tenant:
            return fallback_client

        settings = tenant.get("settings") or {}
        jira_settings = settings.get("jira") or {}

        base_url = jira_settings.get("base_url")
        email = jira_settings.get("email")
        api_token_stored = jira_settings.get("api_token")
        project_key = jira_settings.get("default_project_key") or jira_settings.get(
            "project_key"
        )

        # Decrypt api_token se cifrato (Sprint 6). Tollerante a valori legacy
        # in chiaro durante il rollout della migration 007.
        api_token: Optional[str] = None
        if api_token_stored:
            try:
                from agent_jira.crypto import decrypt as crypto_decrypt

                api_token = crypto_decrypt(api_token_stored)
            except Exception as exc:
                logger.error(
                    "[jira] Decrypt api_token fallito per tenant %s: %s",
                    tenant_id,
                    exc,
                )
                return fallback_client

        if not all([base_url, email, api_token, project_key]):
            # Credenziali Jira non configurate per questo tenant, usa fallback
            return fallback_client

        client = JiraClient(
            base_url=base_url,
            email=email,
            api_token=api_token,
            project_key=project_key,
            issue_type=jira_settings.get("issue_type", "Story"),
            test_case_issue_type=jira_settings.get("test_case_issue_type", "Test Case"),
            default_labels=jira_settings.get("default_labels", []),
            story_points_field=jira_settings.get("story_points_field"),
            kb_label_field=jira_settings.get("kb_label_field"),
            timeout=float(jira_settings.get("timeout", 15.0)),
            default_priority_name=jira_settings.get("default_priority_name", "Medium"),
            priority_mapping=jira_settings.get("priority_mapping", {}),
        )

        _tenant_clients[tenant_id] = client
        logger.info("[jira] Client Jira creato per tenant %s → %s", tenant_id, base_url)
        return client

    except Exception as exc:
        logger.warning(
            "[jira] Errore caricamento credenziali Jira per tenant %s: %s",
            tenant_id,
            exc,
        )
        return fallback_client


def invalidate_tenant_client(tenant_id: str) -> None:
    """Invalida il client Jira cached per un tenant (dopo aggiornamento settings)."""
    _tenant_clients.pop(tenant_id, None)
