"""
Persistence Manager Module

Handles conversation history persistence and telemetry tracking.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from agent_jira.telemetry import telemetry

if TYPE_CHECKING:
    from agent_jira.chat.service import ChatService

logger = logging.getLogger(__name__)


class PersistenceManager:
    """
    Manages persistence of conversation history and telemetry metrics.

    Responsibilities:
    - Save conversation turns to history
    - Update telemetry metrics
    - Track source documents for boosting in subsequent queries
    - Manage session metadata (e.g., Jira issues)
    """

    def __init__(self, service: ChatService) -> None:
        """
        Initialize the persistence manager.

        Args:
            service: ChatService instance for accessing history manager
        """
        self.service = service
        self.history_manager = service.history_manager

    def persist_interaction(
        self,
        session_id: Optional[str],
        history_turns: List[Any],
        query: str,
        answer: str,
        sources: List[Dict],
        jira_issues: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Saves the conversation turn and updates metrics.

        Args:
            session_id: Conversation session identifier
            history_turns: Existing conversation history
            query: User's query
            answer: Agent's answer
            sources: Source documents used
            jira_issues: Optional list of related Jira issues
        """
        if not session_id or not answer:
            return

        # Prepare metadata
        metadata = {}
        if jira_issues:
            metadata["jira_issues"] = jira_issues
        if sources:
            metadata["sources"] = sources

        # Save conversation turn
        self.history_manager.append_turn(
            session_id, history_turns, query, answer, metadata=metadata
        )
        telemetry.increment("history.turn_appended")

        # Track source documents for boosting in next turns
        # Service maintains _last_sources cache for relevance boosting
        if sources:
            doc_ids = set()
            for src in sources:
                val = src.get("document_id")
                if val:
                    doc_ids.add(val)

            if doc_ids and hasattr(self.service, "_last_sources"):
                self.service._last_sources[session_id] = doc_ids

        logger.debug(
            "Persisted interaction for session %s. Sources: %d, Jira issues: %d",
            session_id,
            len(sources),
            len(jira_issues) if jira_issues else 0,
        )
