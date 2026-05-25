"""Analysis operations for graph database queries and reporting."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from agent_jira.graphdb import GraphDb

logger = logging.getLogger(__name__)


class AnalysisOperations:
    """Handles graph analysis and reporting operations."""

    def __init__(self, graph_client: GraphDb) -> None:
        self.client = graph_client

    def get_impact_analysis(self, doc_id: str) -> Dict[str, Any]:
        """
        Calculates impact of document changes.
        Traverses Document <- DERIVES_FROM - Story <- VERIFIES - TestCase.
        """
        if not self.client.is_enabled():
            return {"status": "disabled", "impact": []}

        cypher = """
        MATCH (doc:Document {id: $doc_id})<-[:DERIVES_FROM]-(story:Story)
        OPTIONAL MATCH (story)<-[:VERIFIES]-(test:TestCase)
        RETURN
            story.id as story_id,
            story.summary as story_summary,
            story.status as story_status,
            collect({id: test.id, summary: test.summary, status: test.status}) as tests
        """
        try:
            results = self.client.query(cypher, {"doc_id": doc_id})
            formatted_results = []
            if results:
                for row in results:
                    s_id, s_sum, s_stat, tests = row[0], row[1], row[2], row[3]
                    formatted_results.append(
                        {
                            "story": {"id": s_id, "summary": s_sum, "status": s_stat},
                            "impacted_tests": [t for t in tests if t.get("id")],
                        }
                    )

            return {
                "status": "success",
                "focus_entity": doc_id,
                "impact_tree": formatted_results,
            }
        except Exception:
            logger.error(
                f"AnalysisOps: impact analysis failed for {doc_id}", exc_info=True
            )
            return {"status": "error", "message": "Query execution failed"}

    def get_traceability(self, story_id: str) -> Dict[str, Any]:
        """
        Tracing Story -> Parent Epic AND Story -> Source Document.
        """
        if not self.client.is_enabled():
            return {"status": "disabled"}

        cypher = """
        MATCH (story:Story {id: $story_id})
        OPTIONAL MATCH (story)-[:PARENT_OF]->(epic:Epic)
        OPTIONAL MATCH (story)-[:DERIVES_FROM]->(doc:Document)
        RETURN
            epic.id as epic_id, epic.summary as epic_summary,
            doc.id as doc_id, doc.path as doc_path
        """
        try:
            results = self.client.query(cypher, {"story_id": story_id})
            trace = {"story_id": story_id, "parent_epic": None, "source_document": None}

            if results and len(results) > 0:
                row = results[0]
                if row[0]:
                    trace["parent_epic"] = {"id": row[0], "summary": row[1]}
                if row[2]:
                    trace["source_document"] = {"id": row[2], "path": row[3]}

            return {"status": "success", "traceability": trace}
        except Exception:
            logger.error(
                f"AnalysisOps: traceability failed for {story_id}", exc_info=True
            )
            return {"status": "error"}

    def completeness_report(self, epic_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Finds Stories without Tests and Epics without Stories.
        If epic_id is provided, calculates coverage for that specific epic.
        """
        if not self.client.is_enabled():
            return {"status": "disabled"}

        try:
            if epic_id:
                # Specific Epic Coverage (Backwards compatibility for tests)
                cypher = """
                MATCH (e:Epic {id: $epic_id})-[:PARENT_OF]->(s:Story)
                OPTIONAL MATCH (s)<-[:VERIFIES]-(t:TestCase)
                RETURN s.id, count(t) as test_count
                """
                res = self.client.query(cypher, {"epic_id": epic_id})
                if not res:
                    return {
                        "status": "success",
                        "total_stories": 0,
                        "covered_stories": 0,
                        "coverage_pct": 0.0,
                    }

                total = len(res)
                covered = sum(1 for row in res if row[1] > 0)
                pct = (covered / total * 100.0) if total > 0 else 0.0

                return {
                    "status": "success",
                    "total_stories": total,
                    "covered_stories": covered,
                    "coverage_pct": pct,
                }

            report = {"stories_missing_tests": [], "epics_empty": []}

            # 1. Stories without Tests
            c1 = """
            MATCH (story:Story)
            WHERE NOT (story)<-[:VERIFIES]-(:TestCase)
            RETURN story.id, story.summary
            LIMIT 50
            """
            res1 = self.client.query(c1)
            if res1:
                report["stories_missing_tests"] = [
                    {"id": r[0], "summary": r[1]} for r in res1
                ]

            # 2. Epics without Stories
            c2 = """
            MATCH (epic:Epic)
            WHERE NOT (epic)-[:PARENT_OF]->(:Story)
            RETURN epic.id, epic.summary
            LIMIT 50
            """
            res2 = self.client.query(c2)
            if res2:
                report["epics_empty"] = [{"id": r[0], "summary": r[1]} for r in res2]

            return {"status": "success", "report": report}
        except Exception:
            logger.error(
                f"AnalysisOps: completeness check failed for {epic_id}", exc_info=True
            )
            return {"status": "error"}

    def get_risk_heatmap(self, root_doc_id: Any = None) -> Dict[str, Any]:
        """
        Genera una mappa di calore dei rischi propagando il `risk_level` dai documenti
        alle storie e alle epiche.
        """
        if not self.client.is_enabled():
            return {"status": "disabled"}

        try:
            # Filtro opzionale su root_doc_id
            doc_filter = " {id: $root_doc_id}" if root_doc_id else ""

            # Query: Document (con risk) -> Story -> Epic
            # Case insensitive check for risk_level usually requires constraints or toLower
            # Assuming 'High', 'Medium', 'Low' are stored cleanly.
            cypher = (
                f"MATCH (d:Document{doc_filter})<-[:DERIVES_FROM]-(s:Story) "
                "WHERE d.risk_level IS NOT NULL "
                "OPTIONAL MATCH (s)-[:BELONGS_TO]->(e:Epic) "
                "RETURN d.id, d.name, d.risk_level, s.id, s.status, s.summary, e.id, e.name"
            )

            params = {}
            if root_doc_id:
                params["root_doc_id"] = root_doc_id

            results = self.client.query(cypher, params)

            docs_map = {}
            stories_list = []
            epics_map = {}  # id -> {name, risky_stories_count, total_stories_known_here}

            if results and isinstance(results, list):
                for row in results:
                    if not isinstance(row, list) or len(row) < 8:
                        continue

                    d_id, d_name, d_risk, s_id, s_status, s_sum, e_id, e_name = row

                    # Normalizza risk level
                    risk_norm = str(d_risk).lower()
                    if risk_norm not in ("high", "medium"):
                        continue  # Skip low risk for heatmap focus? Or keep all?
                        # Roadmap says "If High Risk...". Let's focus on High/Medium.

                    # Docs
                    if d_id not in docs_map:
                        docs_map[d_id] = {
                            "id": d_id,
                            "name": d_name,
                            "risk_level": d_risk,
                        }

                    # Stories
                    story_risk_entry = {
                        "story_id": s_id,
                        "summary": s_sum,
                        "status": s_status,
                        "risk_level": d_risk,  # inherited
                        "source_doc": d_name,
                        "epic": e_name or "No Epic",
                    }
                    stories_list.append(story_risk_entry)

                    # Epics aggregation
                    if e_id:
                        if e_id not in epics_map:
                            epics_map[e_id] = {"name": e_name, "risky_stories": 0}
                        epics_map[e_id]["risky_stories"] += 1

            return {
                "status": "success",
                "high_risk_documents": list(docs_map.values()),
                "impacted_stories_count": len(stories_list),
                "impacted_stories": stories_list,
                "epics_at_risk": [{"id": k, **v} for k, v in epics_map.items()],
            }

        except Exception as e:
            logger.error(f"GraphAgent: risk heatmap failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def find_similar_stories(
        self, summary: str, threshold: float = 0.85, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Ricerca semantica per trovare storie simili (duplicate detection).
        Utilizza Qdrant per trovare i vettori più vicini.
        """

        matches = []
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            from agent_jira.nlp_models import get_embedder
            from agent_jira.config import COLLECTION, QDRANT

            if not summary:
                return []

            embedder = get_embedder()
            vector = embedder.encode(summary, convert_to_numpy=True)
            if hasattr(vector, "tolist"):
                vector = vector.tolist()

            # Filter for only user stories
            story_filter = Filter(
                must=[FieldCondition(key="type", match=MatchValue(value="story"))]
            )

            results = QDRANT.query_points(
                collection_name=COLLECTION,
                query=vector,
                query_filter=story_filter,
                limit=limit,
                with_payload=True,
                score_threshold=threshold,
            )

            for point in results.points:
                payload = point.payload or {}
                matches.append(
                    {
                        "id": payload.get("story_id"),
                        "summary": payload.get("text"),
                        "score": point.score,
                        "status": payload.get("status"),
                    }
                )

        except Exception as e:
            logger.warning(
                f"GraphAgent: find_similar_stories failed: {e}", exc_info=True
            )

        return matches

    def gap_analysis(self, doc_id: str) -> Dict[str, Any]:
        """
        Analisi dei gap di test per un documento.
        Identifica:
        1. Requisiti non collegati a nessuna User Story (Uncovered Requirements)
        2. User Story derivate dal documento ma senza Test Case (Untested Stories)
        """
        if not self.client.is_enabled():
            return {"status": "disabled"}

        try:
            # 1. Uncovered Requirements
            # Cerchiamo nodi Requirement collegati al Documento che NON hanno una relazione SATISFIES in ingresso da una Story
            # (Story)-[:SATISFIES]->(Requirement)
            # (Requirement)-[:DERIVES_FROM]->(Document)

            # Nota: DERIVES_FROM tra Req e Doc è stato aggiunto in upsert_requirement

            cypher_reqs = (
                "MATCH (r:Requirement)-[:DERIVES_FROM]->(d:Document {id: $doc_id}) "
                "OPTIONAL MATCH (s:Story)-[:SATISFIES]->(r) "
                "WITH r, count(s) as stories_count "
                "WHERE stories_count = 0 "
                "RETURN r.id, r.text"
            )

            # 2. Untested Stories
            # Cerchiamo Storie derivate dal Documento che NON hanno Test Case
            # (Story)-[:DERIVES_FROM]->(Document)
            # (TestCase)-[:VERIFIES]->(Story)
            cypher_stories = (
                "MATCH (s:Story)-[:DERIVES_FROM]->(d:Document {id: $doc_id}) "
                "OPTIONAL MATCH (t:TestCase)-[:VERIFIES]->(s) "
                "WITH s, count(t) as test_count "
                "WHERE test_count = 0 "
                "RETURN s.id, s.summary, s.status"
            )

            uncovered_reqs = []
            results_req = self.client.query(cypher_reqs, {"doc_id": doc_id})
            if results_req and isinstance(results_req, list):
                for row in results_req:
                    if isinstance(row, list) and len(row) >= 2:
                        uncovered_reqs.append({"id": row[0], "text": row[1]})

            untested_stories = []
            results_stories = self.client.query(cypher_stories, {"doc_id": doc_id})
            if results_stories and isinstance(results_stories, list):
                for row in results_stories:
                    if isinstance(row, list) and len(row) >= 3:
                        untested_stories.append(
                            {"id": row[0], "summary": row[1], "status": row[2]}
                        )

            return {
                "status": "success",
                "doc_id": doc_id,
                "uncovered_requirements_count": len(uncovered_reqs),
                "uncovered_requirements": uncovered_reqs,
                "untested_stories_count": len(untested_stories),
                "untested_stories": untested_stories,
            }

        except Exception as e:
            logger.error(f"GraphAgent: gap_analysis failed for {doc_id}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def find_experts(self, topic: str, limit: int = 5) -> Dict[str, Any]:
        """
        Identify domain experts based on document authorship and story assignment.
        Arguments:
            topic: The topic (keyword) to search for in node content.
            limit: Max number of experts to return.
        """
        if not self.client.is_enabled():
            return {"status": "disabled"}

        try:
            # We search for Documents and Stories that contain the topic.
            # Then we aggregate authors (Docs) and assignees/reporters (Stories).

            # Note: This uses case-insensitive 'CONTAINS'.
            # In a real scenario, full-text index or vector search would be better.

            # 1. Documents (Authors)
            cypher_docs = (
                "MATCH (d:Document) "
                "WHERE toLower(d.name) CONTAINS toLower($topic) OR toLower(d.path) CONTAINS toLower($topic) "
                "WITH d "
                "WHERE d.author IS NOT NULL "
                "RETURN d.author as person, count(d) as score, 'Document' as source"
            )

            # 2. Stories (Assignees)
            cypher_stories_assignee = (
                "MATCH (s:Story) "
                "WHERE toLower(s.summary) CONTAINS toLower($topic) "
                "WITH s "
                "WHERE s.assignee IS NOT NULL "
                "RETURN s.assignee as person, count(s) as score, 'Story Assignee' as source"
            )

            # 3. Stories (Reporters) - maybe give less weight?
            # For now let's just count them.

            results_docs = self.client.query(cypher_docs, {"topic": topic})
            results_stories = self.client.query(
                cypher_stories_assignee, {"topic": topic}
            )

            experts = {}

            def aggregate(results: Any, weight: int = 1):
                if results and isinstance(results, list):
                    for row in results:
                        if isinstance(row, list) and len(row) >= 2:
                            person = row[0]
                            score = row[1]
                            if person:
                                experts[person] = experts.get(person, 0) + (
                                    score * weight
                                )

            aggregate(results_docs, weight=2)  # Documents count more?
            aggregate(results_stories, weight=1)

            # Sort by score desc
            sorted_experts = sorted(experts.items(), key=lambda x: x[1], reverse=True)[
                :limit
            ]

            return {
                "status": "success",
                "topic": topic,
                "experts": [{"person": p, "score": s} for p, s in sorted_experts],
            }

        except Exception as e:
            logger.error(f"GraphAgent: find_experts failed for {topic}", exc_info=True)
            return {"status": "error", "message": str(e)}
