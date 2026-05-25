"""
RAG Flow Handler Module

Handles standard RAG (Retrieval-Augmented Generation) flow for Q&A.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .base import BaseFlowHandler

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RAGFlowHandler(BaseFlowHandler):
    """
    Handles standard RAG (Retrieval-Augmented Generation) flow.

    Flow: Retrieve relevant documents -> Generate answer
    """

    def handle(
        self,
        query: str,
        history_text: str,
        history_turns: List[Any],
        kb_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute RAG flow for Q&A.

        Args:
            query: User's question
            history_text: Conversation history as text
            history_turns: Structured conversation history

        Returns:
            Response dictionary with answer, sources, and metadata
        """
        logger.info("Starting RAG flow.")

        if self.generator_agent is None:
            logger.error("GeneratorAgent not initialized in RAGFlowHandler")
            return {"answer": "Error: GeneratorAgent missing.", "sources": []}

        # 1. Retrieval Phase
        retrieval_result = self.rag_agent.retrieve_context(
            query,
            history=history_text,
            history_turns=history_turns,
            kb_label=kb_label,
        )
        context = retrieval_result.get("context", "")
        sources = retrieval_result.get("sources", [])

        # 2. Synthesis Phase
        answer = self.generator_agent.synthesize(
            query=query, context=context, history=history_text
        )

        logger.info(
            "RAG flow complete. Answer len: %d. Sources: %d", len(answer), len(sources)
        )

        return {
            "answer": answer,
            "sources": sources,
            "source_metrics": {},
            "project_plan": None,
            "jira_issues": retrieval_result.get("jira_issues", []),
            "jira_manual_required": False,
        }
