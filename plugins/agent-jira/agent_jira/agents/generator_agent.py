from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Generator, Optional

from agent_jira.chat.agent_state import AgentState
from agent_jira.chat.prompt import build_prompt
from agent_jira.chat.workflow_response import ResponseGenerator
from agent_jira.llm import generate_response
from agent_jira.models import ChatRequest

if TYPE_CHECKING:
    from agent_jira.chat.service import ChatService

logger = logging.getLogger(__name__)


class GeneratorAgent:
    """
    Agente specializzato nella sintesi di risposte (Generation Only).
    Riceve contesto e query, produce una risposta in linguaggio naturale.
    """

    def __init__(self, service: ChatService) -> None:
        self.service = service
        self.responder = ResponseGenerator(
            service,
            build_prompt_fn=build_prompt,
            generate_response_fn=generate_response,
        )

    def synthesize(
        self,
        query: str,
        context: str,
        history: Optional[str] = None,
    ) -> str:
        """
        Genera una risposta completa basata su query e contesto forniti.
        """
        state = self._prepare_state(query, context, history)

        logger.info("GeneratorAgent: generating answer.")
        self.responder.generate_answer(state)
        self.responder.finalize_answer(state)

        return state.answer or ""

    def synthesize_stream(
        self,
        query: str,
        context: str,
        history: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Genera una risposta in streaming basata su query e contesto forniti.
        """
        state = self._prepare_state(query, context, history)

        logger.info("GeneratorAgent: generating answer stream.")
        for chunk in self.responder.generate_answer_stream(state):
            yield chunk

        self.responder.finalize_answer(state)

    def _prepare_state(
        self, query: str, context: str, history: Optional[str]
    ) -> AgentState:
        """Prepara lo stato per il ResponseGenerator."""
        req = ChatRequest(query=query)
        state = AgentState(request=req)
        state.user_query = query
        state.context = context
        if history:
            state.history_text = history
        return state
