from __future__ import annotations

from typing import TYPE_CHECKING

from agent_jira.chat.agent_state import AgentState
from agent_jira.chat.context import build_context_and_sources
from agent_jira.chat.guardrails import evaluate_guardrails
from agent_jira.chat.prompt import build_prompt
from agent_jira.chat.workflow_planner import BacklogPlanner
from agent_jira.chat.workflow_response import Clarifier, ResponseGenerator
from agent_jira.chat.workflow_retrieval import RetrievalPipeline
from agent_jira.chat.workflow_validation import InputValidator
from agent_jira.telemetry import telemetry

if TYPE_CHECKING:
    from agent_jira.chat.service import ChatService


def search(*args, **kwargs):
    from agent_jira.vectorstore import search as _search

    return _search(*args, **kwargs)


def rerank_hits(*args, **kwargs):
    from agent_jira.chat.reranking import rerank_hits as _rerank_hits

    return _rerank_hits(*args, **kwargs)


def generate_response(*args, **kwargs):
    from agent_jira.llm import generate_response as _generate_response

    return _generate_response(*args, **kwargs)


class AgentWorkflow:
    """Insieme di tool atomici che operano su AgentState."""

    def __init__(self, service: "ChatService") -> None:
        self.service = service
        self.validator = InputValidator(service)
        self.retrieval = RetrievalPipeline(
            service,
            search_fn=search,
            rerank_fn=rerank_hits,
            build_context_fn=build_context_and_sources,
        )
        self.planner = BacklogPlanner(service)
        self.clarifier = Clarifier(service)
        self.responder = ResponseGenerator(
            service,
            build_prompt_fn=build_prompt,
            generate_response_fn=generate_response,
        )

    def validate_input(self, state: AgentState) -> None:
        self.validator.validate_input(state)

    def classify_intent(self, state: AgentState) -> None:
        decision = evaluate_guardrails(state.user_query)
        state.guardrail_decision = decision
        log_message = f"guardrail:{decision.action}"
        if decision.matched:
            log_message = f"{log_message}:{decision.matched}"
        if decision.action == "block":
            state.answer = decision.response or "Richiesta non consentita."
            telemetry.increment("guardrail.block")
            telemetry.increment("answers.guardrail_block")
            state.log(log_message)
            state.done = True
            state.next_action = ""
            return
        if decision.action == "fallback":
            state.answer = (
                decision.response
                or "Posso rispondere solo a domande sui documenti indicizzati."
            )
            telemetry.increment("guardrail.fallback")
            telemetry.increment("answers.guardrail_fallback")
            state.log(log_message)
            state.done = True
            state.next_action = ""
            return
        telemetry.increment("guardrail.allow")
        state.log(log_message)
        state.next_action = "prepare_query"

    def prepare_query(self, state: AgentState) -> None:
        state.next_action = "load_history"

    def load_history(self, state: AgentState) -> None:
        self.retrieval.load_history(state)

    def retrieve_documents(self, state: AgentState) -> None:
        self.retrieval.retrieve_documents(state)

    def score_documents(self, state: AgentState) -> None:
        self.retrieval.score_documents(state)

    def apply_feedback(self, state: AgentState) -> None:
        self.retrieval.apply_feedback(state)

    def build_context(self, state: AgentState) -> None:
        self.retrieval.build_context(state)

    def check_cache(self, state: AgentState) -> None:
        self.retrieval.check_cache(state)

    def plan_backlog(self, state: AgentState) -> None:
        self.planner.plan_backlog(state)

    def sync_with_jira(self, state: AgentState) -> None:
        self.planner.sync_with_jira(state)

    def request_clarification(self, state: AgentState) -> None:
        self.clarifier.request_clarification(
            state, message_builder=self._compose_clarification_message
        )

    def _compose_clarification_message(self, state: AgentState) -> str:
        # Exposed for backward compatibility with tests/monkeypatching.
        return self.clarifier._compose_clarification_message(state)

    def generate_answer(self, state: AgentState) -> None:
        self.responder.generate_answer(state)

    def finalize_answer(self, state: AgentState) -> None:
        self.responder.finalize_answer(state)


__all__ = ["AgentWorkflow"]
