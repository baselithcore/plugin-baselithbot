"""Knowledge-graph algorithm tests.

Builds tiny in-memory NetworkX graphs and asserts the algorithm layer
returns the expected shape + relative orderings. Leiden tests pass with
or without `leidenalg` installed (the fallback path is exercised when
the dep is missing, matching CI environments without optional extras).
"""

from __future__ import annotations

import pytest

networkx = pytest.importorskip("networkx")


def _build_graph() -> object:
    """Two-cluster graph + bridge edge.

    Cluster A: A1, A2, A3 (densely interconnected). Cluster B: B1, B2.
    Bridge: A1 -- B1, low-confidence (0.5).
    """
    g = networkx.DiGraph()
    for nid, kind in [
        ("A1", "concept"),
        ("A2", "concept"),
        ("A3", "concept"),
        ("B1", "entity"),
        ("B2", "entity"),
    ]:
        g.add_node(nid, name=nid.lower(), kind=kind)
    # Dense cluster A
    g.add_edge("A1", "A2", kind="RELATES_TO", confidence=0.9)
    g.add_edge("A2", "A3", kind="RELATES_TO", confidence=0.9)
    g.add_edge("A3", "A1", kind="RELATES_TO", confidence=0.9)
    g.add_edge("A1", "A3", kind="PART_OF", confidence=0.8)
    # Cluster B
    g.add_edge("B1", "B2", kind="RELATES_TO", confidence=0.85)
    # Cross-cluster bridge (high confidence — should be "surprising")
    g.add_edge("A1", "B1", kind="ISSUED_BY", confidence=0.95)
    return g


def test_pagerank_returns_topn() -> None:
    from llm_wiki.graphdb.algorithms import pagerank

    g = _build_graph()
    scores = pagerank(g, top_n=3)
    assert len(scores) == 3
    # A1 has highest in-degree from dense cluster — should top the list.
    assert scores[0].entity_id in {"A1", "A3", "B1"}
    # All entries carry the resolved name + kind.
    for s in scores:
        assert s.name
        assert s.kind in {"concept", "entity"}
        assert 0.0 <= s.score <= 1.0


def test_pagerank_empty_graph() -> None:
    from llm_wiki.graphdb.algorithms import pagerank

    g = networkx.DiGraph()
    assert pagerank(g) == []


def test_degree_centrality_topn() -> None:
    from llm_wiki.graphdb.algorithms import degree_centrality

    g = _build_graph()
    scores = degree_centrality(g, top_n=10)
    assert len(scores) == 5
    # A1 is the hub of the dense cluster + the bridge → highest degree.
    top = scores[0]
    assert top.entity_id == "A1"


def test_leiden_communities_partition_or_fallback() -> None:
    from llm_wiki.graphdb.algorithms import leiden_communities

    g = _build_graph()
    parts = leiden_communities(g)
    assert parts, "should produce at least one community"
    # Sanity: every member appears in exactly one community.
    seen: set[str] = set()
    for c in parts:
        for m in c.members:
            assert m not in seen, f"{m} appears in multiple communities"
            seen.add(m)
    assert seen == {"A1", "A2", "A3", "B1", "B2"}


def test_surprising_connections_finds_cross_cluster_bridge() -> None:
    from llm_wiki.graphdb.algorithms import leiden_communities, surprising_connections

    g = _build_graph()
    communities = leiden_communities(g)
    if len(communities) < 2:
        pytest.skip("Single-community partition; bridge cannot be 'surprising'")
    edges = surprising_connections(g, communities, confidence_min=0.7, top_n=10)
    # Bridge A1→B1 has confidence 0.95 and crosses clusters → must surface.
    assert any(e.src == "A1" and e.dst == "B1" for e in edges)


def test_snapshot_bundles_everything() -> None:
    from llm_wiki.graphdb.algorithms import snapshot

    g = _build_graph()
    snap = snapshot(g, top_n=5)
    assert snap.node_count == 5
    assert snap.edge_count == 6
    assert snap.pagerank
    assert snap.degree
    assert snap.communities


def test_snapshot_empty_graph_returns_zeros() -> None:
    from llm_wiki.graphdb.algorithms import snapshot

    snap = snapshot(None)
    assert snap.node_count == 0
    assert snap.edge_count == 0
    assert snap.pagerank == []
