"""Entity/relation extraction unit tests.

Mocks :func:`generate_structured` so the test never touches Ollama/OpenAI.
Asserts the post-LLM normalization layer: vocabulary coercion, phantom
relation filtering, idempotent persistence.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from llm_wiki.domain.pack import (
    DomainPack,
    GraphEntityType,
    GraphRelationType,
    GraphSpec,
    PageType,
    UILabels,
)


def _make_pack(spec: GraphSpec) -> DomainPack:
    return DomainPack(
        name="testpack",
        label="Test",
        page_types=[
            PageType(id="concept", label="Concetto", folder="concepts"),
            PageType(id="entity", label="Entità", folder="entities"),
        ],
        graph=spec,
        ui=UILabels(app_name="Test"),
    )


@pytest.fixture
def insurance_spec() -> GraphSpec:
    return GraphSpec(
        entity_types=[
            GraphEntityType(id="concept", label="Concetto"),
            GraphEntityType(id="entity", label="Entità"),
        ],
        relation_types=[
            GraphRelationType(id="COVERS", label="copre"),
            GraphRelationType(id="EXCLUDES", label="esclude"),
            GraphRelationType(id="RELATES_TO", label="correlato"),
        ],
        extraction_hints="Identifica garanzie come concept e compagnie come entity.",
    )


class _FakeStore:
    """Captures upserts so we can assert what would be persisted."""

    def __init__(self) -> None:
        self.enabled = True
        self.entities: list[tuple[str, str, list[str]]] = []
        self.mentions: list[tuple[str, str, float, bool]] = []
        self.relations: list[tuple[str, str, str, float, str, str | None]] = []
        self.deletes: list[str] = []

    def ensure_indexes(self) -> None:  # pragma: no cover — orchestrator path
        pass

    def upsert_entity(self, name: str, kind: str, *, aliases: Any = None) -> str:
        from llm_wiki.graphdb.store import canonical_entity_id

        eid = canonical_entity_id(name, kind)
        self.entities.append((name, kind, list(aliases or [])))
        return eid

    def link_mention(
        self,
        page_id: str,
        entity_id: str,
        *,
        confidence: float,
        canonical: bool = False,
    ) -> None:
        self.mentions.append((page_id, entity_id, confidence, canonical))

    def upsert_relation(
        self,
        src_id: str,
        dst_id: str,
        kind: str,
        *,
        confidence: float,
        evidence: str = "",
        page_id: str | None = None,
    ) -> None:
        self.relations.append((src_id, dst_id, kind, confidence, evidence, page_id))

    def delete_page_extractions(self, page_id: str) -> None:
        self.deletes.append(page_id)


@pytest.fixture
def patch_llm(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    """Replace ``generate_structured`` with a controlled fake.

    The fake reads the prepared payload from ``state['payload']`` and
    returns it as an :class:`ExtractionPayload`. Tests mutate the dict
    before invoking the extractor.
    """
    from llm_wiki.graphdb import extraction as ext

    state: dict[str, Any] = {"payload": None, "calls": 0}

    def _fake(schema: Any, **_kw: Any) -> Any:
        state["calls"] += 1
        payload = state["payload"]
        if payload is None:
            return ext.ExtractionPayload()
        if isinstance(payload, schema):
            return payload
        return schema.model_validate(payload)

    monkeypatch.setattr("llm_wiki.ingest_raw.llm_client.generate_structured", _fake)
    monkeypatch.setenv("GRAPH_EXTRACT_ENABLED", "true")
    monkeypatch.setattr("llm_wiki.graphdb.extraction.GRAPH_EXTRACT_ENABLED", True)
    yield state


def test_extraction_disabled_short_circuits(insurance_spec: GraphSpec) -> None:
    from llm_wiki.graphdb import extraction as ext

    pack = _make_pack(insurance_spec)
    store = _FakeStore()
    # GRAPH_EXTRACT_ENABLED is False by default in the module.
    out = ext.extract_from_page(
        page_id="p",
        page_title="t",
        page_body="body",
        page_type="concept",
        pack=pack,
        registry=None,
        store=store,  # type: ignore[arg-type]
    )
    assert out.entities == []
    assert store.entities == []


def test_persistence_pipeline(
    insurance_spec: GraphSpec, patch_llm: dict[str, Any]
) -> None:
    from llm_wiki.graphdb import extraction as ext

    pack = _make_pack(insurance_spec)
    store = _FakeStore()
    patch_llm["payload"] = ext.ExtractionPayload(
        entities=[
            ext.ExtractedEntity(name="RCT", kind="concept", confidence=0.95),
            ext.ExtractedEntity(name="Unipol", kind="entity", confidence=0.9),
        ],
        relations=[
            ext.ExtractedRelation(
                src="RCT",
                dst="Unipol",
                kind="RELATES_TO",
                confidence=0.8,
                evidence="RCT è offerta da Unipol",
            )
        ],
    )

    out = ext.extract_from_page(
        page_id="concepts/rct",
        page_title="RCT",
        page_body="Pagina su RCT offerta da Unipol.",
        page_type="concept",
        pack=pack,
        registry=None,
        store=store,  # type: ignore[arg-type]
    )

    assert len(out.entities) == 2
    assert len(out.relations) == 1
    # Persistence: 1 delete (wipe prior), 2 entities, 2 mentions, 1 relation.
    assert store.deletes == ["concepts/rct"]
    assert {e[0] for e in store.entities} == {"RCT", "Unipol"}
    # Canonical=True because page_type "concept" is a definition page.
    assert all(m[3] is True for m in store.mentions)
    assert len(store.relations) == 1
    assert store.relations[0][2] == "RELATES_TO"


def test_invalid_kind_is_dropped(
    insurance_spec: GraphSpec, patch_llm: dict[str, Any]
) -> None:
    """LLM hallucinates an entity kind not in the spec → coerced out."""
    from llm_wiki.graphdb import extraction as ext

    pack = _make_pack(insurance_spec)
    store = _FakeStore()
    patch_llm["payload"] = ext.ExtractionPayload(
        entities=[
            ext.ExtractedEntity(name="RCT", kind="concept", confidence=0.9),
            ext.ExtractedEntity(name="Hallucinated", kind="ghost", confidence=0.9),
        ],
        relations=[],
    )

    out = ext.extract_from_page(
        page_id="p",
        page_title="t",
        page_body="b",
        page_type="concept",
        pack=pack,
        registry=None,
        store=store,  # type: ignore[arg-type]
    )
    names = {e.name for e in out.entities}
    assert names == {"RCT"}
    assert all(e[0] == "RCT" for e in store.entities)


def test_phantom_relation_is_dropped(
    insurance_spec: GraphSpec, patch_llm: dict[str, Any]
) -> None:
    """Relation references an entity not in the entities[] list."""
    from llm_wiki.graphdb import extraction as ext

    pack = _make_pack(insurance_spec)
    store = _FakeStore()
    patch_llm["payload"] = ext.ExtractionPayload(
        entities=[
            ext.ExtractedEntity(name="RCT", kind="concept", confidence=0.9),
        ],
        relations=[
            ext.ExtractedRelation(
                src="RCT", dst="GhostEntity", kind="COVERS", confidence=0.9
            ),
        ],
    )

    out = ext.extract_from_page(
        page_id="p",
        page_title="t",
        page_body="b",
        page_type="concept",
        pack=pack,
        registry=None,
        store=store,  # type: ignore[arg-type]
    )
    assert out.relations == []
    assert store.relations == []


def test_relation_kind_normalized_to_upper(
    insurance_spec: GraphSpec, patch_llm: dict[str, Any]
) -> None:
    from llm_wiki.graphdb import extraction as ext

    pack = _make_pack(insurance_spec)
    store = _FakeStore()
    patch_llm["payload"] = ext.ExtractionPayload(
        entities=[
            ext.ExtractedEntity(name="A", kind="concept", confidence=0.9),
            ext.ExtractedEntity(name="B", kind="concept", confidence=0.9),
        ],
        relations=[
            ext.ExtractedRelation(src="A", dst="B", kind="covers", confidence=0.7),
        ],
    )
    out = ext.extract_from_page(
        page_id="p",
        page_title="t",
        page_body="b",
        page_type="concept",
        pack=pack,
        registry=None,
        store=store,  # type: ignore[arg-type]
    )
    assert out.relations[0].kind == "COVERS"


def test_non_canonical_page_no_defined_in(
    insurance_spec: GraphSpec, patch_llm: dict[str, Any]
) -> None:
    """page_type=source is NOT a definition page → canonical=False."""
    from llm_wiki.graphdb import extraction as ext

    pack = _make_pack(insurance_spec)
    store = _FakeStore()
    patch_llm["payload"] = ext.ExtractionPayload(
        entities=[ext.ExtractedEntity(name="RCT", kind="concept", confidence=0.9)],
        relations=[],
    )
    ext.extract_from_page(
        page_id="sources/foo",
        page_title="Foo",
        page_body="b",
        page_type="source",
        pack=pack,
        registry=None,
        store=store,  # type: ignore[arg-type]
    )
    assert all(m[3] is False for m in store.mentions)
