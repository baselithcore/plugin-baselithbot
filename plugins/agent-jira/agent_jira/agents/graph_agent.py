from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agent_jira.agents.graph.analysis_ops import AnalysisOperations
from agent_jira.agents.graph.batch_ops import BatchOperations
from agent_jira.agents.graph.document_ops import DocumentOperations
from agent_jira.agents.graph.entity_ops import EntityOperations
from agent_jira.agents.graph.linking_ops import LinkingOperations
from agent_jira.agents.graph.reasoning import GraphReasoning
from agent_jira.agents.graph.utils import current_timestamp
from agent_jira.graphdb import GraphDb

logger = logging.getLogger(__name__)


class GraphAgent:
    """
    Agente responsabile della gestione semantica del grafo conoscitivo.
    Slim orchestrator delegating to specialized operations modules.
    """

    def __init__(self, graph_client: GraphDb) -> None:
        self.client = graph_client

        # Composition for modularity
        self._doc_ops = DocumentOperations(graph_client)
        self._entity_ops = EntityOperations(graph_client)
        self._linking_ops = LinkingOperations(graph_client)
        self._analysis_ops = AnalysisOperations(graph_client)
        self._batch_ops = BatchOperations(graph_client)
        self._reasoning = GraphReasoning(graph_client)

    # --- Write Operations ---

    def upsert_document(
        self,
        doc_id: str,
        doc_type: str,
        path: str,
        category: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        return self._doc_ops.upsert_document(
            doc_id, doc_type, path, category, properties
        )

    def upsert_epic(
        self,
        epic_id: str,
        summary: str,
        status: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        return self._entity_ops.upsert_epic(epic_id, summary, status, properties)

    def upsert_story(
        self,
        story_id: str,
        summary: str,
        status: str,
        points: Optional[float] = None,
        assignee: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        return self._entity_ops.upsert_story(
            story_id, summary, status, points, assignee, properties
        )

    def upsert_test_case(
        self,
        test_id: str,
        summary: str,
        status: str,
        test_type: str = "Test Case",
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        props = properties.copy() if properties else {}
        props["status"] = status
        return self._entity_ops.upsert_test_case(
            test_id=test_id, test_type=test_type, summary=summary, properties=props
        )

    def link_entities(
        self,
        source_id: str,
        relationship: str,
        target_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.client.is_enabled():
            return
        self.client.upsert_edge(
            source_id,
            relationship,
            target_id,
            properties=properties,
        )

    # --- Batch Operations ---

    def upsert_stories_batch(self, stories_data: list[Dict[str, Any]]) -> None:
        return self._batch_ops.upsert_stories_batch(stories_data)

    def upsert_test_cases_batch(self, test_cases_data: list[Dict[str, Any]]) -> None:
        return self._batch_ops.upsert_test_cases_batch(test_cases_data)

    def link_stories_docs_batch(self, links: list[Dict[str, str]]) -> None:
        return self._batch_ops.link_stories_docs_batch(links)

    def link_tests_stories_batch(self, links: list[Dict[str, str]]) -> None:
        return self._batch_ops.link_tests_stories_batch(links)

    def link_stories_issues_batch(self, links: list[Dict[str, str]]) -> None:
        return self._batch_ops.link_stories_issues_batch(links)

    def create_story_relationships_batch(
        self, relationships: list[Dict[str, Any]]
    ) -> None:
        return self._batch_ops.create_story_relationships_batch(relationships)

    # --- Analysis & Reasoning ---

    def reason(self, intent: str, entities: List[str]) -> Dict[str, Any]:
        return self._reasoning.reason(intent, entities)

    def get_impact_analysis(self, doc_id: str) -> Dict[str, Any]:
        return self._analysis_ops.get_impact_analysis(doc_id)

    def get_traceability(self, story_id: str) -> Dict[str, Any]:
        return self._analysis_ops.get_traceability(story_id)

    def get_completeness_report(self, epic_id: Optional[str] = None) -> Dict[str, Any]:
        return self._analysis_ops.completeness_report(epic_id)

    def impact_analysis(self, doc_id: str) -> Dict[str, Any]:
        """Alias for backward compatibility."""
        return self.get_impact_analysis(doc_id)

    def completeness_report(self, epic_id: str) -> Dict[str, Any]:
        """Specific epic completeness report."""
        return self._analysis_ops.completeness_report(epic_id)

    # --- Metadata & Lifecycle ---

    def transition_document_to_kb(
        self, doc_id: str, new_path: Optional[str] = None
    ) -> None:
        return self._doc_ops.transition_document_to_kb(doc_id, new_path)

    def upsert_requirement(
        self,
        req_id: str,
        text: str,
        source_doc_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        return self._entity_ops.upsert_requirement(
            req_id, text, source_doc_id, properties
        )

    def register_rag_usage(
        self, session_id: str, doc_sources: List[Dict[str, Any]]
    ) -> None:
        return self._doc_ops.register_rag_usage(session_id, doc_sources)

    def upsert_stakeholder(
        self,
        name: str,
        role: Optional[str] = None,
        email: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source_document_id: Optional[str] = None,
    ) -> str:
        return self._entity_ops.upsert_stakeholder(
            name,
            role=role,
            email=email,
            properties=properties,
            source_document_id=source_document_id,
        )

    def upsert_milestone(
        self,
        name: str,
        date: Optional[str] = None,
        description: Optional[str] = None,
        milestone_type: str = "Generic",
        status: str = "Planned",
        properties: Optional[Dict[str, Any]] = None,
        source_document_id: Optional[str] = None,
    ) -> str:
        return self._entity_ops.upsert_milestone(
            name,
            date=date,
            description=description,
            milestone_type=milestone_type,
            status=status,
            properties=properties,
            source_document_id=source_document_id,
        )

    def upsert_technology(
        self,
        name: str,
        category: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source_document_id: Optional[str] = None,
    ) -> str:
        return self._entity_ops.upsert_technology(
            name,
            category=category,
            properties=properties,
            source_document_id=source_document_id,
        )

    def upsert_risk(
        self,
        description: str,
        severity: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source_document_id: Optional[str] = None,
    ) -> str:
        return self._entity_ops.upsert_risk(
            description,
            severity=severity,
            properties=properties,
            source_document_id=source_document_id,
        )

    def upsert_topic(
        self,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
        source_document_id: Optional[str] = None,
    ) -> str:
        return self._entity_ops.upsert_topic(
            name,
            properties=properties,
            source_document_id=source_document_id,
        )

    def link_story_to_doc(self, story_id: str, doc_id: str) -> None:
        return self._linking_ops.link_story_to_doc(story_id, doc_id)

    def find_similar_stories(
        self, summary: str, threshold: float = 0.85, limit: int = 5
    ) -> list[Dict[str, Any]]:
        return self._analysis_ops.find_similar_stories(
            summary, threshold=threshold, limit=limit
        )

    def find_experts(self, topic: str, limit: int = 5) -> Dict[str, Any]:
        return self._analysis_ops.find_experts(topic, limit)

    def _safe_link(self, source: str, rel: str, target: str) -> None:
        return self._linking_ops._safe_link(source, rel, target)

    def _current_timestamp(self) -> str:
        return current_timestamp()
