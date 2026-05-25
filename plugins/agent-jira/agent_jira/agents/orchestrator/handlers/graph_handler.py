"""
Graph Flow Handler Module

Handles graph-based analysis flows including impact analysis and completeness checks.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .base import BaseFlowHandler

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class GraphFlowHandler(BaseFlowHandler):
    """
    Handles graph-based analysis flows.

    Flows:
    - Impact Analysis: Find entities affected by document changes
    - Completeness Check: Verify test coverage for epics
    """

    def handle_impact(
        self, query: str, session_id: Optional[str], history_turns: List[Any]
    ) -> Dict[str, Any]:
        """
        Execute impact analysis flow.

        Args:
            query: User's query
            session_id: Session identifier
            history_turns: Conversation history

        Returns:
            Response dictionary with impact analysis results
        """
        logger.info("Handling Impact Analysis Flow")

        if not self.graph_agent:
            answer = "⚠️ Funzionalità di analisi impatto non disponibile (GraphAgent disabilitato)."
            return {"answer": answer, "sources": [], "jira_manual_required": False}

        # Use RAG to find the most relevant document
        rag_state = self.rag_agent.retrieve_context(query)
        top_docs = rag_state.get("used_chunks", [])

        if not top_docs:
            return {
                "answer": "Non ho trovato documenti correlati per analizzare l'impatto.",
                "sources": [],
            }

        # Get document ID from top result
        best_doc = top_docs[0]
        doc_payload = getattr(best_doc, "payload", {})
        doc_id = doc_payload.get("document_id") or doc_payload.get("path")

        if not doc_id:
            return {
                "answer": "Impossibile identificare il documento target per l'analisi.",
                "sources": [],
            }

        # Perform impact analysis
        report = self.graph_agent.get_impact_analysis(doc_id)

        if report["status"] != "success":
            return {
                "answer": f"Errore durante analisi impatto: {report.get('message')}",
                "sources": [],
            }

        # Build response
        impacted = report.get("impacted_entities", [])
        answer = f"🔍 **Analisi Impatto per**: `{doc_id}`\n\n"

        if not impacted:
            answer += (
                "Nessuna User Story sembra dipendere direttamente da questo documento."
            )
        else:
            answer += f"Trovate **{len(impacted)}** Storie impattate:\n"
            for item in impacted:
                answer += f"- **{item['id']}** ({item['status']}): {item['summary']}\n"

        return {"answer": answer, "sources": [], "jira_manual_required": False}

    def handle_completeness(
        self, query: str, session_id: Optional[str], history_turns: List[Any]
    ) -> Dict[str, Any]:
        """
        Execute completeness check flow.

        Args:
            query: User's query
            session_id: Session identifier
            history_turns: Conversation history

        Returns:
            Response dictionary with completeness check results
        """
        logger.info("Handling Completeness Check Flow")

        if not self.graph_agent:
            answer = "⚠️ Funzionalità di analisi completezza non disponibile (GraphAgent disabilitato)."
            return {"answer": answer, "sources": [], "jira_manual_required": False}

        # Extract epic ID from query
        match = re.search(r"([A-Z]+-\d+)", query.upper())
        epic_id = match.group(1) if match else None

        if not epic_id:
            logger.info("Epic ID missing in completeness check. Suggesting projects.")
            projects = self.jira_agent.get_available_projects()
            project_list_str = ""
            suggested_actions = []
            if projects:
                project_list_str = "\nPROGETTI DISPONIBILI:\n" + "\n".join(
                    f"- {p.get('name')} ({p.get('key')})" for p in projects
                )
                # Suggest clicking to search epics for a project
                suggested_actions = [
                    {
                        "label": f"Epiche di {p.get('key')}",
                        "payload": f"Mostra le epiche del progetto {p.get('key')}",
                    }
                    for p in projects[:5]  # Limit to 5
                ]

            answer = (
                "⚠️ Non hai specificato la chiave dell'Epica (es. PROJ-1) per l'analisi della completezza.\n"
                f"{project_list_str}\n\n"
                "Per favore, specifica un codice Epica valido."
            )
            return {
                "answer": answer,
                "sources": [],
                "suggested_actions": suggested_actions,
            }

        # Perform completeness check
        report = self.graph_agent.get_completeness_report(epic_id)

        if report["status"] != "success":
            return {
                "answer": f"Errore durante analisi completezza: {report.get('message')}",
                "sources": [],
            }

        # Build response
        pct = report.get("coverage_pct", 0)
        answer = f"📊 **Report Completezza per {epic_id}**\n\n"

        # Status Badge
        status_icon = "🟢" if pct == 100 else "🟡" if pct > 50 else "🔴"
        answer += f"{status_icon} **Copertura Test**: {pct:.1f}% ({report.get('covered_stories')}/{report.get('total_stories')} storie coperte)\n\n"

        details = report.get("details", [])
        if details:
            answer += "**Dettagli Storie:**\n"
            for d in details:
                icon = "✅" if d["covered"] else "⚠️"
                warning = " (Nessun test collegato)" if not d["covered"] else ""
                answer += f"- {icon} **{d['story_id']}**: {d['test_count']} test cases{warning}\n"
        else:
            answer += "ℹ️ Nessuna storia trovata collegata a questa epica."

        return {"answer": answer, "sources": [], "jira_manual_required": False}
