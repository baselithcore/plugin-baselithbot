"""Report (GRAPH_REPORT.md / graph.json) + export (GraphML / Cypher /
Obsidian) generators tests.

NetworkX is the only hard dep; igraph/leidenalg are optional and the
algorithm layer falls back gracefully. These tests build small in-memory
graphs and validate the artifact format and contents.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

networkx = pytest.importorskip("networkx")


def _graph() -> object:
    g = networkx.DiGraph()
    g.add_node("entity:foo", name="Foo", kind="entity")
    g.add_node("concept:bar", name="Bar", kind="concept")
    g.add_node("source:baz", name="Baz", kind="source")
    g.add_edge("entity:foo", "concept:bar", kind="RELATES_TO", confidence=0.9)
    g.add_edge("concept:bar", "source:baz", kind="DERIVES_FROM", confidence=0.85)
    g.add_edge("entity:foo", "source:baz", kind="ISSUED_BY", confidence=0.95)
    return g


# --- report ---------------------------------------------------------------


def test_report_writes_two_artifacts(tmp_path: Path) -> None:
    from llm_wiki.graphdb.report import generate

    g = _graph()
    paths = generate(g, output_dir=tmp_path)
    assert paths.markdown.is_file()
    assert paths.json.is_file()
    md = paths.markdown.read_text(encoding="utf-8")
    assert "Knowledge Graph Report" in md
    assert "Foo" in md  # entity surfaced
    body = json.loads(paths.json.read_text(encoding="utf-8"))
    assert body["stats"]["node_count"] == 3
    assert body["stats"]["edge_count"] == 3
    # Nodes carry computed scores.
    foo = next(n for n in body["nodes"] if n["id"] == "entity:foo")
    assert "pagerank" in foo
    assert "community" in foo


def test_report_handles_empty_graph(tmp_path: Path) -> None:
    from llm_wiki.graphdb.report import generate

    paths = generate(None, output_dir=tmp_path)
    assert paths.markdown.is_file()
    md = paths.markdown.read_text(encoding="utf-8")
    assert "**Entities**: 0" in md


# --- exports --------------------------------------------------------------


def test_graphml_export(tmp_path: Path) -> None:
    from llm_wiki.graphdb.export import to_graphml

    g = _graph()
    out = tmp_path / "graph.graphml"
    result = to_graphml(g, out)
    assert result == out
    content = out.read_text(encoding="utf-8")
    assert "graphml" in content.lower()
    assert "entity:foo" in content


def test_graphml_empty_graph_returns_none(tmp_path: Path) -> None:
    from llm_wiki.graphdb.export import to_graphml

    empty = networkx.DiGraph()
    assert to_graphml(empty, tmp_path / "graph.graphml") is None


def test_cypher_export_format(tmp_path: Path) -> None:
    from llm_wiki.graphdb.export import to_cypher

    g = _graph()
    out = tmp_path / "graph.cypher"
    result = to_cypher(g, out)
    assert result == out
    content = out.read_text(encoding="utf-8")
    # Header + index.
    assert "CREATE INDEX entity_id" in content
    # Idempotent MERGE for nodes.
    assert "MERGE (:Entity {id: 'entity:foo'" in content
    # MERGE+SET for relations (carries confidence).
    assert "MERGE (a)-[r:R" in content
    assert "SET r.confidence" in content
    # Cypher escaping preserved.
    assert "\\'" not in content  # no name needed quoting in this fixture


def test_cypher_escapes_quotes_in_names(tmp_path: Path) -> None:
    from llm_wiki.graphdb.export import to_cypher

    g = networkx.DiGraph()
    g.add_node("entity:foo", name="O'Brien & Co.", kind="entity")
    out = tmp_path / "graph.cypher"
    to_cypher(g, out)
    content = out.read_text(encoding="utf-8")
    # Single quote escaped to \'.
    assert "O\\'Brien" in content


def test_obsidian_vault_writes_pages_and_communities(tmp_path: Path) -> None:
    from llm_wiki.graphdb.export import to_obsidian_vault

    g = _graph()
    written = to_obsidian_vault(g, tmp_path)
    # 3 entity pages + at least 1 community page.
    assert len(written) >= 4
    entities = list((tmp_path / "entities").glob("*.md"))
    communities = list((tmp_path / "communities").glob("*.md"))
    assert len(entities) == 3
    assert len(communities) >= 1
    # An entity page has frontmatter + wikilinks.
    foo_page = next(p for p in entities if "foo" in p.name)
    body = foo_page.read_text(encoding="utf-8")
    assert body.startswith("---")
    assert "pagerank:" in body
    # Outgoing relations rendered as wikilinks.
    assert "[[" in body


def test_obsidian_empty_graph_returns_empty_list(tmp_path: Path) -> None:
    from llm_wiki.graphdb.export import to_obsidian_vault

    empty = networkx.DiGraph()
    assert to_obsidian_vault(empty, tmp_path) == []
