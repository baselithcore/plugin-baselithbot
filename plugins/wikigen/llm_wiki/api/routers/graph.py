"""Knowledge-graph API (graphify-inspired).

Public read-only endpoints exposing the FalkorDB-backed entity graph:

- ``GET /api/graph/stats`` — node + edge counts.
- ``GET /api/graph/entity/{id}`` — single entity record.
- ``GET /api/graph/search?q=&kind=&limit=`` — substring search on entity name.
- ``GET /api/graph/neighbors/{id}?hops=&confidence_min=&limit=`` — k-hop
  entity neighborhood, filtered by confidence tier.
- ``GET /api/graph/path?src=&dst=&max_hops=`` — shortest entity path.

All endpoints return ``503`` if graph DB is disabled or unreachable —
graph features are opt-in, the rest of the API stays functional.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from llm_wiki import config
from llm_wiki.config import (
    GRAPH_CENTRALITY_TOP_N,
    GRAPH_CONFIDENCE_MIN,
    GRAPH_LEIDEN_RESOLUTION,
    GRAPH_RAG_HOPS,
)
from llm_wiki.graphdb.store import EntityRecord, get_kg_store


def _require_graph_read_or_setup_mode(request: Request) -> None:
    """Gate graph endpoints.

    - Postgres OFF (setup mode / dev senza auth): allow. Coerente con
      gli altri router (ingest, chat, feedback) che restano accessibili
      in setup mode per non bloccare wizard / sviluppo locale.
    - Postgres ON: richiede permesso ``graph.read`` (mig 013).
      Granted a tutti i 4 ruoli system — il grafo è read-only, basic
      tier come ``obsidian.open``.
    """
    if not config.POSTGRES_ENABLED:
        return
    from llm_wiki.auth.dependencies import require_permission

    require_permission("graph.read")(request)


router = APIRouter(
    prefix="/api/graph",
    tags=["graph"],
    dependencies=[Depends(_require_graph_read_or_setup_mode)],
)


def _ensure_enabled() -> Any:
    store = get_kg_store()
    if not store.enabled:
        raise HTTPException(
            status_code=503,
            detail=(
                "knowledge graph not available (GRAPH_DB_ENABLED=false or FalkorDB unreachable)"
            ),
        )
    return store


def _entity_dto(e: EntityRecord) -> dict[str, Any]:
    return {"id": e.id, "name": e.name, "kind": e.kind, "aliases": e.aliases}


@router.get("/stats")
def stats() -> dict[str, Any]:
    """Top-level metrics. Returns zeros if graph disabled, never 503 —
    used by the UI to render a 'graph: off' banner.
    """
    store = get_kg_store()
    if not store.enabled:
        return {
            "enabled": False,
            "nodes": 0,
            "edges": 0,
            "entities": 0,
            "mentions": 0,
            "relations": 0,
        }
    return {"enabled": True, **store.stats()}


@router.get("/entity/{entity_id}")
def get_entity(entity_id: str) -> dict[str, Any]:
    store = _ensure_enabled()
    ent = store.get_entity(entity_id)
    if ent is None:
        raise HTTPException(status_code=404, detail=f"entity {entity_id!r} not found")
    return _entity_dto(ent)


@router.get("/search")
def search_entities(
    q: str = Query(..., min_length=1, max_length=200),
    kind: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=25, ge=1, le=100),
) -> dict[str, Any]:
    store = _ensure_enabled()
    rows = store.search_entities(q, kind=kind, limit=limit)
    return {
        "query": q,
        "kind": kind,
        "count": len(rows),
        "results": [_entity_dto(r) for r in rows],
    }


@router.get("/neighbors/{entity_id}")
def neighbors(
    entity_id: str,
    hops: int = Query(default=GRAPH_RAG_HOPS, ge=1, le=3),
    confidence_min: float = Query(default=GRAPH_CONFIDENCE_MIN, ge=0.0, le=1.0),
    kind: str | None = Query(default=None, description="Filter on relation kind"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    store = _ensure_enabled()
    if store.get_entity(entity_id) is None:
        raise HTTPException(status_code=404, detail=f"entity {entity_id!r} not found")
    rows = store.neighbors(
        entity_id,
        hops=hops,
        confidence_min=confidence_min,
        relation_kind=kind,
        limit=limit,
    )
    return {
        "entity_id": entity_id,
        "hops": hops,
        "confidence_min": confidence_min,
        "count": len(rows),
        "results": [_entity_dto(r) for r in rows],
    }


@router.get("/path")
def shortest_path(
    src: str = Query(..., min_length=1),
    dst: str = Query(..., min_length=1),
    max_hops: int = Query(default=5, ge=1, le=8),
) -> dict[str, Any]:
    store = _ensure_enabled()
    path = store.shortest_path(src, dst, max_hops=max_hops)
    return {
        "src": src,
        "dst": dst,
        "max_hops": max_hops,
        "found": bool(path),
        "length": max(0, len(path) - 1),
        "path": path,
    }


# --- PR2: algorithms endpoints --------------------------------------------


def _load_networkx() -> Any:
    """Snapshot the entity graph as networkx.DiGraph. Returns None if
    NetworkX is not installed (graph extra not installed) or graph empty.
    Caller decides how to surface that.
    """
    store = _ensure_enabled()
    return store.to_networkx()


def _centrality_dto(s: Any) -> dict[str, Any]:
    return {"entity_id": s.entity_id, "name": s.name, "kind": s.kind, "score": s.score}


@router.get("/centrality")
def centrality(
    metric: str = Query(default="pagerank", pattern="^(pagerank|degree)$"),
    top_n: int = Query(default=GRAPH_CENTRALITY_TOP_N, ge=1, le=200),
) -> dict[str, Any]:
    """Top-N entities by centrality. ``metric`` ∈ {pagerank, degree}."""
    from llm_wiki.graphdb.algorithms import degree_centrality
    from llm_wiki.graphdb.algorithms import pagerank as pagerank_algo

    g = _load_networkx()
    if g is None:
        return {"metric": metric, "top_n": top_n, "count": 0, "results": []}
    fn = pagerank_algo if metric == "pagerank" else degree_centrality
    scores = fn(g, top_n=top_n)
    return {
        "metric": metric,
        "top_n": top_n,
        "count": len(scores),
        "results": [_centrality_dto(s) for s in scores],
    }


@router.get("/communities")
def communities(
    resolution: float = Query(default=GRAPH_LEIDEN_RESOLUTION, ge=0.1, le=10.0),
    max_communities: int = Query(default=50, ge=1, le=500),
    members_preview: int = Query(default=10, ge=0, le=100),
) -> dict[str, Any]:
    """Leiden community partition. Falls back to weakly-connected
    components when ``leidenalg`` is not installed (same response shape).
    """
    from llm_wiki.graphdb.algorithms import leiden_communities

    g = _load_networkx()
    if g is None:
        return {"resolution": resolution, "count": 0, "communities": []}
    parts = leiden_communities(g, resolution=resolution)[:max_communities]
    return {
        "resolution": resolution,
        "count": len(parts),
        "communities": [
            {
                "id": c.id,
                "size": len(c.members),
                "cohesion": c.cohesion,
                "members": c.members[: members_preview or None],
            }
            for c in parts
        ],
    }


@router.get("/surprising")
def surprising(
    confidence_min: float = Query(default=0.7, ge=0.0, le=1.0),
    top_n: int = Query(default=20, ge=1, le=200),
    resolution: float = Query(default=GRAPH_LEIDEN_RESOLUTION, ge=0.1, le=10.0),
) -> dict[str, Any]:
    """Cross-community high-confidence edges (graphify-style surprising
    connections). Often the most insight-dense relations in the graph.
    """
    from llm_wiki.graphdb.algorithms import (
        leiden_communities,
        surprising_connections,
    )

    g = _load_networkx()
    if g is None:
        return {"confidence_min": confidence_min, "count": 0, "results": []}
    parts = leiden_communities(g, resolution=resolution)
    edges = surprising_connections(g, parts, confidence_min=confidence_min, top_n=top_n)
    return {
        "confidence_min": confidence_min,
        "count": len(edges),
        "results": [
            {
                "src": e.src,
                "dst": e.dst,
                "kind": e.kind,
                "confidence": e.confidence,
                "src_community": e.src_community,
                "dst_community": e.dst_community,
            }
            for e in edges
        ],
    }


@router.post("/report")
def generate_report() -> dict[str, Any]:
    """Trigger generation of GRAPH_REPORT.md + graph.json under
    GRAPH_REPORT_DIR. Returns the absolute paths. Non-idempotent: each
    call overwrites the previous artifacts.
    """
    from llm_wiki.graphdb.report import generate

    g = _load_networkx()
    paths = generate(g)
    return {
        "markdown": str(paths.markdown),
        "json": str(paths.json),
    }


@router.get("/data")
def graph_data(
    confidence_min: float = Query(default=0.0, ge=0.0, le=1.0),
    resolution: float = Query(default=GRAPH_LEIDEN_RESOLUTION, ge=0.1, le=10.0),
    top_n: int = Query(default=GRAPH_CENTRALITY_TOP_N, ge=1, le=500),
    max_nodes: int = Query(default=500, ge=1, le=5000),
) -> dict[str, Any]:
    """Full graph payload for the React UI (PR3).

    Same JSON shape as ``graph.json`` artifact but built in-memory; no
    file I/O. Filters at the API level keep wire payload bounded even
    on large graphs (a 2k-node + 8k-edge graph weighs ~600 KB JSON).

    ``confidence_min`` filters edges; ``max_nodes`` caps the node list
    by PageRank descending — high-rank nodes survive, long-tail nodes
    plus their incident edges are dropped.
    """
    from llm_wiki.graphdb.algorithms import snapshot
    from llm_wiki.graphdb.report import render_json

    store = get_kg_store()
    if not store.enabled:
        return {
            "enabled": False,
            "stats": {"node_count": 0, "edge_count": 0, "community_count": 0},
            "nodes": [],
            "edges": [],
            "communities": [],
            "surprising": [],
        }
    g = store.to_networkx()
    if g is None:
        return {
            "enabled": True,
            "stats": {"node_count": 0, "edge_count": 0, "community_count": 0},
            "nodes": [],
            "edges": [],
            "communities": [],
            "surprising": [],
        }
    # confidence filter on edges (drop low-conf), then cap nodes by PageRank.
    if confidence_min > 0.0:
        import networkx as nx  # type: ignore[import-not-found]

        keep = [
            (u, v)
            for u, v, data in g.edges(data=True)
            if float(data.get("confidence", 0.0)) >= confidence_min
        ]
        h = nx.DiGraph()
        h.add_nodes_from(g.nodes(data=True))
        for u, v in keep:
            h.add_edge(u, v, **g.edges[u, v])
        g = h
    snap = snapshot(g, top_n=top_n, resolution=resolution)
    if g.number_of_nodes() > max_nodes:
        top_ids = {s.entity_id for s in snap.pagerank[:max_nodes]}
        g = g.subgraph(top_ids).copy()
        snap = snapshot(g, top_n=top_n, resolution=resolution)
    import json as _json

    payload = _json.loads(render_json(g, snap))
    payload["enabled"] = True
    return payload


__all__ = ["router"]
