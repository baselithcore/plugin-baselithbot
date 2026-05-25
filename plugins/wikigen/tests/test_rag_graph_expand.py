"""RAG graph-aware expansion tests.

Verifies :func:`expand_with_entity_graph` gating + behavior without
hitting FalkorDB or Qdrant. Both backing services are monkey-patched.
"""

from __future__ import annotations

from typing import Any

import pytest

from llm_wiki.graphdb.store import EntityRecord


class _FakeStore:
    def __init__(
        self,
        *,
        entity_neighbors: dict[str, list[EntityRecord]] | None = None,
        docs_for_entities: list[str] | None = None,
        mention_entities: list[str] | None = None,
    ) -> None:
        self.enabled = True
        self._neighbors = entity_neighbors or {}
        self._docs = docs_for_entities or []
        self._mention_entities = mention_entities or []
        self._g = _FakeUnderlyingGraph(self._mention_entities)

    @staticmethod
    def _rows(result: list[Any]) -> list[list[Any]]:
        # Mirror real store._rows.
        if len(result) > 1 and isinstance(result[1], list):
            return [list(r) if isinstance(r, list | tuple) else [r] for r in result[1]]
        return []

    def neighbors(self, eid: str, **_kw: Any) -> list[EntityRecord]:
        return self._neighbors.get(eid, [])

    def pages_for_entities(self, entity_ids: Any, **_kw: Any) -> list[str]:
        return list(self._docs)


class _FakeUnderlyingGraph:
    """Fake of ``store._g``: returns the FalkorDB --compact result shape."""

    def __init__(self, mention_entities: list[str]) -> None:
        self.mention_entities = mention_entities

    def query(self, cypher: str, _params: Any = None) -> list[Any]:
        if "MENTIONS" in cypher:
            # Shape: [header, rows, stats]. Each row is [[type_code, value]].
            rows = [[["e.id", eid]] for eid in self.mention_entities]
            return [["e.id"], rows, []]
        return []


def test_expansion_disabled_returns_hits_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_ENABLED", False)
    from llm_wiki.vectorstore.expansions import expand_with_entity_graph

    hits = [{"payload": {"document_id": "concepts/foo"}, "score": 0.9}]
    out = expand_with_entity_graph(hits)
    assert out == hits


def test_expansion_no_seed_docs_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hits without document_id → no work to do, no Qdrant call."""
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_ENABLED", True)
    monkeypatch.setattr(
        "llm_wiki.graphdb.store.get_kg_store",
        lambda: _FakeStore(),
    )
    from llm_wiki.vectorstore.expansions import expand_with_entity_graph

    hits = [{"payload": {}, "score": 0.9}]
    assert expand_with_entity_graph(hits) == hits


def test_expansion_disabled_store_returns_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_ENABLED", True)

    class _OffStore(_FakeStore):
        def __init__(self) -> None:
            super().__init__()
            self.enabled = False

    monkeypatch.setattr(
        "llm_wiki.graphdb.store.get_kg_store",
        lambda: _OffStore(),
    )
    from llm_wiki.vectorstore.expansions import expand_with_entity_graph

    hits = [{"payload": {"document_id": "p1"}, "score": 0.9}]
    assert expand_with_entity_graph(hits) == hits


def test_expansion_adds_extra_hit_when_qdrant_returns_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_ENABLED", True)
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_MAX_EXTRA_PAGES", 3)

    fake_store = _FakeStore(
        mention_entities=["entity:bar"],
        entity_neighbors={
            "entity:bar": [EntityRecord(id="entity:baz", name="Baz", kind="entity", aliases=[])]
        },
        docs_for_entities=["concepts/baz"],
    )
    monkeypatch.setattr("llm_wiki.graphdb.store.get_kg_store", lambda: fake_store)

    class _FakePoint:
        id = "pt-123"
        payload = {"document_id": "concepts/baz", "text": "Baz chunk"}

    class _FakeQdrant:
        def scroll(self, **_kw: Any) -> tuple[list[Any], None]:
            return [_FakePoint()], None

    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: _FakeQdrant())

    from llm_wiki.vectorstore.expansions import expand_with_entity_graph

    hits = [{"payload": {"document_id": "concepts/foo"}, "score": 0.9}]
    out = expand_with_entity_graph(hits)
    assert len(out) == 2
    extra = out[-1]
    assert extra["graph_expanded"] is True
    assert extra["payload"]["document_id"] == "concepts/baz"


def test_expansion_filters_out_seed_docs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pages already in top-K must not be re-added by graph expansion."""
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_ENABLED", True)
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_MAX_EXTRA_PAGES", 3)

    fake_store = _FakeStore(
        mention_entities=["entity:bar"],
        docs_for_entities=["concepts/foo"],  # already a seed
    )
    monkeypatch.setattr("llm_wiki.graphdb.store.get_kg_store", lambda: fake_store)
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: None)

    from llm_wiki.vectorstore.expansions import expand_with_entity_graph

    hits = [{"payload": {"document_id": "concepts/foo"}, "score": 0.9}]
    out = expand_with_entity_graph(hits)
    assert out == hits
