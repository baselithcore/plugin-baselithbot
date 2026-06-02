"""Knowledge-graph algorithms (graphify PR2).

Operates on the entity-level subgraph loaded into a :class:`networkx.DiGraph`
via :meth:`KnowledgeGraphStore.to_networkx`. All algorithms are stateless +
pure: they take a graph in, return ranked / partitioned data structures.

Algorithms
----------
- :func:`pagerank` — entity importance (Brin & Page 1998). Identifies
  "god nodes" — entities with disproportionate inbound authority.
- :func:`degree_centrality` — fast first-pass importance metric.
- :func:`leiden_communities` — community detection (Traag et al. 2019).
  Falls back to weakly-connected components when ``leidenalg`` is not
  installed — same shape, lower quality.
- :func:`surprising_connections` — high-confidence edges that cross
  community boundaries. Graphify's "surprising connections" feature.
- :func:`snapshot` — pre-baked dict that bundles all the above for one
  graph pass (saves repeated NetworkX traversals).

Design
------
- NetworkX is the canonical algorithm container; igraph is used purely as
  the input format Leiden requires. Conversion is cheap (linear in nodes
  + edges) and isolated to :func:`leiden_communities`.
- The functions never raise on an empty graph: an empty graph returns
  empty data structures. Callers can assume the result type unconditionally.
- Top-N caps are enforced by callers, not here — algorithms compute the
  full distribution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from llm_wiki.config import GRAPH_LEIDEN_RESOLUTION, GRAPH_PAGERANK_ALPHA

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CentralityScore:
    entity_id: str
    name: str
    kind: str
    score: float


@dataclass(slots=True)
class Community:
    """A Leiden community: bag of entity ids + cohesion metric.

    ``cohesion`` is the fraction of intra-community edges over total
    incident edges (Newman modularity contribution proxy). Higher =
    tighter community. ~0.0 for trivial singletons.
    """

    id: int
    members: list[str]
    cohesion: float


@dataclass(slots=True)
class SurprisingEdge:
    """High-confidence edge that crosses a community boundary."""

    src: str
    dst: str
    kind: str
    confidence: float
    src_community: int
    dst_community: int


def _ensure_graph(g: Any) -> Any | None:
    """Returns the graph if usable, else None."""
    if g is None:
        return None
    try:
        # NetworkX exposes number_of_nodes/edges as universal API.
        if g.number_of_nodes() == 0:
            return None
        return g
    except Exception:
        return None


# --- ranking ---------------------------------------------------------------


def pagerank(
    graph: Any,
    *,
    alpha: float = GRAPH_PAGERANK_ALPHA,
    top_n: int | None = None,
) -> list[CentralityScore]:
    """PageRank over the entity DiGraph. Weighted by edge ``confidence``.

    Sink nodes (no outgoing edges) are absorbed via NetworkX's default
    teleport — no need for a personalization vector.
    """
    g = _ensure_graph(graph)
    if g is None:
        return []
    try:
        import networkx as nx  # type: ignore[import-not-found]

        scores: dict[str, float] = nx.pagerank(g, alpha=alpha, weight="confidence")
    except Exception as exc:
        logger.warning("[graph.algorithms] pagerank failed: %s", exc)
        return []
    return _topn_scores(g, scores, top_n=top_n)


def degree_centrality(graph: Any, *, top_n: int | None = None) -> list[CentralityScore]:
    """Combined in+out degree centrality. Fast first-pass importance."""
    g = _ensure_graph(graph)
    if g is None:
        return []
    try:
        import networkx as nx  # type: ignore[import-not-found]

        scores = nx.degree_centrality(g.to_undirected())
    except Exception as exc:
        logger.warning("[graph.algorithms] degree_centrality failed: %s", exc)
        return []
    return _topn_scores(g, scores, top_n=top_n)


def _topn_scores(
    g: Any,
    scores: dict[str, float],
    *,
    top_n: int | None,
) -> list[CentralityScore]:
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if top_n is not None:
        ranked = ranked[:top_n]
    out: list[CentralityScore] = []
    for entity_id, score in ranked:
        attrs = g.nodes.get(entity_id, {}) or {}
        out.append(
            CentralityScore(
                entity_id=entity_id,
                name=str(attrs.get("name") or entity_id),
                kind=str(attrs.get("kind") or ""),
                score=float(score),
            )
        )
    return out


# --- communities ----------------------------------------------------------


def leiden_communities(
    graph: Any,
    *,
    resolution: float = GRAPH_LEIDEN_RESOLUTION,
) -> list[Community]:
    """Leiden community detection (Traag, Waltman, van Eck 2019).

    Falls back to weakly-connected-components if ``leidenalg`` is not
    installed — same return shape, lower quality. Logs a warning so users
    know to ``pip install -e ".[graph]"``.
    """
    g = _ensure_graph(graph)
    if g is None:
        return []
    try:
        import leidenalg  # type: ignore[import-not-found]
    except ImportError:
        logger.warning(
            "[graph.algorithms] leidenalg/igraph not installed; falling back to "
            "weakly-connected components. Install with: pip install -e '.[graph]'"
        )
        return _fallback_communities(g)

    try:
        ig_graph, id_map = _to_igraph(g)
        partition = leidenalg.find_partition(
            ig_graph,
            leidenalg.RBConfigurationVertexPartition,
            resolution_parameter=resolution,
            weights="confidence",
        )
    except Exception as exc:
        logger.warning("[graph.algorithms] leiden failed: %s — using fallback", exc)
        return _fallback_communities(g)

    communities: list[Community] = []
    for cid, members_idx in enumerate(partition):
        members = [id_map[i] for i in members_idx]
        communities.append(
            Community(id=cid, members=members, cohesion=_cohesion(g, set(members)))
        )
    # Largest first — UX shows substantive communities, then long-tail.
    communities.sort(key=lambda c: len(c.members), reverse=True)
    return communities


def _fallback_communities(g: Any) -> list[Community]:
    """Weakly-connected components as a poor-man's community partition."""
    try:
        import networkx as nx  # type: ignore[import-not-found]

        components = list(nx.weakly_connected_components(g))
    except Exception as exc:
        logger.warning("[graph.algorithms] fallback components failed: %s", exc)
        return []
    out: list[Community] = []
    for cid, comp in enumerate(components):
        members = sorted(comp)
        out.append(
            Community(id=cid, members=members, cohesion=_cohesion(g, set(members)))
        )
    out.sort(key=lambda c: len(c.members), reverse=True)
    return out


