"""Batch operations for optimized graph database updates."""

from __future__ import annotations

import logging
from typing import Any, Dict

from agent_jira.graphdb import GraphDb
from agent_jira.graphdb.relationship_schema import (
    build_relationship_properties,
    normalize_relationship_type,
)

logger = logging.getLogger(__name__)


class BatchOperations:
    """Handles batch operations for performance optimization."""

    def __init__(self, graph_client: GraphDb) -> None:
        self.client = graph_client

    def upsert_stories_batch(self, stories_data: list[Dict[str, Any]]) -> None:
        """
        Upsert massivo di User Stores.
        stories_data: lista di dict con keys: id, summary, status, points, properties
        """
        if not self.client.is_enabled() or not stories_data:
            return

        try:
            # Prepare data for UNWIND
            # We want a list of dicts.
            # Cypher: UNWIND $batch as item MERGE ...
            cypher = (
                "UNWIND $batch AS item "
                "MERGE (s:Story {id: item.id}) "
                "SET s.summary = item.summary, "
                "    s.status = item.status, "
                "    s.points = item.points "
                "SET s += item.properties"
            )
            # Ensure properties is a dict
            sanitized_batch = []
            for s in stories_data:
                item = {
                    "id": s["id"],
                    "summary": s["summary"],
                    "status": s["status"],
                    "points": s.get("points"),
                    "properties": s.get("properties", {}),
                }
                sanitized_batch.append(item)

            self.client.query(cypher, {"batch": sanitized_batch})
            logger.info(f"GraphAgent: batch upsert {len(stories_data)} stories")
        except Exception:
            logger.error("GraphAgent: batch story upsert failed", exc_info=True)

    def upsert_test_cases_batch(self, test_cases_data: list[Dict[str, Any]]) -> None:
        """
        Upsert massivo di Test Cases.
        test_cases_data: lista di dict con keys: id, type, summary, properties
        """
        if not self.client.is_enabled() or not test_cases_data:
            return

        try:
            cypher = (
                "UNWIND $batch AS item "
                "MERGE (t:TestCase {id: item.id}) "
                "SET t.type = item.type, "
                "    t.summary = item.summary "
                "SET t += item.properties"
            )
            sanitized_batch = []
            for t in test_cases_data:
                item = {
                    "id": t["id"],
                    "type": t.get("type", "Test"),
                    "summary": t["summary"],
                    "properties": t.get("properties", {}),
                }
                sanitized_batch.append(item)

            self.client.query(cypher, {"batch": sanitized_batch})
            logger.info(f"GraphAgent: batch upsert {len(test_cases_data)} test cases")
        except Exception:
            logger.error("GraphAgent: batch test case upsert failed", exc_info=True)

    def link_stories_docs_batch(self, links: list[Dict[str, str]]) -> None:
        """
        Link massivo Story -> Doc.
        links: lista di dict {"story_id": ..., "doc_id": ...}
        """
        if not self.client.is_enabled() or not links:
            return

        try:
            # We only link if Doc exists? Or we blindly link?
            # Original code checked for doc existence.
            # In batch, checking one by one is slow.
            # We can do: MATCH (d:Document {id: item.doc_id}) MERGE ...
            # If doc doesn't exist, MATCH fails (if using classic MATCH) and no link created.
            cypher = (
                "UNWIND $batch AS item "
                "MATCH (d:Document {id: item.doc_id}) "  # Match any node with this ID (KnowledgeBase or Analysis)
                "MERGE (s:Story {id: item.story_id}) "
                "MERGE (s)-[r:DERIVES_FROM]->(d) "
                "SET r += item.properties"
            )
            sanitized_links = []
            for link in links:
                sanitized_links.append(
                    {
                        **link,
                        "properties": build_relationship_properties(
                            "DERIVES_FROM",
                            provenance="batch_linking",
                            extraction_method="batch_story_document_link",
                        ),
                    }
                )
            self.client.query(cypher, {"batch": sanitized_links})
            logger.info(f"GraphAgent: batch link {len(links)} stories to docs")
        except Exception:
            logger.error("GraphAgent: batch link stories->docs failed", exc_info=True)

    def link_tests_stories_batch(self, links: list[Dict[str, str]]) -> None:
        """
        Link massivo Test -> Story.
        links: lista di dict {"test_id": ..., "story_id": ...}
        """
        if not self.client.is_enabled() or not links:
            return

        try:
            cypher = (
                "UNWIND $batch AS item "
                "MATCH (s:Story {id: item.story_id}) "
                "MERGE (t:TestCase {id: item.test_id}) "
                "MERGE (t)-[r:VERIFIES]->(s) "
                "SET r += item.properties"
            )
            sanitized_links = []
            for link in links:
                sanitized_links.append(
                    {
                        **link,
                        "properties": build_relationship_properties(
                            "VERIFIES",
                            provenance="batch_linking",
                            extraction_method="batch_test_story_link",
                        ),
                    }
                )
            self.client.query(cypher, {"batch": sanitized_links})
            logger.info(f"GraphAgent: batch link {len(links)} tests to stories")
        except Exception:
            logger.error("GraphAgent: batch link tests->stories failed", exc_info=True)

    def link_stories_issues_batch(self, links: list[Dict[str, str]]) -> None:
        """
        Link massivo Story -> JiraIssue.
        links: lista di dict {"story_id": ..., "issue_key": ...}
        """
        if not self.client.is_enabled() or not links:
            return

        try:
            cypher = (
                "UNWIND $batch AS item "
                "MERGE (j:JiraIssue {id: item.issue_key}) "
                "MERGE (s:Story {id: item.story_id}) "
                "MERGE (s)-[r:LINKED_ISSUE]->(j) "
                "SET r += item.properties"
            )
            sanitized_links = []
            for link in links:
                sanitized_links.append(
                    {
                        **link,
                        "properties": build_relationship_properties(
                            "LINKED_ISSUE",
                            provenance="batch_linking",
                            extraction_method="batch_story_issue_link",
                        ),
                    }
                )
            self.client.query(cypher, {"batch": sanitized_links})
            logger.info(f"GraphAgent: batch link {len(links)} stories to issues")
        except Exception:
            logger.error("GraphAgent: batch link stories->issues failed", exc_info=True)

    def create_story_relationships_batch(
        self, relationships: list[Dict[str, Any]]
    ) -> None:
        """
        Create intelligent relationships between stories (BLOCKS, RELATES_TO, COMPLEMENTS).
        relationships: lista di dict {
            "from_story_id": ...,
            "to_story_id": ...,
            "relationship_type": "BLOCKS" | "RELATES_TO" | "COMPLEMENTS",
            "properties": {...}  # Optional properties like score, reason, etc.
        }
        """
        if not self.client.is_enabled() or not relationships:
            return

        try:
            # Group by relationship type for better logging
            by_type = {}
            for rel in relationships:
                rel_type = normalize_relationship_type(
                    rel.get("relationship_type", "RELATES_TO")
                )
                raw_props = rel.get("properties") or {}
                props = build_relationship_properties(
                    rel_type,
                    properties=raw_props,
                    provenance="story_relationship_detection",
                    extraction_method="jira_agent_relationship_detector",
                    confidence=raw_props.get("similarity_score"),
                    evidence=raw_props.get("reason")
                    or raw_props.get("shared_concepts"),
                )
                normalized_rel = {
                    **rel,
                    "relationship_type": rel_type,
                    "properties": props,
                }
                if rel_type not in by_type:
                    by_type[rel_type] = []
                by_type[rel_type].append(normalized_rel)

            # Create relationships for each type
            for rel_type, rels in by_type.items():
                cypher = (
                    "UNWIND $batch AS item "
                    "MATCH (from:Story {id: item.from_story_id}) "
                    "MATCH (to:Story {id: item.to_story_id}) "
                    f"MERGE (from)-[r:{rel_type}]->(to) "
                    "SET r += item.properties"
                )
                self.client.query(cypher, {"batch": rels})
                logger.info(
                    f"GraphAgent: batch created {len(rels)} {rel_type} relationships"
                )
        except Exception:
            logger.error(
                "GraphAgent: batch create story relationships failed", exc_info=True
            )
