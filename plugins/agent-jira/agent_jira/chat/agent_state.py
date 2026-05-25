from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, TypedDict

from agent_jira.chat.guardrails import GuardrailDecision
from agent_jira.integrations.jira import JiraIssueResult

if TYPE_CHECKING:
    from agent_jira.models import ChatRequest
    from agent_jira.project_manager import ProjectPlan


@dataclass
class AgentState:
    """Stato condiviso tra i passi dell'agente di chat."""

    request: "ChatRequest"
    user_query: str = ""
    rerank_query: str = ""
    normalized_query: str = ""
    conversation_id: Optional[str] = None
    history_turns: Sequence[Any] = ()
    history_text: str = ""
    query_vector: Optional[List[float]] = None
    hits: Sequence[Any] = ()
    ranked_hits: Sequence[Any] = ()
    context: str = ""
    doc_sources: List[Dict[str, Any]] = field(default_factory=list)
    source_metrics: Dict[str, Any] = field(default_factory=dict)
    cache_key: Optional[Tuple[str, str]] = None
    answer: Optional[Any] = None
    done: bool = False
    next_action: str = "validate_input"
    logs: List[str] = field(default_factory=list)
    guardrail_decision: Optional[GuardrailDecision] = None
    clarification_reason: Optional[str] = None
    project_plan: Optional["ProjectPlan"] = None
    jira_results: List[JiraIssueResult] = field(default_factory=list)
    jira_requires_manual_approval: bool = False
    rag_only: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def log(self, message: str) -> None:
        self.logs.append(message)


class _GraphState(TypedDict):
    agent_state: AgentState


__all__ = ["AgentState", "_GraphState"]
