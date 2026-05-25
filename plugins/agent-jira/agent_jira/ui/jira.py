"""Helpers that keep the Jira integration logic isolated from the UI layout."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping

from agent_jira.project_manager import ProjectPlan

from .services import chat_service

logger = logging.getLogger(__name__)


def _resolve_jira_client():
    """Return tenant-aware Jira client with global fallback."""
    from agent_jira.integrations.jira.tenant_resolver import get_tenant_jira_client

    fallback = getattr(chat_service, "jira_client", None)
    return get_tenant_jira_client(fallback_client=fallback)


def jira_client_ready() -> bool:
    client = _resolve_jira_client()
    return bool(client and client.is_ready())


def get_jira_results_for_label(label: str, limit: int = 10) -> List[Dict[str, Any]]:
    if not label:
        logger.debug("get_jira_results_for_label chiamato con label vuota.")
        return []
    client = _resolve_jira_client()
    if client is None or not client.is_ready():
        logger.debug(
            "get_jira_results_for_label saltata: client Jira non pronto per label %s.",
            label,
        )
        return []
    try:
        logger.debug("Ricerca Jira per label=%s max_results=%d", label, limit)
        results = client.search_issues_by_label(label=label, max_results=limit)
    except Exception:  # pragma: no cover - dipende da Jira
        logger.exception(
            "Impossibile recuperare ticket Jira per l'etichetta %s.", label
        )
        return []
    payload = [result.to_dict() for result in results]
    linked = client.fetch_linked_issues(issue_keys=[r.key for r in results if r.key])
    if linked:
        payload.extend(res.to_dict() for res in linked)
    logger.info(
        "Recuperate %d issue Jira (incluse linked=%d) per l'etichetta %s.",
        len(payload),
        len(linked),
        label,
    )
    return payload


def default_jira_status() -> str:
    if getattr(chat_service, "jira_manual_approval", False):
        if jira_client_ready():
            return '⚠️ Jira è in modalità manuale: rivedi il project plan e premi "Crea user story su Jira".'
        return "⚠️ Jira è impostato sulla modalità manuale ma l'integrazione non è configurata."
    if jira_client_ready():
        return "ℹ️ Jira sincronizza automaticamente le user story approvate dal planner."
    return "ℹ️ Integrazione Jira non configurata."


def has_user_stories(plan_payload: Any) -> bool:
    if not plan_payload:
        return False
    if isinstance(plan_payload, ProjectPlan):
        stories = getattr(plan_payload, "user_stories", None)
    elif isinstance(plan_payload, Mapping):
        stories = plan_payload.get("user_stories")
    else:
        stories = None
    return bool(stories)


def coerce_project_plan(plan_payload: Any) -> ProjectPlan:
    if isinstance(plan_payload, ProjectPlan):
        return plan_payload
    if isinstance(plan_payload, Mapping):
        return ProjectPlan.from_payload(plan_payload)
    raise ValueError("Project plan non disponibile o di tipo non supportato.")


def build_jira_status(
    manual_required: bool,
    plan_has_stories: bool,
    has_results: bool,
) -> str:
    ready = jira_client_ready()
    if manual_required:
        if not ready:
            return "⚠️ Jira manuale attivo ma integrazione non configurata."
        if plan_has_stories and not has_results:
            return "⚠️ Jira attende la tua approvazione manuale."
        if has_results:
            return "✅ User story create su Jira."
        return "ℹ️ Jira manuale: nessuna user story disponibile."
    if has_results:
        return "✅ Jira sincronizzato automaticamente."
    if ready:
        return "ℹ️ Jira pronto: genera una richiesta per creare user story."
    return "ℹ️ Integrazione Jira disattivata o non configurata."


__all__ = [
    "build_jira_status",
    "coerce_project_plan",
    "default_jira_status",
    "get_jira_results_for_label",
    "has_user_stories",
    "jira_client_ready",
]
