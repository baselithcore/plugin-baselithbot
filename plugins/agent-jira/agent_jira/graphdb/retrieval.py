"""
Advanced graph retrieval operations.

This module contains specialized queries for fetching subgraphs and complex data structures
from the graph database, primarily for visualization and analysis purposes.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from agent_jira.tenant_context import get_current_tenant_id
from agent_jira.config import MULTI_TENANT_REQUIRED

from .inference import _should_include_neighbor
from .schema import (
    _extract_relationship_properties,
    _extract_relationship_type,
    _get_id,
    _process_node,
)
from .styles import NODE_STYLES

logger = logging.getLogger(__name__)


def get_subgraph_for_node(
    query_fn: Callable,
    node_id: str,
    hops: int = 1,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Retrieve the immediate neighborhood (subgraph) of a specific node.

    Args:
        query_fn: The function to execute Cypher queries.
        node_id: The ID of the center node.
        hops: Number of hops to traverse (currently optimized for 1 hop).
        limit: Max number of relationships to return to avoid overfetching.

    Returns:
        A dictionary containing "nodes" and "links" suitable for force-graph visualization.
    """
    tenant_id = get_current_tenant_id()
    if tenant_id:
        # Isolamento stretto: nessun fallback su nodi senza tenant_id
        cypher = (
            f"MATCH (n {{id: $id}}) WHERE n.tenant_id = $tenant_id "
            f"OPTIONAL MATCH (n)-[r]-(m) WHERE m.tenant_id = $tenant_id "
            f"RETURN n, r, m LIMIT {limit}"
        )
        params = {"id": node_id, "tenant_id": tenant_id}
    elif MULTI_TENANT_REQUIRED:
        logger.warning(
            "get_subgraph_for_node chiamato senza tenant in modalità MULTI_TENANT_REQUIRED: nega accesso"
        )
        return {"nodes": [], "links": [], "legend": NODE_STYLES}
    else:
        cypher = f"MATCH (n {{id: $id}}) OPTIONAL MATCH (n)-[r]-(m) RETURN n, r, m LIMIT {limit}"
        params = {"id": node_id}

    try:
        results = query_fn(cypher, params)
        logger.debug(f"[get_subgraph_for_node] Raw results for {node_id}: {results}")
    except Exception as e:
        logger.error(f"[graphdb] Error fetching subgraph for {node_id}: {e}")
        return {"nodes": [], "links": [], "legend": NODE_STYLES}

    nodes_map: Dict[str, Any] = {}
    links: List[Dict[str, Any]] = []

    if not results:
        logger.warning(f"[get_subgraph_for_node] No results returned for {node_id}")
        return {"nodes": [], "links": [], "legend": NODE_STYLES}

    header = results[0] if len(results) > 0 else []
    data_rows = results[1] if len(results) > 1 else []

    label_map = {}
    prop_map = {}

    try:
        if isinstance(header, list) and len(header) >= 2:
            raw_labels = header[1]
            raw_props = []
            if len(header) > 2:
                raw_props = header[2]

            if isinstance(raw_labels, list):
                for i, label in enumerate(raw_labels):
                    label_map[i] = str(label)

            if isinstance(raw_props, list):
                for i, prop in enumerate(raw_props):
                    prop_map[i] = str(prop)

            logger.debug(
                f"[get_subgraph_for_node] Extracted schema - Labels({len(label_map)}), Props({len(prop_map)})"
            )
    except Exception as e:
        logger.warning(
            f"[get_subgraph_for_node] Failed to extract schema from header: {e}"
        )

    if not data_rows:
        return {"nodes": [], "links": [], "legend": NODE_STYLES}

    for row in data_rows:
        if not isinstance(row, list) or len(row) < 1:
            continue

        center_node = row[0]
        if center_node:
            _process_node(center_node, nodes_map, label_map, prop_map, is_center=True)

        if len(row) >= 3:
            rel = row[1]
            neighbor = row[2]

            if rel and neighbor:
                _process_node(neighbor, nodes_map, label_map, prop_map)

                n_id = _get_id(center_node, prop_map)
                m_id = _get_id(neighbor, prop_map)

                if n_id and m_id:
                    parsed_center = nodes_map.get(n_id)
                    parsed_neighbor = nodes_map.get(m_id)
                    if (
                        parsed_center
                        and parsed_neighbor
                        and not _should_include_neighbor(parsed_center, parsed_neighbor)
                    ):
                        continue

                    rel_type = _extract_relationship_type(rel)
                    rel_props = _extract_relationship_properties(rel, prop_map)

                    links.append(
                        {
                            "source": n_id,
                            "target": m_id,
                            "label": rel_type,
                            "properties": rel_props,
                            "confidence": rel_props.get("confidence"),
                            "provenance": rel_props.get("provenance"),
                        }
                    )

    center_graph_node = nodes_map.get(node_id)
    filtered_nodes = list(nodes_map.values())
    if center_graph_node:
        filtered_nodes = [
            node
            for node in filtered_nodes
            if node.get("id") == node_id
            or _should_include_neighbor(center_graph_node, node)
        ]

    return {"nodes": filtered_nodes, "links": links, "legend": NODE_STYLES}


def search_node_by_property(query_fn: Callable, prop: str, value: str) -> Optional[str]:
    """
    Search for a node ID by a specific property value.
    """
    if not prop.isalnum():
        logger.warning(f"[search_node] Invalid property name: {prop}")
        return None

    tenant_id = get_current_tenant_id()
    if tenant_id:
        cypher = (
            f"MATCH (n) WHERE n.{prop} = $val AND n.tenant_id = $tenant_id "
            f"RETURN n.id LIMIT 1"
        )
        params = {"val": value, "tenant_id": tenant_id}
    elif MULTI_TENANT_REQUIRED:
        logger.warning(
            "search_node_by_property senza tenant in MULTI_TENANT_REQUIRED: nega accesso"
        )
        return None
    else:
        cypher = f"MATCH (n) WHERE n.{prop} = $val RETURN n.id LIMIT 1"
        params = {"val": value}

    try:
        results = query_fn(cypher, params)
        data_rows = results[1] if results and len(results) > 1 else []
        if data_rows and len(data_rows) > 0:
            row = data_rows[0]
            if isinstance(row, list) and len(row) > 0:
                val = row[0]
                if isinstance(val, list) and len(val) >= 2:
                    return str(val[1])
                return str(val)
    except Exception as e:
        logger.warning(f"[search_node] Error searching by {prop}={value}: {e}")

    return None
