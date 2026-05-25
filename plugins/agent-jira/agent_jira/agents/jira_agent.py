from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from agent_jira.integrations.jira.tenant_resolver import get_tenant_jira_client
from agent_jira.telemetry import telemetry

from .jira.context import detect_project_context
from .jira.intent import create_intelligent_relationships
from .jira.sync import sync_backlog_to_jira

if TYPE_CHECKING:
    from agent_jira.agents.graph_agent import GraphAgent
    from agent_jira.chat.service import ChatService
    from agent_jira.integrations.jira.client import JiraClient

logger = logging.getLogger(__name__)


class JiraAgent:
    """
    Agente responsabile della pianificazione (Project Planner) e dell'integrazione con Jira.
    Genera backlog, user stories e test cases, e li sincronizza con Jira.
    """

    def __init__(
        self, service: ChatService, graph_agent: Optional[GraphAgent] = None
    ) -> None:
        self.service = service
        self.graph_agent = graph_agent

    def _resolve_jira_client(self) -> Optional["JiraClient"]:
        fallback = getattr(self.service, "jira_client", None)
        return get_tenant_jira_client(fallback_client=fallback)

    def detect_project_context(self, query: str, history: str = "") -> Optional[str]:
        """
        Tenta di identificare il progetto Jira dal contesto della conversazione.
        """
        available_projects = self.get_available_projects()
        return detect_project_context(
            query=query, available_projects=available_projects, history=history
        )

    def get_available_projects(self) -> List[Dict[str, str]]:
        """Restituisce la lista dei progetti Jira disponibili."""
        jira_client = self._resolve_jira_client()
        if jira_client is not None and hasattr(jira_client, "list_projects"):
            try:
                return jira_client.list_projects()
            except Exception:
                logger.error("Error listing Jira projects", exc_info=True)
                return []
        return []

    def generate_backlog(
        self,
        context: str,
        goal: str,
        history: str = "",
        jira_project_key: Optional[str] = None,
        max_stories: Optional[int] = None,
        include_tests: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Genera un piano di progetto (backlog) basato sul contesto fornito e sull'obiettivo.
        """
        planner = getattr(self.service, "project_planner", None)
        if planner is None:
            logger.warning("Project Planner non configurato nel servizio.")
            return {"error": "Project Planner disabled"}

        try:
            plan = planner.generate_plan(
                query=goal,
                context=context,
                history_text=history,
                jira_project_key=jira_project_key,
                max_stories=max_stories,
                include_tests=include_tests,
            )
            telemetry.increment("planner.generated")
            return plan.to_dict()
        except Exception as exc:
            telemetry.increment("planner.error")
            logger.exception("Errore generazione backlog")
            return {"error": str(exc)}

    def search_issues_by_label(
        self, label: str, max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Cerca issue Jira globalmente per label (es. doc-hash)."""
        jira_client = self._resolve_jira_client()
        if jira_client and hasattr(jira_client, "search_issues_by_label"):
            try:
                results = jira_client.search_issues_by_label(
                    label=label, max_results=max_results
                )
                return [r.__dict__ for r in results]
            except Exception:
                logger.error(f"Error searching issues by label {label}", exc_info=True)
                return []
        return []

    def sync_backlog_to_jira(
        self,
        backlog: Dict[str, Any],
        doc_sources: Optional[List[Dict[str, Any]]] = None,
        kb_label: Optional[str] = None,
        project_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Sincronizza il backlog su Jira e GraphDB.
        """
        jira_client = self._resolve_jira_client()
        if jira_client is None or not jira_client.is_ready():
            logger.warning("Jira Client non pronto o disabilitato.")
            return [{"error": "Jira disabled"}]

        return sync_backlog_to_jira(
            backlog=backlog,
            jira_client=jira_client,
            graph_agent=self.graph_agent,
            doc_sources=doc_sources,
            kb_label=kb_label,
            project_key=project_key,
            create_intelligent_relationships_callback=self._create_intelligent_relationships,
        )

    def _create_intelligent_relationships(self, stories: List) -> None:
        """
        Detect and create intelligent relationships between user stories.
        """
        create_intelligent_relationships(stories=stories, graph_agent=self.graph_agent)
