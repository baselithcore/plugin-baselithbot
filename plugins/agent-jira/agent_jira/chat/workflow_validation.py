from __future__ import annotations

from typing import TYPE_CHECKING

from agent_jira.chat.agent_state import AgentState

if TYPE_CHECKING:
    from agent_jira.chat.service import ChatService


def list_indexed_documents():
    from agent_jira.vectorstore import list_indexed_documents as _list_indexed_documents

    return _list_indexed_documents()


class InputValidator:
    """Handle input preprocessing and early exit checks."""

    def __init__(self, service: "ChatService") -> None:
        self.service = service

    def validate_input(self, state: AgentState) -> None:
        state.rag_only = bool(getattr(state.request, "rag_only", False))
        state.user_query = (state.request.query or "").strip()
        if not state.user_query:
            state.answer = "⚠️ La domanda è vuota."
            state.done = True
            state.next_action = ""
            return

        state.normalized_query = " ".join(state.user_query.split())

        # Intent: lista documenti disponibili in KB
        if self._is_list_documents_query(state.normalized_query):
            docs = list_indexed_documents()
            if not docs:
                state.answer = (
                    "Non risultano documenti indicizzati nella knowledge base."
                )
            else:
                lines = []
                for entry in docs:
                    doc_id = entry.get("document_id") or ""
                    meta = entry.get("metadata") or {}
                    title = meta.get("title") or meta.get("filename") or doc_id
                    lines.append(f"- {title} ({doc_id})")
                state.answer = "Documenti disponibili in KB:\n" + "\n".join(lines)
            state.done = True
            state.next_action = ""
            return

        state.next_action = "classify_intent"

    @staticmethod
    def _is_list_documents_query(query: str) -> bool:
        q = query.lower()
        triggers = [
            "che documenti hai",
            "quali documenti hai",
            "lista documenti",
            "elenca documenti",
            "documenti disponibili",
            "kb disponibili",
        ]
        return any(trigger in q for trigger in triggers)


__all__ = ["InputValidator"]
