from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .jira_agent import JiraAgent
    from .orchestrator_agent import OrchestratorAgent
    from .rag_agent import RAGAgent


def __getattr__(name):
    if name == "RAGAgent":
        from .rag_agent import RAGAgent

        return RAGAgent
    if name == "JiraAgent":
        from .jira_agent import JiraAgent

        return JiraAgent
    if name == "OrchestratorAgent":
        from .orchestrator_agent import OrchestratorAgent

        return OrchestratorAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["RAGAgent", "JiraAgent", "OrchestratorAgent"]
