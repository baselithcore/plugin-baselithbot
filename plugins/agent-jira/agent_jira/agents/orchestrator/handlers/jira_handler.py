"""
Jira Flow Handler Module

Handles Jira ticket creation flow with project detection, context retrieval,
backlog generation, and Jira synchronization.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from agent_jira.kb_labels import build_kb_label
from agent_jira.project_manager.story_count import parse_requested_story_count

from .base import BaseFlowHandler

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class JiraFlowHandler(BaseFlowHandler):
    """
    Handles Jira ticket creation flow.

    Flow: Detect project -> Retrieve context -> Generate backlog -> Sync to Jira
    """

    def handle(
        self,
        query: str,
        history_text: str,
        history_turns: List[Any],
        session_id: Optional[str],
        kb_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute Jira flow for ticket creation.

        Args:
            query: User's request
            history_text: Conversation history as text
            history_turns: Structured conversation history
            session_id: Session identifier
            kb_label: Optional knowledge base label

        Returns:
            Response dictionary with answer, sources, backlog, and Jira issues
        """
        logger.info("Starting Jira flow.")

        # 0. Check Project Context
        project_key = self.jira_agent.detect_project_context(query, history="")
        if not project_key:
            return self._handle_missing_project(query)

        logger.info(f"Using Jira project: {project_key}")

        # 1. Retrieve Context via RAG
        rag_result = self.rag_agent.retrieve_context(
            query,
            history=history_text,
            history_turns=history_turns,
            project_key=project_key,
            kb_label=kb_label,
        )

        # Build context from chunks
        context_text = self._build_context_from_rag(rag_result)

        # Extract doc sources for graph linking
        doc_sources = rag_result.get("sources", [])
        logger.info(
            f"DEBUG JiraFlowHandler: Extracted {len(doc_sources)} doc_sources from RAG"
        )
        logger.info(f"DEBUG JiraFlowHandler: doc_sources = {doc_sources}")

        # Extract max stories requested
        max_stories = self._extract_max_stories(query)
        if max_stories:
            logger.info(f"User requested {max_stories} stories.")

        logger.info(
            "Context retrieved for planner. Chunks: %d. Context len: %d",
            len(rag_result.get("used_chunks", [])),
            len(context_text),
        )

        # 2. Generate Backlog Plan
        plan = self.jira_agent.generate_backlog(
            goal=query,
            context=context_text,
            history=history_text,
            jira_project_key=project_key,
            max_stories=max_stories,
        )

        # 2.1 Infer kb_label from sources if missing
        kb_label = self._infer_kb_label(rag_result, kb_label)

        # 3. Synchronize with Jira
        logger.info(
            f"DEBUG JiraFlowHandler: Calling sync_backlog_to_jira with {len(doc_sources)} sources"
        )
        jira_results = self.jira_agent.sync_backlog_to_jira(
            backlog=plan,
            project_key=project_key,
            kb_label=kb_label,
            doc_sources=doc_sources,
        )

        # 4. Build Final Response
        answer = self._build_jira_response(project_key, jira_results)
        final_jira_list = self._collect_jira_issues(kb_label, rag_result, jira_results)

        logger.info(
            "Jira flow complete. Created: %d tickets",
            len([r for r in jira_results if not r.get("error")]),
        )

        return {
            "answer": answer,
            "sources": rag_result.get("sources"),
            "project_plan": plan,
            "jira_issues": final_jira_list,
            "created_jira_issues": [
                issue
                for issue in jira_results
                if issue.get("key") or issue.get("error")
            ],
            "jira_manual_required": False,
        }

    def _handle_missing_project(self, query: str) -> Dict[str, Any]:
        """
        Handle case where project context is missing.

        Args:
            query: The original user query, used to preserve intent in suggested actions.
        """
        logger.info("Jira project context missing. Asking user.")
        projects = self.jira_agent.get_available_projects()

        suggested_actions = []
        project_list_str = ""
        if projects:
            project_list_str = "\nPROGETTI DISPONIBILI:\n" + "\n".join(
                f"- {p.get('name')} ({p.get('key')})" for p in projects
            )
            # Use dynamic payload to preserve original intent
            suggested_actions = [
                {
                    "label": f"{p.get('name')} ({p.get('key')})",
                    "payload": f"{query} per il progetto {p.get('key')}",
                }
                for p in projects
            ]

        answer = (
            "⚠️ Non hai specificato su quale progetto Jira vuoi creare le user stories.\n\n"
            "Per favore, indicami il nome o la chiave del progetto nella tua richiesta.\n"
            f"{project_list_str}\n\n"
            f'Esempio: "Crea storie per il progetto {projects[0]["key"] if projects else "MIO_PROGETTO"}".'
        )

        return {
            "answer": answer,
            "sources": [],
            "project_plan": None,
            "jira_issues": [],
            "created_jira_issues": [],
            "jira_manual_required": False,
            "suggested_actions": suggested_actions,
        }

    def _extract_max_stories(self, query: str) -> Optional[int]:
        """Extract requested number of stories from query."""
        requested = parse_requested_story_count(query, default=None)
        if requested is not None:
            logger.info("User requested %d stories.", requested)
        return requested

    def _build_context_from_rag(self, rag_result: Dict[str, Any]) -> str:
        """Build context text from RAG result."""
        chunks = rag_result.get("used_chunks", [])
        context_parts = []
        for c in chunks:
            payload = getattr(c, "payload", {}) or {}
            text = payload.get("text") or payload.get("chunk_body")
            if text:
                context_parts.append(text)

        context_text = "\n\n".join(context_parts)

        # Use explicit context from RAG if available
        return (
            rag_result.get("context", "")
            or context_text
            or rag_result.get("answer", "")
        )

    def _infer_kb_label(
        self, rag_result: Dict[str, Any], kb_label: Optional[str]
    ) -> Optional[str]:
        """Infer KB label from sources with weighted voting."""
        label_weights = Counter()

        for src in rag_result.get("sources", []):
            path_str = src.get("path") or src.get("relative_path")
            if path_str:
                try:
                    lbl = build_kb_label(Path(path_str))
                    if lbl:
                        weight = src.get("chunks_used", 1)
                        label_weights[lbl] += weight
                        logger.debug(
                            f"Source: {path_str}, Label: {lbl}, Weight: {weight}"
                        )
                except Exception:
                    pass

        if label_weights:
            inferred_label = label_weights.most_common(1)[0][0]
            if inferred_label != kb_label:
                logger.info(
                    f"Overwriting kb_label '{kb_label}' with inferred '{inferred_label}' "
                    f"(weights: {dict(label_weights)})"
                )
                return inferred_label
            else:
                logger.info(
                    f"Confirmed kb_label: {kb_label} (weights: {dict(label_weights)})"
                )
                return kb_label
        else:
            logger.info(f"No kb_label inferred from sources. keeping: {kb_label}")
            return kb_label

    def _build_jira_response(
        self, project_key: str, jira_results: List[Dict[str, Any]]
    ) -> str:
        """Build response message for Jira flow."""
        count_created = len([r for r in jira_results if not r.get("error")])
        count_failed = len(jira_results) - count_created

        answer = f"Ho analizzato la richiesta per il progetto **{project_key}** e generato il backlog."
        if count_created > 0:
            answer += f"\n\n✅ Creati {count_created} ticket su Jira."
        if count_failed > 0:
            answer += f"\n\n⚠️ {count_failed} ticket non creati per errori."

        if not jira_results:
            answer += "\n\nNessun ticket generato (forse il piano non conteneva user stories valide)."
            return answer

        created_refs = []
        for issue in jira_results:
            key = issue.get("key")
            if not key or issue.get("error"):
                continue
            summary = issue.get("summary") or "Senza titolo"
            url = issue.get("url")
            if url:
                created_refs.append(f"- [{key}]({url}) - {summary}")
            else:
                created_refs.append(f"- {key} - {summary}")
        if created_refs:
            answer += "\n\nRiferimenti Jira creati:\n" + "\n".join(created_refs)

        return answer

    def _collect_jira_issues(
        self,
        kb_label: Optional[str],
        rag_result: Dict[str, Any],
        jira_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Collect all Jira issues from various sources."""
        final_jira_list = []
        seen_keys = set()

        # 1. Global Search by KB Label (if available)
        if kb_label:
            logger.info(f"Performing global Jira search for label: {kb_label}")
            global_issues = self.jira_agent.search_issues_by_label(kb_label)
            for issue in global_issues:
                k = issue.get("key")
                if k and k not in seen_keys:
                    final_jira_list.append(issue)
                    seen_keys.add(k)

        # 2. Add current RAG issues
        for issue in rag_result.get("jira_issues", []):
            k = issue.get("key")
            if k and k not in seen_keys:
                final_jira_list.append(issue)
                seen_keys.add(k)

        # 3. Add newly created issues
        for issue in jira_results:
            k = issue.get("key")
            if k and k not in seen_keys:
                final_jira_list.append(issue)
                seen_keys.add(k)

        return final_jira_list
