from __future__ import annotations

from typing import TYPE_CHECKING, List

from agent_jira.chat.agent_state import AgentState
from agent_jira.chat.prompt import build_prompt
from agent_jira.llm import generate_response
from agent_jira.telemetry import telemetry
from agent_jira.config import OLLAMA_MODEL

if TYPE_CHECKING:
    from agent_jira.chat.service import ChatService


class Clarifier:
    """Handle clarification responses when the RAG pipeline cannot answer."""

    def __init__(self, service: "ChatService") -> None:
        self.service = service

    def request_clarification(
        self,
        state: AgentState,
        *,
        message_builder=None,
    ) -> None:
        telemetry.increment("clarification.triggered")
        if state.clarification_reason:
            telemetry.increment(f"clarification.{state.clarification_reason}")
            state.log(f"clarification:reason={state.clarification_reason}")
        telemetry.increment("answers.clarification")
        builder = message_builder or self._compose_clarification_message
        message = builder(state)
        state.answer = message
        state.done = True
        state.next_action = ""

    def _compose_clarification_message(self, state: AgentState) -> str:
        query_snippet = (state.user_query or state.request.query or "").strip()
        base_message = (
            "Non ho trovato abbastanza informazioni nei documenti indicizzati"
        )
        if query_snippet:
            base_message = f'{base_message} per la domanda "{query_snippet}".'
        else:
            base_message = f"{base_message}."

        tips: List[str] = [
            "aggiungi dettagli su reparto, progetto o periodo a cui ti riferisci",
            "specifica il nome del file, del documento o una parola chiave distintiva",
            "descrivi l'obiettivo o il problema che stai cercando di risolvere",
        ]

        if state.history_text:
            tips.append(
                "richiama un passaggio precedente della conversazione che ritieni rilevante"
            )

        suggestions = "\n".join(f"- {tip}" for tip in tips)
        return f"{base_message}\n\nPuoi aiutarmi così:\n{suggestions}"


class ResponseGenerator:
    """LLM prompt orchestration and final answer formatting."""

    def __init__(
        self,
        service: "ChatService",
        *,
        build_prompt_fn=build_prompt,
        generate_response_fn=generate_response,
        generate_response_stream_fn=None,
    ) -> None:
        self.service = service
        self.build_prompt_fn = build_prompt_fn
        self.generate_response_fn = generate_response_fn
        # Lazy import or pass from init to avoid circular deps if needed,
        # but defaulting to app.llm.generate_response_stream is fine if passed.
        from agent_jira.llm import generate_response_stream

        self.generate_response_stream_fn = (
            generate_response_stream_fn or generate_response_stream
        )

    def generate_answer(self, state: AgentState) -> None:
        prompt = self.build_prompt_fn(
            state.user_query,
            state.context,
            state.history_text,
            project_plan=state.project_plan,
            jira_results=state.jira_results,
        )
        state.answer = self.generate_response_fn(prompt, model=OLLAMA_MODEL)
        state.next_action = "finalize_answer"

    def generate_answer_stream(self, state: AgentState):
        """Generates answer using streaming, yielding chunks."""
        prompt = self.build_prompt_fn(
            state.user_query,
            state.context,
            state.history_text,
            project_plan=state.project_plan,
            jira_results=state.jira_results,
        )

        full_answer = []
        for chunk in self.generate_response_stream_fn(prompt, model=OLLAMA_MODEL):
            full_answer.append(chunk)
            yield chunk

        state.answer = "".join(full_answer)
        state.next_action = "finalize_answer"

    def finalize_answer(self, state: AgentState) -> None:
        answer = state.answer

        if isinstance(answer, str):
            # Legacy: answer = self.service._finalize_answer_state(state, answer)
            # RAGAgent/Orchestrator now handle final composition.
            pass
        telemetry.increment("answers.generated")

        state.done = True
        state.next_action = ""


__all__ = ["Clarifier", "ResponseGenerator"]
