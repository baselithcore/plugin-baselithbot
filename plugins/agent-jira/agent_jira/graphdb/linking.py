"""
Domain-specific linking and relationship helpers for FalkorDB/RedisGraph.

Provides high-level operations for linking stories, Jira issues, and documents.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from agent_jira.graphdb.relationship_schema import build_relationship_properties

logger = logging.getLogger(__name__)


def link_story_to_doc(
    upsert_node_fn: Callable,
    upsert_edge_fn: Callable,
    story_id: str,
    doc_id: str,
    *,
    title: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
) -> None:
    """
    Link a user story to a knowledge base document (Story DERIVES_FROM Document).

    Args:
        upsert_node_fn: Node upsert function
        upsert_edge_fn: Edge upsert function
        story_id: Story identifier
        doc_id: Document identifier
        title: Optional story title
        priority: Optional story priority
        status: Optional story status
    """
    props: dict[str, Any] = {}
    if title:
        props["title"] = title
    if priority:
        props["priority"] = priority
    if status:
        props["status"] = status
    if props:
        upsert_node_fn(story_id, labels=["Story"], properties=props)
    upsert_edge_fn(
        story_id,
        "DERIVES_FROM",
        doc_id,
        properties=build_relationship_properties(
            "DERIVES_FROM",
            provenance="application_linking",
            extraction_method="graphdb_link_story_to_doc",
        ),
    )


def link_story_to_jira(
    upsert_node_fn: Callable,
    upsert_edge_fn: Callable,
    story_id: str,
    *,
    issue_key: Optional[str] = None,
    issue_status: Optional[str] = None,
    issue_url: Optional[str] = None,
) -> None:
    """
    Link a story to a Jira issue, creating the issue node if necessary.

    Args:
        upsert_node_fn: Node upsert function
        upsert_edge_fn: Edge upsert function
        story_id: Story identifier
        issue_key: Jira issue key (e.g., "PROJ-123")
        issue_status: Jira issue status
        issue_url: Jira issue URL
    """
    if not issue_key:
        return
    props: dict[str, Any] = {}
    if issue_status:
        props["status"] = issue_status
    if issue_url:
        props["url"] = issue_url
    upsert_node_fn(issue_key, labels=["JiraIssue"], properties=props)
    upsert_edge_fn(
        story_id,
        "LINKED_ISSUE",
        issue_key,
        properties=build_relationship_properties(
            "LINKED_ISSUE",
            provenance="application_linking",
            extraction_method="graphdb_link_story_to_jira",
        ),
    )


def get_linked_jiras(query_fn: Callable, doc_id: str) -> list[dict[str, Any]]:
    """
    Retrieve Jira issues linked to a specific document.

    Args:
        query_fn: Query execution function
        doc_id: Document identifier

    Returns:
        List of dicts with keys: key, status, url, summary
    """
    # Schema: (Story)-[:DERIVES_FROM]->(Document)
    #         (Story)-[:LINKED_ISSUE]->(JiraIssue)
    # We want JiraIssues linked to a Story that derives from the Document.

    cypher = (
        "MATCH (j:JiraIssue)<-[:LINKED_ISSUE]-(s:Story)-[:DERIVES_FROM]->(d {id: $doc_id}) "
        "RETURN j.id, j.status, j.url, s.title"
    )

    results = query_fn(cypher, {"doc_id": doc_id})

    def _unpack(v: Any) -> Any:
        """Unpack FalkorDB values handling both compact and singleton-list payloads."""
        while isinstance(v, list) and len(v) == 1:
            v = v[0]
        if isinstance(v, list) and len(v) >= 2 and isinstance(v[0], int):
            return v[1]
        return v

    jiras = []
    # FalkorDB usually returns [header, data_rows, stats], but tests and some client
    # adapters may hand us the data rows directly.
    if (
        isinstance(results, list)
        and len(results) > 1
        and isinstance(results[1], list)
        and (not results[1] or isinstance(results[1][0], list))
    ):
        data_rows = results[1]
    elif isinstance(results, list):
        data_rows = results
    else:
        data_rows = []
    for row in data_rows:
        if not isinstance(row, list) or len(row) < 4:
            continue

        key = _unpack(row[0])
        status = _unpack(row[1])
        url = _unpack(row[2])
        summary = _unpack(row[3])

        if key:
            jiras.append(
                {
                    "key": str(key),
                    "status": str(status) if status else None,
                    "url": str(url) if url else None,
                    "summary": str(summary) if summary else "No Summary",
                }
            )

    return jiras


def record_document_feedback(
    query_fn: Callable,
    document_id: str,
    feedback: str,
    comment: Optional[str] = None,
) -> None:
    """
    Update feedback counters on a Document node.

    Tracks:
    - feedback_total
    - feedback_positive / feedback_negative
    - last_feedback_at (ISO8601)
    - last_feedback_comment (truncated to 500 chars)

    Args:
        query_fn: Query execution function
        document_id: Document identifier
        feedback: Feedback sentiment ("positive" or "negative")
        comment: Optional feedback comment
    """
    if not document_id:
        return

    sentiment = feedback.strip().lower()
    is_positive = sentiment == "positive"
    is_negative = sentiment == "negative"
    now_iso = datetime.now(timezone.utc).isoformat()
    trimmed_comment = (comment or "").strip()
    if trimmed_comment:
        trimmed_comment = trimmed_comment[:500]  # security/readability limit

    cypher = (
        "MERGE (d:Document {id: $id}) "
        "SET d.feedback_total = coalesce(d.feedback_total, 0) + 1, "
        "    d.last_feedback_at = $now "
        + (
            "    , d.feedback_positive = coalesce(d.feedback_positive, 0) + 1 "
            if is_positive
            else ""
        )
        + (
            "    , d.feedback_negative = coalesce(d.feedback_negative, 0) + 1 "
            if is_negative
            else ""
        )
        + ("    , d.last_feedback_comment = $comment " if trimmed_comment else "")
        + "RETURN d.id"
    )
    query_fn(
        cypher,
        {"id": document_id, "now": now_iso, "comment": trimmed_comment},
    )
