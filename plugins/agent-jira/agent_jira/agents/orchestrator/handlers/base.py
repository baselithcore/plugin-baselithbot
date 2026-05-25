"""
Base Flow Handler Module

Provides the base class with common dependencies for all flow handlers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from agent_jira.agents.graph_agent import GraphAgent
    from agent_jira.agents.jira_agent import JiraAgent
    from agent_jira.agents.rag_agent import RAGAgent
    from agent_jira.chat.service import ChatService

logger = logging.getLogger(__name__)


class BaseFlowHandler:
    """Base class for flow handlers with common dependencies."""

    def __init__(
        self,
        service: ChatService,
        rag_agent: RAGAgent,
        jira_agent: JiraAgent,
        generator_agent: Optional[Any] = None,
        graph_agent: Optional[GraphAgent] = None,
    ) -> None:
        """
        Initialize base flow handler.

        Args:
            service: ChatService instance
            rag_agent: RAGAgent for document retrieval
            jira_agent: JiraAgent for Jira operations
            generator_agent: GeneratorAgent for synthesis
            graph_agent: Optional GraphAgent for graph operations
        """

        self.service = service
        self.rag_agent = rag_agent
        self.jira_agent = jira_agent
        self.generator_agent = generator_agent
        self.graph_agent = graph_agent
