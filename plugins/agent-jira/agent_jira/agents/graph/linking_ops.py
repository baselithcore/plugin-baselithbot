"""Linking operations for managing graph relationships."""

from __future__ import annotations

import logging

from agent_jira.graphdb import GraphDb
from agent_jira.graphdb.relationship_schema import build_relationship_properties

logger = logging.getLogger(__name__)


class LinkingOperations:
    """Handles relationship/edge operations in the knowledge graph."""

    def __init__(self, graph_client: GraphDb) -> None:
        self.client = graph_client

    def link_story_to_doc(self, story_id: str, doc_id: str) -> None:
        """Crea relazione: Story DERIVES_FROM Document (SOLO SE DOC ESISTE)."""
        # Fix Ghost Nodes: check if document exists before linking
        try:
            # Check if Document exists (fast check, only id)
            check_cypher = "MATCH (d:Document {id: $id}) RETURN d.id LIMIT 1"
            result = self.client.query(check_cypher, {"id": doc_id})
            # FalkorDB compact format: [header, [data_rows], stats] - always truthy
            data_rows = result[1] if result and len(result) > 1 else []
            if data_rows:
                self._safe_link(
                    story_id,
                    "DERIVES_FROM",
                    doc_id,
                    properties=build_relationship_properties(
                        "DERIVES_FROM",
                        provenance="application_linking",
                        extraction_method="story_to_document_link",
                    ),
                )
            else:
                logger.debug(
                    f"GraphAgent: skipped linking Story {story_id} to non-existent Document {doc_id}"
                )
        except Exception:
            logger.warning(
                f"GraphAgent: failed to check/link document {doc_id} to story {story_id}",
                exc_info=True,
            )

    def link_story_to_epic(self, story_id: str, epic_id: str) -> None:
        """Crea relazione: Story BELONGS_TO Epic."""
        self._safe_link(
            story_id,
            "BELONGS_TO",
            epic_id,
            properties=build_relationship_properties(
                "BELONGS_TO",
                provenance="application_linking",
                extraction_method="story_to_epic_link",
            ),
        )

    def link_test_to_story(self, test_id: str, story_id: str) -> None:
        """Crea relazione: TestCase VERIFIES Story."""
        self._safe_link(
            test_id,
            "VERIFIES",
            story_id,
            properties=build_relationship_properties(
                "VERIFIES",
                provenance="application_linking",
                extraction_method="test_to_story_link",
            ),
        )

    def link_story_to_requirement(self, story_id: str, req_id: str) -> None:
        """Crea relazione: Story SATISFIES Requirement."""
        self._safe_link(
            story_id,
            "SATISFIES",
            req_id,
            properties=build_relationship_properties(
                "SATISFIES",
                provenance="application_linking",
                extraction_method="story_to_requirement_link",
            ),
        )

    def _safe_link(
        self,
        source: str,
        rel: str,
        target: str,
        properties: dict | None = None,
    ) -> None:
        """Helper method to safely create edges with error handling."""
        if not self.client.is_enabled():
            return

        # Robustness check: prevent creating edges with missing nodes
        if not source or not target:
            logger.debug(
                f"GraphAgent: skipping link {rel} due to missing source/target"
            )
            return

        try:
            self.client.upsert_edge(source, rel, target, properties=properties)
            logger.debug(f"GraphAgent: linked {source} -[{rel}]-> {target}")
        except Exception:
            logger.warning(f"GraphAgent: failed link {source}->{target}", exc_info=True)
