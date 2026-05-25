"""
Basic node and edge CRUD operations for FalkorDB/RedisGraph.

Provides fundamental graph database operations: create, read, update, delete nodes and edges.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from agent_jira.graphdb.query_builder import format_labels
from agent_jira.graphdb.relationship_schema import (
    build_relationship_properties,
    normalize_relationship_type,
)

logger = logging.getLogger(__name__)


def get_node(
    query_fn: Callable,
    node_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve node properties by ID.

    Args:
        query_fn: Query execution function
        node_id: Node identifier

    Returns:
        Node properties dict or None if not found
    """
    try:
        # Safe parameterized query
        query = "MATCH (n {id: $id}) RETURN n"
        result = query_fn(query, {"id": node_id})

        # FalkorDB compact format: [header, [data_rows], stats]
        # Node compact format: [8, [internal_id, [label_ids], [[prop_id, type_code, value], ...]]]
        data_rows = result[1] if result and len(result) > 1 else []
        if data_rows:
            first_row = data_rows[0]
            if isinstance(first_row, list) and len(first_row) > 0:
                node = first_row[0]
                if hasattr(node, "properties"):
                    return node.properties  # type: ignore[union-attr]
                if isinstance(node, dict):
                    return node
                # Compact format: [type_code=8, [internal_id, [label_ids], [[prop_id, type, val], ...]]]
                if isinstance(node, list) and len(node) >= 2:
                    from agent_jira.graphdb.schema import _extract_properties

                    props = _extract_properties(node, {})
                    return props if props else None

        return None
    except Exception as exc:
        logger.warning(f"[graphdb] get_node failed for {node_id}: {exc}")
        return None


def upsert_node(
    query_fn: Callable,
    node_id: str,
    *,
    labels: Sequence[str] | None = None,
    properties: Mapping[str, Any] | None = None,
) -> None:
    """
    Create or update a node with stable ID and mergeable properties.

    Args:
        query_fn: Query execution function
        node_id: Node identifier
        labels: Optional list of node labels
        properties: Optional property dictionary
    """
    # Match by ID only to prevent duplicates if labels change
    # Then SET the new labels. Note: This adds labels, it does not remove old ones.
    label_clause = format_labels(labels or [])
    cypher = f"MERGE (n {{id: $id}}) SET n += $props{', n' + label_clause if label_clause else ''} RETURN n.id"
    query_fn(cypher, {"id": node_id, "props": properties or {}})


def upsert_edge(
    query_fn: Callable,
    source_id: str,
    relationship: str,
    target_id: str,
    *,
    properties: Mapping[str, Any] | None = None,
) -> None:
    """
    Create or update a directed relationship between two nodes.

    Args:
        query_fn: Query execution function
        source_id: Source node identifier
        relationship: Relationship type
        target_id: Target node identifier
        properties: Optional relationship properties
    """
    rel = normalize_relationship_type(relationship)
    edge_props = build_relationship_properties(rel, properties=properties)
    cypher = (
        f"MERGE (s {{id: $source_id}}) "
        f"MERGE (t {{id: $target_id}}) "
        f"MERGE (s)-[r:{rel}]->(t) "
        "SET r += $props "
        "RETURN type(r)"
    )
    query_fn(
        cypher,
        {
            "source_id": source_id,
            "target_id": target_id,
            "props": edge_props,
        },
    )


def delete_node(query_fn: Callable, node_id: str) -> None:
    """
    Delete a node and all its incident relationships.

    Args:
        query_fn: Query execution function
        node_id: Node identifier to delete
    """
    cypher = "MATCH (n {id: $id}) DETACH DELETE n"
    query_fn(cypher, {"id": node_id})


def delete_orphan_nodes(query_fn: Callable) -> int:
    """
    Delete orphan nodes (without relationships) from the graph.
    Explicitly excludes Document nodes for safety.

    Args:
        query_fn: Query execution function

    Returns:
        Number of nodes deleted
    """
    # Query: Find nodes that have NO relationships (--) and are NOT Documents.
    cypher = "MATCH (n) WHERE NOT (n)--() AND NOT n:Document DELETE n RETURN count(n) as deleted"
    try:
        result = query_fn(cypher)
        # FalkorDB compact format: [header, [data_rows], stats]
        data_rows = result[1] if result and len(result) > 1 else []
        if data_rows and isinstance(data_rows[0], list) and data_rows[0]:
            val = data_rows[0][0]
            # Scalar values are [type_code, value] in compact format
            count = val[1] if isinstance(val, list) and len(val) >= 2 else val
            return int(count)  # type: ignore[arg-type]
        return 0
    except Exception as exc:
        logger.warning(f"[graphdb] delete_orphan_nodes failed: {exc}")
        return 0
