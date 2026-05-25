from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, Optional, Sequence

from langgraph.graph import END, START, StateGraph

from agent_jira.chat.agent_state import AgentState, _GraphState
from agent_jira.chat.agent_workflow import AgentWorkflow
from agent_jira.telemetry import telemetry
from agent_jira.config import FEEDBACK_BOOST_ENABLED

if TYPE_CHECKING:
    from agent_jira.chat.service import ChatService
    from agent_jira.models import ChatRequest


class ChatAgent:
    """Agente conversazionale che orchestra i tool del ChatService tramite LangGraph."""

    MAX_STEPS = 12

    def __init__(self, service: "ChatService") -> None:
        self.service = service
        self.workflow = AgentWorkflow(service)
        self._tools: Dict[str, Callable[[AgentState], None]] = {
            "validate_input": self.workflow.validate_input,
            "classify_intent": self.workflow.classify_intent,
            "prepare_query": self.workflow.prepare_query,
            "load_history": self.workflow.load_history,
            "retrieve_documents": self.workflow.retrieve_documents,
            "score_documents": self.workflow.score_documents,
            "apply_feedback": self.workflow.apply_feedback,
            "build_context": self.workflow.build_context,
            "plan_backlog": self.workflow.plan_backlog,
            "check_cache": self.workflow.check_cache,
            "sync_with_jira": self.workflow.sync_with_jira,
            "generate_answer": self.workflow.generate_answer,
            "finalize_answer": self.workflow.finalize_answer,
            "request_clarification": self.workflow.request_clarification,
        }
        self._graph_full = self._build_graph(include_generation=True)
        self._graph_until_generation = self._build_graph(include_generation=False)

    def run(
        self,
        request: "ChatRequest",
        *,
        stop_before: Optional[Sequence[str]] = None,
    ) -> AgentState:
        stop_set = set(stop_before or [])
        unsupported_stop = stop_set.difference({"generate_answer"})
        if unsupported_stop:
            return self._run_sequential(request, stop_before=stop_before)

        graph_input: _GraphState = {
            "agent_state": AgentState(request=request, metadata=request.metadata)
        }
        graph = (
            self._graph_until_generation
            if "generate_answer" in stop_set
            else self._graph_full
        )
        result = graph.invoke(graph_input)
        state = result["agent_state"]

        if not state.done and not stop_set:
            state.done = True
            if state.answer is None:
                state.answer = "❌ Errore interno dell'agente: flusso incompleto."
            telemetry.increment("answers.error")

        return state

    def _wrap_method(
        self, method: Callable[[AgentState], None]
    ) -> Callable[[_GraphState], _GraphState]:
        def _node(graph_state: _GraphState) -> _GraphState:
            method(graph_state["agent_state"])
            return {"agent_state": graph_state["agent_state"]}

        return _node

    def _build_graph(self, *, include_generation: bool):
        workflow: StateGraph[_GraphState] = StateGraph(_GraphState)
        workflow.add_node(
            "validate_input", self._wrap_method(self.workflow.validate_input)
        )
        workflow.add_node(
            "classify_intent", self._wrap_method(self.workflow.classify_intent)
        )
        workflow.add_node(
            "prepare_query", self._wrap_method(self.workflow.prepare_query)
        )
        workflow.add_node("load_history", self._wrap_method(self.workflow.load_history))
        workflow.add_node(
            "retrieve_documents", self._wrap_method(self.workflow.retrieve_documents)
        )
        workflow.add_node(
            "score_documents", self._wrap_method(self.workflow.score_documents)
        )
        workflow.add_node(
            "apply_feedback", self._wrap_method(self.workflow.apply_feedback)
        )
        workflow.add_node(
            "build_context", self._wrap_method(self.workflow.build_context)
        )
        workflow.add_node("check_cache", self._wrap_method(self.workflow.check_cache))
        workflow.add_node("plan_backlog", self._wrap_method(self.workflow.plan_backlog))
        workflow.add_node(
            "sync_with_jira", self._wrap_method(self.workflow.sync_with_jira)
        )
        workflow.add_node(
            "request_clarification",
            self._wrap_method(self.workflow.request_clarification),
        )
        if include_generation:
            workflow.add_node(
                "generate_answer", self._wrap_method(self.workflow.generate_answer)
            )
            workflow.add_node(
                "finalize_answer", self._wrap_method(self.workflow.finalize_answer)
            )

        workflow.add_edge(START, "validate_input")
        workflow.add_edge("prepare_query", "load_history")
        workflow.add_edge("load_history", "retrieve_documents")
        workflow.add_edge("apply_feedback", "build_context")
        workflow.add_edge("request_clarification", END)

        def _done_or_next(data: _GraphState) -> str:
            return "end" if data["agent_state"].done else "next"

        def _after_retrieval(data: _GraphState) -> str:
            return (
                "clarify"
                if data["agent_state"].clarification_reason
                else "score_documents"
            )

        def _after_scoring(data: _GraphState) -> str:
            state = data["agent_state"]
            if not state.ranked_hits:
                return "clarify"
            return "apply_feedback" if FEEDBACK_BOOST_ENABLED else "build_context"

        def _after_context(data: _GraphState) -> str:
            state = data["agent_state"]
            needs_clarification = not state.context.strip() and not state.history_text
            return "clarify" if needs_clarification else "check_cache"

        def _after_cache(data: _GraphState) -> str:
            return "done" if data["agent_state"].done else "continue"

        workflow.add_conditional_edges(
            "validate_input",
            _done_or_next,
            {"end": END, "next": "classify_intent"},
        )
        workflow.add_conditional_edges(
            "classify_intent",
            _done_or_next,
            {"end": END, "next": "prepare_query"},
        )
        workflow.add_conditional_edges(
            "retrieve_documents",
            _after_retrieval,
            {"clarify": "request_clarification", "score_documents": "score_documents"},
        )
        workflow.add_conditional_edges(
            "score_documents",
            _after_scoring,
            {
                "clarify": "request_clarification",
                "apply_feedback": "apply_feedback",
                "build_context": "build_context",
            },
        )
        workflow.add_conditional_edges(
            "build_context",
            _after_context,
            {"clarify": "request_clarification", "check_cache": "check_cache"},
        )
        workflow.add_conditional_edges(
            "check_cache",
            _after_cache,
            {"done": END, "continue": "plan_backlog"},
        )
        workflow.add_edge("plan_backlog", "sync_with_jira")
        next_after_sync = "generate_answer" if include_generation else END
        workflow.add_edge("sync_with_jira", next_after_sync)
        if include_generation:
            workflow.add_edge("generate_answer", "finalize_answer")
            workflow.add_edge("finalize_answer", END)
        return workflow.compile()

    def _run_sequential(
        self,
        request: "ChatRequest",
        *,
        stop_before: Optional[Sequence[str]] = None,
    ) -> AgentState:
        state = AgentState(request=request, metadata=request.metadata)
        steps = 0
        stop_set = set(stop_before or [])

        while not state.done and state.next_action and steps < self.MAX_STEPS:
            if stop_set and state.next_action in stop_set:
                break
            tool = self._tools.get(state.next_action)
            if tool is None:
                state.log(
                    f"Nessun tool definito per '{state.next_action}', interruzione."
                )
                break
            steps += 1
            tool(state)

        if not state.done:
            state.done = True
            if state.answer is None:
                state.answer = "❌ Errore interno dell'agente: flusso incompleto."
            telemetry.increment("answers.error")

        return state


__all__ = ["AgentState", "ChatAgent"]
