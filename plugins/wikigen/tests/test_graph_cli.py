"""CLI smoke tests for ``wiki-wl graph ...``.

Uses Typer's :class:`CliRunner`. Backing store + extraction are
monkey-patched so we never touch FalkorDB or the LLM. Asserts wiring +
exit codes, not pipeline depth (which is covered by extraction tests).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from llm_wiki.cli import app
from llm_wiki.graphdb.store import EntityRecord

runner = CliRunner()


class _EnabledStore:
    enabled = True

    def __init__(self) -> None:
        self._entities: dict[str, EntityRecord] = {
            "entity:foo": EntityRecord(id="entity:foo", name="Foo", kind="entity", aliases=[]),
            "concept:bar": EntityRecord(
                id="concept:bar", name="Bar", kind="concept", aliases=["barbar"]
            ),
        }

    def ensure_indexes(self) -> None: ...

    def to_networkx(self) -> Any:
        import networkx as nx  # type: ignore[import-not-found]

        g = nx.DiGraph()
        g.add_node("entity:foo", name="Foo", kind="entity")
        g.add_node("concept:bar", name="Bar", kind="concept")
        g.add_edge("entity:foo", "concept:bar", kind="RELATES_TO", confidence=0.9)
        return g

    def get_entity(self, entity_id: str) -> EntityRecord | None:
        return self._entities.get(entity_id)

    def search_entities(
        self,
        query: str,
        *,
        kind: str | None = None,
        limit: int = 25,
    ) -> list[EntityRecord]:
        needle = query.strip().lower()
        rows = [
            e
            for e in self._entities.values()
            if needle in e.name.lower() and (kind is None or e.kind == kind)
        ]
        return rows[:limit]

    def neighbors(
        self,
        entity_id: str,
        *,
        hops: int = 1,
        confidence_min: float | None = None,
        relation_kind: str | None = None,
        limit: int = 50,
    ) -> list[EntityRecord]:
        if entity_id == "entity:foo":
            return [self._entities["concept:bar"]]
        if entity_id == "concept:bar":
            return [self._entities["entity:foo"]]
        return []

    def shortest_path(
        self,
        src_id: str,
        dst_id: str,
        *,
        max_hops: int = 5,
    ) -> list[str]:
        if {src_id, dst_id} == {"entity:foo", "concept:bar"}:
            return [src_id, dst_id]
        return []

    def pages_for_entities(
        self,
        entity_ids: Any,
        *,
        confidence_min: float | None = None,
        limit: int = 25,
    ) -> list[str]:
        ids = list(entity_ids)
        if "entity:foo" in ids:
            return ["page:concepts/foo"]
        return []


def test_graph_rebuild_fails_when_extract_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("llm_wiki.config.GRAPH_EXTRACT_ENABLED", False)
    result = runner.invoke(app, ["graph", "rebuild"])
    assert result.exit_code != 0
    assert "GRAPH_EXTRACT_ENABLED" in result.output


def test_graph_rebuild_fails_when_store_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("llm_wiki.config.GRAPH_EXTRACT_ENABLED", True)
    monkeypatch.setattr(
        "llm_wiki.cli.graph_cmd._require_store",
        lambda _ctx: (_ for _ in ()).throw(SystemExit(1)),
    )
    result = runner.invoke(app, ["graph", "rebuild"])
    assert result.exit_code != 0


def test_graph_report_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("networkx")
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(app, ["graph", "report", "--output-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "GRAPH_REPORT.md").is_file()
    assert (tmp_path / "graph.json").is_file()


def test_graph_export_graphml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("networkx")
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(
        app,
        ["graph", "export", "--format", "graphml", "--output-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "graph.graphml").is_file()


def test_graph_export_cypher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("networkx")
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(
        app,
        ["graph", "export", "--format", "cypher", "--output-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "graph.cypher").is_file()


def test_graph_export_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("networkx")
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(
        app,
        ["graph", "export", "--format", "html", "--output-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    out = tmp_path / "graph.html"
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "cytoscape" in text
    assert "Foo" in text and "Bar" in text


def test_graph_export_unknown_format(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("networkx")
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(app, ["graph", "export", "--format", "doom"])
    assert result.exit_code != 0
    assert "unknown format" in result.output


def test_graph_query_returns_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(app, ["graph", "query", "Foo"])
    assert result.exit_code == 0, result.output
    assert "entity:foo" in result.output
    assert "Bar" in result.output  # neighbor preview


def test_graph_query_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(app, ["graph", "query", "nope-no-match"])
    assert result.exit_code == 0, result.output
    assert "no entities match" in result.output


def test_graph_path_found(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(app, ["graph", "path", "Foo", "Bar"])
    assert result.exit_code == 0, result.output
    assert "entity:foo" in result.output and "concept:bar" in result.output


def test_graph_path_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(app, ["graph", "path", "Ghost", "Bar"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_graph_explain_renders(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(app, ["graph", "explain", "Foo"])
    assert result.exit_code == 0, result.output
    assert "entity:foo" in result.output
    assert "page:concepts/foo" in result.output


def test_graph_explain_resolves_by_id(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _EnabledStore()
    monkeypatch.setattr("llm_wiki.cli.graph_cmd._require_store", lambda _ctx: store)
    result = runner.invoke(app, ["graph", "explain", "concept:bar"])
    assert result.exit_code == 0, result.output
    assert "concept:bar" in result.output