def _to_igraph(g: Any) -> tuple[Any, list[str]]:
    """networkx.DiGraph → igraph.Graph (undirected, weighted by confidence).

    Leiden runs on undirected graphs by default — the modularity gains
    of directed variants don't beat the conversion overhead at our scale.
    """
    import igraph as ig  # type: ignore[import-not-found]

    nodes = list(g.nodes())
    id_to_idx = {nid: i for i, nid in enumerate(nodes)}
    edges = []
    weights = []
    # Coalesce parallel edges → max confidence wins (graphify pattern).
    seen: dict[tuple[int, int], float] = {}
    for u, v, data in g.edges(data=True):
        a, b = id_to_idx[u], id_to_idx[v]
        key = (min(a, b), max(a, b))
        w = float(data.get("confidence", 1.0) or 0.0)
        if key in seen:
            seen[key] = max(seen[key], w)
        else:
            seen[key] = w
    for (a, b), w in seen.items():
        edges.append((a, b))
        weights.append(w)
    ig_g = ig.Graph(n=len(nodes), edges=edges, directed=False)
    ig_g.es["confidence"] = weights
    return ig_g, nodes


def _cohesion(g: Any, members: set[str]) -> float:
    """Internal edges / (internal + boundary) for the member set."""
    if len(members) <= 1:
        return 0.0
    internal = 0
    boundary = 0
    for u, v in g.edges():
        u_in = u in members
        v_in = v in members
        if u_in and v_in:
            internal += 1
        elif u_in or v_in:
            boundary += 1
    total = internal + boundary
    return internal / total if total else 0.0


# --- surprising connections ------------------------------------------------


def surprising_connections(
    graph: Any,
    communities: list[Community],
    *,
    confidence_min: float = 0.7,
    top_n: int | None = 20,
) -> list[SurprisingEdge]:
    """High-confidence edges connecting different communities.

    "Surprising" in the graphify sense: structurally these entities live
    in different conceptual clusters, but the LLM extraction says they
    are related with high confidence. Often the most insight-dense edges
    in the whole graph.
    """
    g = _ensure_graph(graph)
    if g is None or not communities:
        return []

    membership: dict[str, int] = {}
    for c in communities:
        for m in c.members:
            membership[m] = c.id

    surprising: list[SurprisingEdge] = []
    for u, v, data in g.edges(data=True):
        conf = float(data.get("confidence", 0.0) or 0.0)
        if conf < confidence_min:
            continue
        cu = membership.get(u)
        cv = membership.get(v)
        if cu is None or cv is None or cu == cv:
            continue
        surprising.append(
            SurprisingEdge(
                src=u,
                dst=v,
                kind=str(data.get("kind") or ""),
                confidence=conf,
                src_community=cu,
                dst_community=cv,
            )
        )
    surprising.sort(key=lambda s: s.confidence, reverse=True)
    if top_n is not None:
        surprising = surprising[:top_n]
    return surprising


# --- bundled snapshot ------------------------------------------------------


@dataclass(slots=True)
class GraphSnapshot:
    """One-shot pre-computed analytics over the entity subgraph.

    Used by ``/api/graph/report`` and the CLI to avoid running 3+ separate
    NetworkX passes when one is enough. Cheap to construct (~0.1s on 5k
    nodes); callers can memoize if needed.
    """

    pagerank: list[CentralityScore]
    degree: list[CentralityScore]
    communities: list[Community]
    surprising: list[SurprisingEdge]
    node_count: int
    edge_count: int


def snapshot(
    graph: Any,
    *,
    top_n: int | None = None,
    resolution: float = GRAPH_LEIDEN_RESOLUTION,
    surprising_confidence_min: float = 0.7,
) -> GraphSnapshot:
    g = _ensure_graph(graph)
    if g is None:
        return GraphSnapshot(
            pagerank=[],
            degree=[],
            communities=[],
            surprising=[],
            node_count=0,
            edge_count=0,
        )
    communities = leiden_communities(g, resolution=resolution)
    return GraphSnapshot(
        pagerank=pagerank(g, top_n=top_n),
        degree=degree_centrality(g, top_n=top_n),
        communities=communities,
        surprising=surprising_connections(
            g, communities, confidence_min=surprising_confidence_min, top_n=top_n
        ),
        node_count=g.number_of_nodes(),
        edge_count=g.number_of_edges(),
    )


__all__ = [
    "CentralityScore",
    "Community",
    "GraphSnapshot",
    "SurprisingEdge",
    "degree_centrality",
    "leiden_communities",
    "pagerank",
    "snapshot",
    "surprising_connections",
]
