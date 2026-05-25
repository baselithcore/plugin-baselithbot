"""Knowledge-graph store unit tests.

Uses a fake :class:`GraphDb` that records Cypher invocations instead of
talking to FalkorDB — the store layer must be testable without Docker.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from llm_wiki.graphdb.store import (
    TIER_AMBIGUOUS,
    TIER_EXTRACTED,
    TIER_INFERRED,
    KnowledgeGraphStore,
    canonical_entity_id,
    confidence_to_tier,
)


class FakeGraphDb:
    """Records `query()` invocations; returns canned results for reads."""

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._canned: dict[str, list[Any]] = {}

    def is_enabled(self) -> bool:
        return self.enabled

    def create_indexes(self) -> None:
        self.calls.append(("__indexes__", {}))

    def query(self, cypher: str, params: Mapping[str, Any] | None = None) -> list[Any]:
        normalized = " ".join(cypher.split())
        self.calls.append((normalized, dict(params or {})))
        # Most-recent canned response wins; default empty.
        for needle, resp in self._canned.items():
            if needle in normalized:
                return resp
        return []

    def stats(self) -> dict[str, int]:
        return {"nodes": 0, "edges": 0}

    def stub(self, cypher_needle: str, response: list[Any]) -> None:
        self._canned[cypher_needle] = response


def test_confidence_tiers() -> None:
    assert confidence_to_tier(0.99) == TIER_EXTRACTED
    assert confidence_to_tier(0.85) == TIER_EXTRACTED
    assert confidence_to_tier(0.84) == TIER_INFERRED
    assert confidence_to_tier(0.5) == TIER_INFERRED
    assert confidence_to_tier(0.49) == TIER_AMBIGUOUS
    assert confidence_to_tier(0.0) == TIER_AMBIGUOUS


def test_canonical_entity_id_collapses_surface_forms() -> None:
    a = canonical_entity_id("Unipol Assicurazioni", "entity")
    b = canonical_entity_id("UNIPOL ASSICURAZIONI ", "entity")
    c = canonical_entity_id("unipol-assicurazioni", "entity")
    assert a == b == c == "entity:unipol-assicurazioni"


def test_canonical_entity_id_kind_prefix() -> None:
    eid = canonical_entity_id("RCT", "concept")
    assert eid == "concept:rct"


def test_upsert_entity_writes_merge_cypher() -> None:
    fake = FakeGraphDb()
    store = KnowledgeGraphStore(graph=fake)  # type: ignore[arg-type]
    eid = store.upsert_entity("Generali Italia", "entity", aliases=["Generali"])
    assert eid == "entity:generali-italia"
    # Find the MERGE call.
    merge_calls = [c for c in fake.calls if "MERGE (e:Entity" in c[0]]
    assert len(merge_calls) == 1
    _, params = merge_calls[0]
    assert params["id"] == "entity:generali-italia"
    assert params["name"] == "Generali Italia"
    assert "Generali" in params["aliases"]


def test_link_mention_records_tier_from_confidence() -> None:
    fake = FakeGraphDb()
    store = KnowledgeGraphStore(graph=fake)  # type: ignore[arg-type]
    store.link_mention("polizze/foo", "entity:bar", confidence=0.91, canonical=False)
    mention_calls = [c for c in fake.calls if "MENTIONS" in c[0]]
    assert len(mention_calls) == 1
    _, params = mention_calls[0]
    assert params["tier"] == TIER_EXTRACTED
    assert pytest.approx(params["conf"]) == 0.91


def test_link_mention_canonical_writes_defined_in() -> None:
    fake = FakeGraphDb()
    store = KnowledgeGraphStore(graph=fake)  # type: ignore[arg-type]
    store.link_mention("concepts/rct", "concept:rct", confidence=0.95, canonical=True)
    assert any("DEFINED_IN" in c[0] for c in fake.calls)


def test_upsert_relation_truncates_evidence() -> None:
    fake = FakeGraphDb()
    store = KnowledgeGraphStore(graph=fake)  # type: ignore[arg-type]
    long_evidence = "x" * 500
    store.upsert_relation(
        "entity:a",
        "entity:b",
        "COVERS",
        confidence=0.7,
        evidence=long_evidence,
        page_id="polizze/foo",
    )
    rel_calls = [c for c in fake.calls if "MERGE (a)-[r:R" in c[0]]
    assert len(rel_calls) == 1
    _, params = rel_calls[0]
    assert len(params["ev"]) == 280
    assert params["tier"] == TIER_INFERRED
    assert params["page"] == "polizze/foo"


def test_disabled_store_is_noop() -> None:
    fake = FakeGraphDb(enabled=False)
    store = KnowledgeGraphStore(graph=fake)  # type: ignore[arg-type]
    assert store.enabled is False
    # No calls on disabled store.
    store.upsert_entity("X", "concept")
    store.link_mention("p", "e", confidence=0.9)
    store.upsert_relation("a", "b", "RELATES_TO", confidence=0.9)
    assert fake.calls == []


def test_neighbors_clamps_hops_and_filters_confidence() -> None:
    fake = FakeGraphDb()
    fake.stub(
        "(a:Entity {id: $id})-[r:R*1..3]-(b:Entity)",
        [["e.id", "e.name", "e.kind", "e.aliases"], [], []],
    )
    store = KnowledgeGraphStore(graph=fake)  # type: ignore[arg-type]
    store.neighbors("entity:foo", hops=99, confidence_min=0.6)
    # Find the variable-length match: hops clamped to 3.
    traversal = [c for c in fake.calls if "r:R*1..3" in c[0]]
    assert traversal, "hops should be clamped to 3"
    _, params = traversal[0]
    assert params["conf"] == 0.6


def test_pages_for_entities_empty_input_short_circuits() -> None:
    fake = FakeGraphDb()
    store = KnowledgeGraphStore(graph=fake)  # type: ignore[arg-type]
    out = store.pages_for_entities([])
    assert out == []
    # No Cypher should be emitted for empty input.
    assert all("Page" not in c[0] for c in fake.calls)


def test_delete_page_extractions_emits_three_deletes() -> None:
    fake = FakeGraphDb()
    store = KnowledgeGraphStore(graph=fake)  # type: ignore[arg-type]
    store.delete_page_extractions("polizze/foo")
    delete_calls = [c for c in fake.calls if "DELETE" in c[0]]
    # MENTIONS, DEFINED_IN, R attributed to page → 3 wipes.
    assert len(delete_calls) == 3
