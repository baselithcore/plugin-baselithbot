from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from agent_jira.agents.orchestrator.flow_handlers import (
    GlobalAnalysisFlowHandler,
    GraphFlowHandler,
    JiraFlowHandler,
    RAGFlowHandler,
    SystemFlowHandler,
)

# Import modular components
from agent_jira.agents.orchestrator.intent_classifier import IntentClassifier
from agent_jira.agents.orchestrator.persistence import PersistenceManager
from agent_jira.agents.orchestrator.streaming_handlers import (
    GlobalAnalysisStreamHandler,
    JiraStreamHandler,
    RAGStreamHandler,
    SystemStreamHandler,
)
from agent_jira.models import ChatRequest

if TYPE_CHECKING:
    from agent_jira.agents.graph_agent import GraphAgent
    from agent_jira.chat.service import ChatService

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Agente coordinatore che gestisce l'interazione con l'utente,
    identifica l'intento e delega ai sotto-agenti specializzati (RAG, Jira).

    Refactored to use modular components for better maintainability and scalability.
    """

    def __init__(
        self, service: ChatService, graph_agent: Optional[GraphAgent] = None
    ) -> None:
        from agent_jira.agents.generator_agent import GeneratorAgent
        from agent_jira.agents.graph_agent import GraphAgent
        from agent_jira.agents.jira_agent import JiraAgent
        from agent_jira.agents.rag_agent import RAGAgent
        from agent_jira.graphdb import graph_db

        self.service = service
        self.history_manager = service.history_manager

        # Initialize graph agent
        if graph_agent is None and graph_db.is_enabled():
            self.graph_agent = GraphAgent(graph_db)
        else:
            self.graph_agent = graph_agent

        # Initialize specialized agents
        self.rag_agent = RAGAgent(service)
        self.jira_agent = JiraAgent(service, graph_agent=self.graph_agent)
        self.generator_agent = GeneratorAgent(service)

        # Initialize Audit Agent (Optional)
        from agent_jira.config import AUDIT_ENABLED

        self.audit_agent = None
        if AUDIT_ENABLED:
            from agent_jira.agents.audit_agent import AuditAgent

            self.audit_agent = AuditAgent(service)
            logger.info("AuditAgent initialized and enabled.")

        # Initialize modular components
        self.intent_classifier = IntentClassifier()

        self.rag_flow = RAGFlowHandler(
            service,
            self.rag_agent,
            self.jira_agent,
            self.generator_agent,
            self.graph_agent,
        )
        self.jira_flow = JiraFlowHandler(
            service,
            self.rag_agent,
            self.jira_agent,
            self.generator_agent,
            self.graph_agent,
        )
        self.graph_flow = GraphFlowHandler(
            service,
            self.rag_agent,
            self.jira_agent,
            self.generator_agent,
            self.graph_agent,
        )

        self.system_flow = SystemFlowHandler(
            service, self.rag_agent, self.jira_agent, self.generator_agent
        )
        self.global_flow = GlobalAnalysisFlowHandler(
            service, self.rag_agent, self.generator_agent
        )

        self.rag_stream = RAGStreamHandler(
            service, self.rag_agent, self.generator_agent
        )
        self.jira_stream = JiraStreamHandler(
            service, self.rag_agent, self.jira_agent, self.generator_agent
        )
        self.system_stream = SystemStreamHandler(
            service, self.rag_agent, self.generator_agent
        )
        self.global_stream = GlobalAnalysisStreamHandler(
            service, self.rag_agent, self.generator_agent
        )

        self.persistence = PersistenceManager(service)

        logger.info("OrchestratorAgent initialized (Multi-Agent System ready).")

    def handle_user_message(self, request: ChatRequest) -> Dict[str, Any]:
        """
        Gestisce il messaggio dell'utente orchestrando il flusso (sync).
        """
        user_input = request.query
        session_id = request.conversation_id

        logger.info(
            "Orchestrator received message. Session: %s. Query len: %d",
            session_id,
            len(user_input),
        )

        # 1. Load History
        history_turns = []
        history_text = ""
        if session_id:
            history_turns, history_text = self.history_manager.load(session_id)

        # 2. Intent Detection
        intent = self.intent_classifier.classify(user_input)

        # 3. Routing to appropriate flow handler
        if intent == "jira_generation":
            result = self.jira_flow.handle(
                user_input,
                history_text,
                history_turns,
                session_id,
                kb_label=request.kb_label,
            )
        elif intent == "graph_impact":
            result = self.graph_flow.handle_impact(
                user_input, session_id, history_turns
            )
        elif intent == "graph_completeness":
            result = self.graph_flow.handle_completeness(
                user_input, session_id, history_turns
            )
        elif intent == "system_status":
            result = self.system_flow.handle(
                user_input, history_text, history_turns, session_id
            )
        elif intent == "global_analysis":
            result = self.global_flow.handle(
                user_input, history_text, history_turns, session_id
            )
        else:  # qa_docs
            result = self.rag_flow.handle(
                user_input,
                history_text,
                history_turns,
                kb_label=request.kb_label,
            )

        # 4. Persist interaction
        self.persistence.persist_interaction(
            session_id,
            history_turns,
            user_input,
            result["answer"],
            result.get("sources", []),
            jira_issues=result.get("jira_issues"),
        )

        # 5. Audit Interaction (Non-blocking)
        self._audit_interaction(user_input, result["answer"], session_id)

        return result

    def handle_user_message_stream(self, request: ChatRequest):
        """
        Gestisce il messaggio dell'utente orchestrando il flusso (streaming).
        Yields JSON-structured events.
        """
        user_input = request.query
        session_id = request.conversation_id

        logger.info("Orchestrator (Stream) received message.")

        # 1. Load History
        history_turns = []
        history_text = ""
        if session_id:
            history_turns, history_text = self.history_manager.load(session_id)

        # 2. Intent Detection
        intent = self.intent_classifier.classify(user_input)

        # 3. Routing to appropriate streaming handler
        final_data = None

        if intent == "jira_generation":
            for event_str in self.jira_stream.handle(
                user_input, history_text, history_turns, kb_label=request.kb_label
            ):
                yield event_str
                try:
                    data = json.loads(event_str)
                    if data.get("event_type") == "final_payload":
                        final_data = data
                except Exception:
                    pass

        elif intent in ["graph_impact", "graph_completeness"]:
            # Wrap sync graph results in structured events for consistency
            if intent == "graph_impact":
                result = self.graph_flow.handle_impact(
                    user_input, session_id, history_turns
                )
            else:
                result = self.graph_flow.handle_completeness(
                    user_input, session_id, history_turns
                )

            final_data = {
                "event_type": "final_payload",
                "answer": result["answer"],
                "sources": result.get("sources", []),
                "jira_issues": result.get("jira_issues", []),
                "created_jira_issues": result.get("created_jira_issues", []),
            }
            yield json.dumps(final_data)

        elif intent == "system_status":
            for event_str in self.system_stream.handle(
                user_input, history_text, history_turns
            ):
                yield event_str
                try:
                    data = json.loads(event_str)
                    if data.get("event_type") == "final_payload":
                        final_data = data
                except Exception:
                    pass

        elif intent == "global_analysis":
            for event_str in self.global_stream.handle(
                user_input, history_text, history_turns
            ):
                yield event_str
                try:
                    data = json.loads(event_str)
                    if data.get("event_type") == "final_payload":
                        final_data = data
                except Exception:
                    pass

        else:  # qa_docs
            for event_str in self.rag_stream.handle(
                user_input,
                history_text,
                history_turns,
                kb_label=request.kb_label,
            ):
                yield event_str
                try:
                    data = json.loads(event_str)
                    if data.get("event_type") == "final_payload":
                        final_data = data
                except Exception:
                    pass

        # 4. Persistence & Audit (after stream finishes)
        if final_data:
            ans = final_data.get("answer", "")
            srcs = final_data.get("sources", [])
            issues = final_data.get("jira_issues", [])

            self.persistence.persist_interaction(
                session_id, history_turns, user_input, ans, srcs, jira_issues=issues
            )
            self._audit_interaction(user_input, ans, session_id)

    def _audit_interaction(
        self, query: str, response: str, session_id: Optional[str]
    ) -> None:
        """Run audit agent if enabled."""
        if self.audit_agent:
            try:
                # Fire-and-forget logic (sync for now as it uses heuristics)
                report = self.audit_agent.evaluate_interaction(query, response)
                if not report.is_safe:
                    logger.warning(
                        f"AUDIT ALERT [Session: {session_id}]: Risk Score {report.risk_score}. "
                        f"Issues: {[i.message for i in report.issues]}"
                    )
            except Exception:
                logger.error("Audit processing failed", exc_info=True)
