from __future__ import annotations

import logging
from typing import Any, Dict, List

from agent_jira.graphdb import GraphDb

logger = logging.getLogger(__name__)


class GraphReasoning:
    """Handles batched semantic reasoning queries on the graph."""

    def __init__(self, graph_client: GraphDb) -> None:
        self.client = graph_client

    def reason(self, intent: str, entities: List[str]) -> Dict[str, Any]:
        """
        Executes reasoning on the graph based on intent.
        Returns semantic context for LLM prompts.
        """
        if not self.client.is_enabled():
            return {"status": "disabled", "reasoning_context": ""}

        if not entities:
            return {"status": "success", "reasoning_context": "No entities provided."}

        context_parts = []
        intent_lower = intent.lower()

        # 1. Impact Analysis Intent
        if (
            "impact" in intent_lower
            or "break" in intent_lower
            or "chang" in intent_lower
        ):
            self._add_impact_context(entities, context_parts)

        # 2. Traceability Intent
        elif (
            "trace" in intent_lower
            or "origin" in intent_lower
            or "source" in intent_lower
        ):
            self._add_traceability_context(entities, context_parts)

        # 3. Default: General Neighborhood Search
        if not context_parts:
            self._add_neighborhood_context(entities, context_parts)

        return {
            "status": "success",
            "reasoning_context": "\n\n".join(context_parts)
            if context_parts
            else "No specific graph context found.",
        }

    def _add_impact_context(self, entities: List[str], context_parts: List[str]):
        cypher = """
        UNWIND $doc_ids as doc_id
        MATCH (doc:Document {id: doc_id})<-[:DERIVES_FROM]-(story:Story)
        OPTIONAL MATCH (story)<-[:VERIFIES]-(test:TestCase)
        RETURN doc_id, story.summary, story.status, collect(test.summary) as tests
        LIMIT 50
        """
        try:
            results = self.client.query(cypher, {"doc_ids": entities})
            if results:
                grouped = {}
                for row in results:
                    d_id, s_sum, s_stat, tests_list = row[0], row[1], row[2], row[3]
                    if d_id not in grouped:
                        grouped[d_id] = []
                    grouped[d_id].append(
                        f"- Story: {s_sum} ({s_stat})\n  Tests: {', '.join(tests_list) if tests_list else 'None'}"
                    )

                for d_id, items in grouped.items():
                    context_parts.append(
                        f"Impact Analysis for '{d_id}':\n" + "\n".join(items)
                    )
        except Exception:
            logger.error(
                "GraphReasoning: batched impact analysis failed", exc_info=True
            )

    def _add_traceability_context(self, entities: List[str], context_parts: List[str]):
        cypher = """
        UNWIND $story_ids as story_id
        MATCH (story:Story {id: story_id})
        OPTIONAL MATCH (story)-[:PARENT_OF]->(epic:Epic)
        OPTIONAL MATCH (story)-[:DERIVES_FROM]->(doc:Document)
        RETURN story_id, epic.summary, doc.path
        LIMIT 50
        """
        try:
            results = self.client.query(cypher, {"story_ids": entities})
            if results:
                for row in results:
                    s_id, epic_sum, doc_path = row[0], row[1], row[2]
                    block = f"Traceability for '{s_id}':\n"
                    if epic_sum:
                        block += f"- Parent Epic: {epic_sum}\n"
                    if doc_path:
                        block += f"- Source Doc: {doc_path}\n"
                    context_parts.append(block)
        except Exception:
            logger.error("GraphReasoning: batched traceability failed", exc_info=True)

    def _add_neighborhood_context(self, entities: List[str], context_parts: List[str]):
        cypher = """
        UNWIND $entities as entity
        MATCH (n)-[r]-(m)
        WHERE n.id CONTAINS entity OR n.name CONTAINS entity
        RETURN n.id, n.summary, type(r), m.summary
        LIMIT 20
        """
        try:
            results = self.client.query(cypher, {"entities": entities})
            if results:
                block = "Knowledge Context:\n"
                seen = set()
                for row in results:
                    n_id, n_sum, rel, m_sum = row[0], row[1], row[2], row[3]
                    line = f"- {n_sum or n_id} -[{rel}]-> {m_sum}"
                    if line not in seen:
                        block += line + "\n"
                        seen.add(line)
                context_parts.append(block)
        except Exception:
            logger.warning(
                f"GraphReasoning: neighborhood fallback failed for: {entities}"
            )
