"""
System Flow Handler Module

Handles exact queries about system status and document metadata.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from agent_jira.ui.documents import list_kb_documents

from ..events import FinalPayloadEvent, StatusEvent, TokenEvent, format_event
from .base import BaseFlowHandler

if TYPE_CHECKING:
    from agent_jira.agents.generator_agent import GeneratorAgent
    from agent_jira.agents.rag_agent import RAGAgent
    from agent_jira.chat.service import ChatService

logger = logging.getLogger(__name__)


class SystemFlowHandler(BaseFlowHandler):
    """
    Gestisce la flow listando i metadati del sistema e delegando
    la sintesi testuale al GeneratorAgent in modo sincrono.
    """

    def handle(
        self,
        query: str,
        history_text: str,
        history_turns: List[Dict[str, str]],
        session_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        logger.info("SystemFlowHandler: extracting system document statistics.")

        docs = list_kb_documents()
        doc_count = len(docs)

        # Build deterministic context
        context = (
            f"Statistiche di Sistema Interne:\n"
            f"Numero totale di documenti indicizzati e presenti in Knowledge Base: {doc_count}\n"
        )
        if doc_count > 0:
            context += "Elenco file:\n" + "\n".join([f"- {d}" for d in docs])
        else:
            context += "Nessun file presente.\n"

        context += "\nUsa queste statistiche interne per rispondere alla domanda dell'utente in modo preciso."

        answer = "Le informazioni di sistema non sono disponibili in questo momento."
        if self.generator_agent:
            answer = self.generator_agent.synthesize(query, context, history_text)

        sources = []
        if doc_count > 0:
            sources = [
                {
                    "document_id": "SystemMetadata",
                    "content": f"Elenco file:\n{', '.join(docs[:10])}{' ...' if doc_count > 10 else ''}",
                    "has_linked_jira": False,
                }
            ]

        return {
            "answer": answer,
            "sources": sources,
            "jira_issues": [],
        }


class SystemStreamHandler:
    """
    Gestisce la flow listando i metadati del sistema e delegando
    la sintesi testuale in streaming al GeneratorAgent.
    """

    def __init__(
        self,
        service: ChatService,
        rag_agent: RAGAgent,
        generator_agent: GeneratorAgent,
    ) -> None:
        self.service = service
        self.rag_agent = rag_agent
        self.generator_agent = generator_agent

    def handle(
        self,
        query: str,
        history_text: str,
        history_turns: List[Dict[str, str]],
    ):
        logger.info(
            "SystemStreamHandler: extracting system document statistics (streaming)."
        )

        docs = list_kb_documents()
        doc_count = len(docs)

        # Provide an early status for the frontend
        yield format_event(
            StatusEvent(message="Lettura stato del sistema...", agent="system")
        )

        context = (
            f"Statistiche di Sistema Interne:\n"
            f"Numero totale di documenti indicizzati e presenti in Knowledge Base: {doc_count}\n"
        )
        if doc_count > 0:
            context += "Elenco file:\n" + "\n".join([f"- {d}" for d in docs])
        else:
            context += "Nessun file presente.\n"

        context += "\nUsa queste statistiche interne per rispondere alla domanda dell'utente in modo preciso."

        answer_chunks = []
        if self.generator_agent:
            for chunk in self.generator_agent.synthesize_stream(
                query, context, history_text
            ):
                answer_chunks.append(chunk)
                yield format_event(TokenEvent(text=chunk))

        answer = "".join(answer_chunks)

        sources = []
        if doc_count > 0:
            sources = [
                {
                    "document_id": "SystemMetadata",
                    "content": f"Elenco di {doc_count} file analizzati dal sistema.",
                    "has_linked_jira": False,
                }
            ]

        yield format_event(
            FinalPayloadEvent(
                answer=answer,
                sources=sources,
                jira_issues=[],
                created_jira_issues=[],
            )
        )
