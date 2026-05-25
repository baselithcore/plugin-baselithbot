"""
Global Analysis Flow Handler Module

Handles map-reduce logic for performing global summaries across all documents.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional

from agent_jira.ui.documents import (
    list_kb_documents,
    load_uploaded_document,
    resolve_kb_document,
)

from ..events import (
    ErrorEvent,
    FinalPayloadEvent,
    StatusEvent,
    TokenEvent,
    format_event,
)

if TYPE_CHECKING:
    from agent_jira.agents.generator_agent import GeneratorAgent
    from agent_jira.agents.rag_agent import RAGAgent
    from agent_jira.chat.service import ChatService

logger = logging.getLogger(__name__)


class GlobalAnalysisFlowHandler:
    """Handles global analysis flow (sync)."""

    def __init__(
        self,
        service: ChatService,
        rag_agent: RAGAgent,
        generator_agent: Optional[GeneratorAgent] = None,
    ) -> None:
        self.service = service
        self.rag_agent = rag_agent
        self.generator_agent = generator_agent

    def handle(
        self,
        query: str,
        history_text: str,
        history_turns: List[Any],
        session_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        logger.info("GlobalAnalysisFlowHandler: Map-Reduce execution.")

        docs = list_kb_documents()
        doc_count = len(docs)

        if doc_count == 0:
            return {
                "answer": "Nessun documento trovato per l'analisi globale.",
                "sources": [],
                "jira_manual_required": False,
            }

        summaries = []
        for doc_name in docs:
            try:
                doc_path = resolve_kb_document(doc_name)
                text, _ = load_uploaded_document(str(doc_path))

                if self.generator_agent and len(text) > 0:
                    summary_query = "Estrai e decodifica i concetti principali dal seguente testo in un riassunto tecnico conciso (max 150 parole)."
                    # Map phase
                    local_summary = self.generator_agent.synthesize(
                        summary_query, text[:15000], ""
                    )
                    summaries.append(
                        f"Documento: {doc_name}\nRiassunto Base: {local_summary}\n"
                    )
            except Exception as e:
                logger.warning(f"Failed to summarize document {doc_name}: {e}")

        combined_context = "\n---\n".join(summaries)
        reduce_context = (
            "Ti sto passando un dizionario di sintesi globali ricavati da TUTTI i file indicizzati. "
            "Usa questi frammenti, che assieme compongono una visione globale di tutto il contesto, "
            "per rispondere accuratamente alla seguente domanda e fare confronti.\n\n"
            f"CONTESTI GLOBALI:\n{combined_context}"
        )

        answer = "I dettagli non sono disponibili al momento."
        if self.generator_agent:
            answer = self.generator_agent.synthesize(
                query, reduce_context, history_text
            )

        sources = [
            {
                "document_id": "GlobalMapReduce",
                "content": f"Elaborati interi {doc_count} documenti per formare l'analisi globale.",
                "has_linked_jira": False,
            }
        ]

        return {
            "answer": answer,
            "sources": sources,
            "jira_manual_required": False,
        }


class GlobalAnalysisStreamHandler:
    """Handles global analysis flow (streaming)."""

    def __init__(
        self,
        service: ChatService,
        rag_agent: RAGAgent,
        generator_agent: Optional[GeneratorAgent] = None,
    ) -> None:
        self.service = service
        self.rag_agent = rag_agent
        self.generator_agent = generator_agent

    def handle(
        self,
        query: str,
        history_text: str,
        history_turns: List[Any],
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        t_total = time.perf_counter()
        logger.info("GlobalAnalysisStreamHandler: starting Map-Reduce.")

        if not self.generator_agent:
            yield format_event(ErrorEvent(message="GeneratorAgent missing."))
            return

        docs = list_kb_documents()
        doc_count = len(docs)

        if doc_count == 0:
            yield format_event(
                FinalPayloadEvent(
                    answer="Nessun documento indicizzato per una meta-analisi globale.",
                    sources=[],
                )
            )
            return

        yield format_event(
            StatusEvent(
                message=f"Preparazione alla lettura globale di {doc_count} documenti...",
                step="map",
                agent="global",
            )
        )

        # Map phase
        summaries = []
        for index, doc_name in enumerate(docs, start=1):
            yield format_event(
                StatusEvent(
                    message=f"Sintesi file ({index}/{doc_count}): {doc_name}",
                    step="map",
                    agent="global",
                )
            )
            try:
                doc_path = resolve_kb_document(doc_name)
                text, _ = load_uploaded_document(str(doc_path))

                if len(text) > 0:
                    summary_query = "Estrai e decodifica i concetti principali dal seguente testo in un riassunto tecnico conciso (max 150 parole)."
                    # Map phase
                    local_summary = self.generator_agent.synthesize(
                        summary_query, text[:15000], ""
                    )
                    summaries.append(
                        f"Documento: {doc_name}\nRiassunto Base: {local_summary}\n"
                    )
            except Exception as e:
                logger.warning(f"Failed to summarize document {doc_name}: {e}")

        yield format_event(
            StatusEvent(
                message="Creazione del quadro generale in corso...",
                step="reduce",
                agent="global",
            )
        )

        combined_context = "\n---\n".join(summaries)
        reduce_context = (
            "Ti sto passando un dizionario di sintesi concettuali ricavate da TUTTI i file presenti. "
            "Usa questi frammenti, che formano l'orizzonte completo della knowledge base, "
            "per rispondere accuratamente alla richiesta globale dell'utente (potrebbe essere una comparazione, "
            "una sintesi o l'estrazione di relazioni).\n\n"
            f"=== CONTESTI GLOBALI DEI FILE ===\n{combined_context}"
        )

        # Reduce stream
        full_answer = []
        for chunk in self.generator_agent.synthesize_stream(
            query, reduce_context, history_text
        ):
            full_answer.append(chunk)
            yield format_event(TokenEvent(text=chunk))

        sources = [
            {
                "document_id": "GlobalMapReduce",
                "content": f"Lette e riassunte a caldo {doc_count} entità di knowledge base.",
                "has_linked_jira": False,
            }
        ]

        yield format_event(
            FinalPayloadEvent(
                answer="".join(full_answer),
                sources=sources,
                duration=time.perf_counter() - t_total,
            )
        )
