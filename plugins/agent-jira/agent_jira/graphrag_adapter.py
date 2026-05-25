"""
Integrazione opzionale con FalkorDB GraphRAG SDK.

Se l'SDK non è installato o il flag è disabilitato, le funzioni sono no-op e
ritornano i risultati originali della ricerca Qdrant.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from agent_jira.graphdb import graph_db
from agent_jira.config import GRAPH_RAG_ENABLED

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    """True se il flag è attivo e il database a grafo è disponibile."""

    return GRAPH_RAG_ENABLED and graph_db.is_enabled()


def expand_with_graph(
    hits: Sequence[Any],
    query_vector: Any | None = None,
    limit: int | None = None,
) -> Sequence[Any]:
    """
    Hook per espandere i risultati usando GraphRAG.
    Oggi ritorna i risultati originali; quando l'SDK è disponibile si potrà
    implementare traversal/arricchimento opzionale.
    """

    if not GRAPH_RAG_ENABLED:
        return hits

    # Custom expansion using our graph_db
    # We ignore the SDK for now as we want specific custom logic (and SDK is optional)
    from agent_jira.graphdb import graph_db

    if not graph_db.is_enabled():
        return hits

    enriched_hits = []
    # Collect all doc IDs
    doc_ids = []
    for hit in hits:
        payload = getattr(hit, "payload", None) or {}
        d_id = payload.get("document_id")
        if d_id:
            doc_ids.append(d_id)

    if not doc_ids:
        return hits

    # Query graph for neighbors of these docs
    # 1. Related Stories (linked via DERIVES_FROM)
    # 2. Similar Documents (SIMILAR)
    # 3. Code Components (if path matches) - Optional for now

    # We can do a batched query or per-doc. Per-doc is safer for now.

    for hit in hits:
        payload = getattr(hit, "payload", None) or {}
        doc_id = payload.get("document_id")

        # Init extra graph context
        graph_context = []

        if doc_id:
            # A. Get Linked Stories
            try:
                # (s:Story)-[:DERIVES_FROM]->(d:Document)
                q_stories = (
                    "MATCH (s:Story)-[:DERIVES_FROM]->(d {id: $doc_id}) "
                    "RETURN s.title, s.status"
                )
                res_stories = graph_db.query(q_stories, {"doc_id": doc_id})
                for row in res_stories:
                    if isinstance(row, list) and len(row) >= 1:
                        title = row[0]
                        status = row[1] if len(row) > 1 else ""
                        graph_context.append(f"Related Story: {title} ({status})")
            except Exception:
                pass

            # B. Get Similar Docs (via Graph) that might not be in vector results
            # (d)-[r:SIMILAR]-(other)
            try:
                q_sim = (
                    "MATCH (d {id: $doc_id})-[r:SIMILAR]-(o) "
                    "RETURN o.source, r.score ORDER BY r.score DESC LIMIT 3"
                )
                res_sim = graph_db.query(q_sim, {"doc_id": doc_id})
                for row in res_sim:
                    if isinstance(row, list) and len(row) >= 1:
                        src = row[0]
                        # score = row[1]
                        graph_context.append(f"Graph Parallel: {src}")
            except Exception:
                pass

        # Append to payload text or a special field?
        # Standard context builder uses "text" field.
        # We can append to 'content' or 'text' in payload to make it visible to LLM.

        if graph_context:
            extra_text = "\n\n[Graph Context]:\n" + "\n".join(graph_context)
            # Modify payload in place (it's a dict usually)
            # Qdrant Hit payload is a dict or object.
            # If it's a python client object, payload is a dict.
            if "text" in payload:
                payload["text"] += extra_text
            # Also add to metadata for debugging
            payload["graph_expanded"] = True

        enriched_hits.append(hit)

    return enriched_hits


__all__ = ["is_enabled", "expand_with_graph"]
