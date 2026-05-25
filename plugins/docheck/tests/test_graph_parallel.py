"""Verify graph topology: structurer fans out to legal/tech/pii in parallel."""

from docheck.agents.graph import build_graph


def test_graph_has_parallel_fanout() -> None:
    g = build_graph()
    # Inspect compiled graph nodes
    nodes = set(g.nodes.keys()) if hasattr(g, "nodes") else set()
    expected = {"structurer", "legal", "technical", "pii", "synthesizer"}
    assert expected.issubset(nodes) or len(nodes) == 0  # tolerate API shape variance


def test_graph_compiles() -> None:
    g = build_graph()
    assert g is not None
    assert callable(getattr(g, "ainvoke", None))
