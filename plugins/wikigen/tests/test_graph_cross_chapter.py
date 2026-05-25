"""Cross-chapter retrieval via Knowledge Graph (graphify-aligned).

Verifica end-to-end:
- comparative archetype riconosciuto dal classifier;
- ``spot_entities_in_query`` ritorna canonical ids (con KG store mocked);
- ``expand_with_entity_graph`` accetta ``query_entities`` e propaga il
  segnale path-comparative + overlap boost ai hit emessi;
- chunk_tagging matcher fa word-boundary case-insensitive;
- auto-enable attivato solo per pack con GraphSpec custom (no default).

I test non richiedono FalkorDB attivo: mockano lo store + Qdrant client.
"""

from __future__ import annotations

import pytest

from llm_wiki.graphdb.chunk_tagging import _make_matcher
from llm_wiki.vectorstore.expansions import expand_with_entity_graph
from llm_wiki.vectorstore.query_classifier import detect_archetype

# --- archetype: comparative ----------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "Compara X e Y",
        "Differenza tra Kubernetes e Docker",
        "Kubernetes vs Docker",
        "qual è la relazione tra A e B",
        "Confronta i pattern RAG e GraphRAG",
        "A versus B",
        "What's the difference between X and Y",
    ],
)
def test_comparative_archetype_detected(query: str) -> None:
    archetype, confidence, _ = detect_archetype(query)
    assert archetype == "comparative"
    assert confidence == "strict"


def test_comparative_priority_over_definitional() -> None:
    # "cos'è X" sarebbe definitional, ma "differenza tra X e Y" deve vincere.
    archetype, _, _ = detect_archetype("Differenza tra cos'è X e cos'è Y")
    assert archetype == "comparative"


def test_non_comparative_unaffected() -> None:
    arch_def, _, _ = detect_archetype("cos'è il RAG pattern")
    assert arch_def == "definitional"
    arch_proc, _, _ = detect_archetype("come configuro Kubernetes")
    assert arch_proc == "procedural"


# --- chunk_tagging matcher ----------------------------------------------


def test_make_matcher_word_boundary() -> None:
    m = _make_matcher(["Unipol Assicurazioni", "Allianz"])
    assert m is not None
    # Match standalone
    assert m.search("Il contratto Unipol Assicurazioni offre…")
    # Match alias
    assert m.search("Confronto con Allianz.")
    # Word boundary: "unipola" NON deve matchare "unipol"
    assert not m.search("La parola unipolare è diversa.")
    # Case-insensitive
    assert m.search("UNIPOL ASSICURAZIONI")


def test_make_matcher_prefers_longer_form() -> None:
    """Surface ordinate per lunghezza decrescente → 'Unipol Assicurazioni'
    matcha prima di 'Unipol' quando entrambi sono nel pattern."""
    m = _make_matcher(["Unipol", "Unipol Assicurazioni"])
    assert m is not None
    text = "Il gruppo Unipol Assicurazioni opera in Italia."
    matches = m.findall(text)
    # Solo UN match (il più lungo), non due overlap.
    assert len(matches) == 1
    assert matches[0].lower() == "unipol assicurazioni"


def test_make_matcher_empty_input() -> None:
    assert _make_matcher([]) is None
    assert _make_matcher(["", "   "]) is None


# --- expand_with_entity_graph + query_entities boost ---------------------


class _FakeStore:
    """Mock minimale del KG store per test deterministici."""

    enabled = True

    def __init__(
        self,
        *,
        seed_entities: list[str],
        neighbors_map: dict[str, list],
        pages: list[str],
        path_returns: dict[tuple[str, str], list[str]] | None = None,
        entity_meta: dict[str, str] | None = None,
    ) -> None:
        self._seed_entities = seed_entities
        self._neighbors = neighbors_map
        self._pages = pages
        self._paths = path_returns or {}
        self._meta = entity_meta or {}

    # API consumata dal codice prod
    @property
    def _g(self):  # noqa: ANN201
        store_self = self

        class _G:
            def query(self, _cypher: str, _params: dict):  # noqa: ANN201
                # Step 1 cypher seed_entity_ids — ritorna le seed entities.
                return [None, [[eid] for eid in store_self._seed_entities], None]

        return _G()

    @staticmethod
    def _rows(result):  # noqa: ANN001, ANN205
        try:
            if len(result) > 1 and isinstance(result[1], list):
                return result[1]
        except Exception:
            pass
        return []

    def neighbors(self, eid, *, hops, confidence_min, limit):  # noqa: ANN001, ANN201, ARG002
        from llm_wiki.graphdb.store import EntityRecord

        return [
            EntityRecord(id=n, name=n, kind="entity", aliases=[])
            for n in self._neighbors.get(eid, [])
        ]

    def pages_for_entities(self, _ids, *, confidence_min, limit):  # noqa: ANN001, ANN201, ARG002
        return self._pages

    def shortest_path(self, src, dst, *, max_hops):  # noqa: ANN001, ANN201, ARG002
        return self._paths.get((src, dst), [])

    def get_entity(self, eid):  # noqa: ANN001, ANN201
        from llm_wiki.graphdb.store import EntityRecord

        name = self._meta.get(eid, eid)
        return EntityRecord(id=eid, name=name, kind="entity", aliases=[])


class _FakeQdrantPoint:
    def __init__(self, pid: str, payload: dict) -> None:
        self.id = pid
        self.payload = payload


class _FakeQdrant:
    """Mock Qdrant: registra scroll calls, ritorna chunk taggati."""

    def __init__(self, response_by_doc: dict[str, list[_FakeQdrantPoint]]) -> None:
        self._resp = response_by_doc
        self.calls: list[tuple[str, dict]] = []

    def scroll(self, *, collection_name, scroll_filter, limit, with_payload):  # noqa: ANN201, ARG002
        # Estrai document_id dal filter (per match con _resp).
        doc_id = ""
        try:
            for cond in scroll_filter.must or []:
                if cond.key == "document_id":
                    doc_id = cond.match.value
                    break
        except Exception:
            pass
        self.calls.append((doc_id, {"filter": scroll_filter, "limit": limit}))
        return self._resp.get(doc_id, []), None


def test_entity_graph_expansion_overlap_boost(monkeypatch) -> None:
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_ENABLED", True, raising=False)
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_HOPS", 2, raising=False)
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_MAX_EXTRA_PAGES", 5, raising=False)
    monkeypatch.setattr("llm_wiki.config.GRAPH_CONFIDENCE_MIN", 0.0, raising=False)
    fake_store = _FakeStore(
        seed_entities=["e:a", "e:b"],
        neighbors_map={"e:a": ["e:c"], "e:b": []},
        pages=["docs/extra"],
        entity_meta={"e:a": "Alpha", "e:b": "Beta", "e:c": "Gamma"},
    )
    fake_q = _FakeQdrant(
        response_by_doc={
            "docs/extra": [
                _FakeQdrantPoint(
                    "pt-extra-1",
                    {
                        "document_id": "docs/extra",
                        "raw_text": "Alpha e Beta sono correlati.",
                        "entities_mentioned": ["e:a", "e:b"],
                        "entity_tiers": {"e:a": "EXTRACTED", "e:b": "EXTRACTED"},
                    },
                )
            ]
        }
    )
    monkeypatch.setattr("llm_wiki.graphdb.store.get_kg_store", lambda: fake_store)
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: fake_q)

    seed_hits = [{"payload": {"document_id": "docs/seed-1"}, "score": 0.9}]
    out = expand_with_entity_graph(seed_hits)
    # Hit originale + 1 extra
    assert len(out) == 2
    extra = out[1]
    assert extra["graph_expanded"] is True
    # Overlap = 2 (e:a, e:b) → boost 0.05 * 2 = 0.10
    assert extra["score"] >= 0.05
    assert extra["via_graph_overlap"] == 2
    assert extra.get("via_graph_entity") in {"e:a", "e:b"}
    assert extra.get("via_graph_entity_name") in {"Alpha", "Beta"}
    assert extra.get("via_graph_tier") == "EXTRACTED"


def test_entity_graph_comparative_path_boost(monkeypatch) -> None:
    """Quando ``query_entities`` contiene ≥ 2 ids E lo shortest_path
    ritorna un cammino, i chunk lungo il path sono boostati 0.10 e
    annotati ``via_graph_comparative_path=True``."""
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_ENABLED", True, raising=False)
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_HOPS", 2, raising=False)
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_MAX_EXTRA_PAGES", 5, raising=False)
    monkeypatch.setattr("llm_wiki.config.GRAPH_CONFIDENCE_MIN", 0.0, raising=False)
    fake_store = _FakeStore(
        seed_entities=["e:a"],
        neighbors_map={"e:a": []},
        pages=["docs/bridge"],
        path_returns={("e:a", "e:b"): ["e:a", "e:bridge", "e:b"]},
        entity_meta={"e:bridge": "BridgeConcept"},
    )
    fake_q = _FakeQdrant(
        response_by_doc={
            "docs/bridge": [
                _FakeQdrantPoint(
                    "pt-bridge",
                    {
                        "document_id": "docs/bridge",
                        "raw_text": "BridgeConcept collega Alpha a Beta.",
                        "entities_mentioned": ["e:bridge"],
                        "entity_tiers": {"e:bridge": "INFERRED"},
                    },
                )
            ]
        }
    )
    monkeypatch.setattr("llm_wiki.graphdb.store.get_kg_store", lambda: fake_store)
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: fake_q)

    seed_hits = [{"payload": {"document_id": "docs/seed-1"}, "score": 0.9}]
    out = expand_with_entity_graph(seed_hits, query_entities=["e:a", "e:b"])
    bridge = next(h for h in out if h.get("graph_expanded"))
    assert bridge["via_graph_comparative_path"] is True
    assert bridge["via_graph_entity"] == "e:bridge"
    # Boost path = 0.10 (no overlap boost: solo 1 entità nel chunk).
    assert bridge["score"] >= 0.10
    assert bridge.get("via_graph_tier") == "INFERRED"


def test_entity_graph_falls_back_to_first_chunk_for_pre_tagging_docs(
    monkeypatch,
) -> None:
    """Doc senza ``entities_mentioned`` (pre-Wave-A): la scroll prima
    tenta il filtro, ottiene 0 risultati, poi fa il fallback al primo
    chunk del doc. L'hit emette ``graph_expanded=True`` ma niente
    overlap/path attribution."""
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_ENABLED", True, raising=False)
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_HOPS", 2, raising=False)
    monkeypatch.setattr("llm_wiki.config.GRAPH_RAG_MAX_EXTRA_PAGES", 5, raising=False)
    monkeypatch.setattr("llm_wiki.config.GRAPH_CONFIDENCE_MIN", 0.0, raising=False)
    fake_store = _FakeStore(
        seed_entities=["e:a"],
        neighbors_map={"e:a": ["e:b"]},
        pages=["docs/legacy"],
    )

    class _FakeQ2:
        calls: list = []

        def scroll(self, *, collection_name, scroll_filter, limit, with_payload):  # noqa: ANN201, ARG002
            self.calls.append(
                {"limit": limit, "has_should": bool(scroll_filter.should)}
            )
            # Primo tentativo (filtro entities_mentioned) → vuoto.
            if scroll_filter.should:
                return [], None
            # Fallback (solo document_id) → primo chunk.
            return [
                _FakeQdrantPoint(
                    "pt-legacy",
                    {"document_id": "docs/legacy", "raw_text": "contenuto legacy"},
                )
            ], None

    fake_q = _FakeQ2()
    monkeypatch.setattr("llm_wiki.graphdb.store.get_kg_store", lambda: fake_store)
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: fake_q)

    seed_hits = [{"payload": {"document_id": "docs/seed-1"}, "score": 0.9}]
    out = expand_with_entity_graph(seed_hits)
    extras = [h for h in out if h.get("graph_expanded")]
    assert len(extras) == 1
    # Niente overlap né path: payload senza entities_mentioned.
    assert extras[0]["via_graph_overlap"] == 0
    assert extras[0].get("via_graph_comparative_path") is not True
    # Scroll calls: 1 entity-aware (skipped) + 1 fallback.
    assert any(c["has_should"] for c in fake_q.calls)
    assert any(not c["has_should"] for c in fake_q.calls)


# --- Wave D: auto-enable per pack con GraphSpec custom ------------------


def test_auto_enable_skipped_for_default_graph_spec(monkeypatch) -> None:
    """Pack con GraphSpec default (concept/entity/source + RELATES_TO…)
    NON deve attivare i flag. Override esplicito sempre rispettato."""
    from llm_wiki import config as _config
    from llm_wiki.domain.pack import _default_graph_spec
    from llm_wiki.domain.registry import (
        _auto_enable_graph_flags,
        _has_custom_graph_spec,
    )

    monkeypatch.setattr(_config, "GRAPH_EXTRACT_ENABLED", False, raising=False)
    monkeypatch.setattr(_config, "GRAPH_RAG_ENABLED", False, raising=False)
    monkeypatch.setattr(
        _config, "GRAPH_CHUNK_ENTITY_TAGGING_ENABLED", False, raising=False
    )
    monkeypatch.delenv("GRAPH_EXTRACT_ENABLED", raising=False)
    monkeypatch.delenv("GRAPH_RAG_ENABLED", raising=False)
    monkeypatch.delenv("GRAPH_CHUNK_ENTITY_TAGGING_ENABLED", raising=False)

    class _FakePack:
        name = "demo"
        graph = _default_graph_spec()

    assert _has_custom_graph_spec(_FakePack()) is False  # type: ignore[arg-type]
    _auto_enable_graph_flags(_FakePack())  # type: ignore[arg-type]
    assert _config.GRAPH_EXTRACT_ENABLED is False
    assert _config.GRAPH_RAG_ENABLED is False
    assert _config.GRAPH_CHUNK_ENTITY_TAGGING_ENABLED is False


def test_auto_enable_fires_for_custom_graph_spec(monkeypatch) -> None:
    from llm_wiki import config as _config
    from llm_wiki.domain.pack import GraphEntityType, GraphRelationType, GraphSpec
    from llm_wiki.domain.registry import (
        _auto_enable_graph_flags,
        _has_custom_graph_spec,
    )

    monkeypatch.setattr(_config, "GRAPH_EXTRACT_ENABLED", False, raising=False)
    monkeypatch.setattr(_config, "GRAPH_RAG_ENABLED", False, raising=False)
    monkeypatch.setattr(
        _config, "GRAPH_CHUNK_ENTITY_TAGGING_ENABLED", False, raising=False
    )
    monkeypatch.delenv("GRAPH_EXTRACT_ENABLED", raising=False)
    monkeypatch.delenv("GRAPH_RAG_ENABLED", raising=False)
    monkeypatch.delenv("GRAPH_CHUNK_ENTITY_TAGGING_ENABLED", raising=False)

    class _FakePack:
        name = "tech"
        graph = GraphSpec(
            entity_types=[
                GraphEntityType(id="service", label="Servizio"),
                GraphEntityType(id="protocol", label="Protocollo"),
            ],
            relation_types=[GraphRelationType(id="USES", label="usa")],
            extraction_hints="",
        )

    assert _has_custom_graph_spec(_FakePack()) is True  # type: ignore[arg-type]
    _auto_enable_graph_flags(_FakePack())  # type: ignore[arg-type]
    assert _config.GRAPH_EXTRACT_ENABLED is True
    assert _config.GRAPH_RAG_ENABLED is True
    assert _config.GRAPH_CHUNK_ENTITY_TAGGING_ENABLED is True


def test_auto_enable_respects_explicit_env_override(monkeypatch) -> None:
    """Env explicit (anche se vuota/false) NON deve essere sovrascritta."""
    from llm_wiki import config as _config
    from llm_wiki.domain.pack import GraphEntityType, GraphSpec
    from llm_wiki.domain.registry import _auto_enable_graph_flags

    monkeypatch.setattr(_config, "GRAPH_EXTRACT_ENABLED", False, raising=False)
    monkeypatch.setenv("GRAPH_EXTRACT_ENABLED", "false")
    monkeypatch.delenv("GRAPH_RAG_ENABLED", raising=False)
    monkeypatch.setattr(_config, "GRAPH_RAG_ENABLED", False, raising=False)

    class _FakePack:
        name = "tech"
        graph = GraphSpec(
            entity_types=[GraphEntityType(id="custom", label="Custom")],
            relation_types=[],
            extraction_hints="",
        )

    _auto_enable_graph_flags(_FakePack())  # type: ignore[arg-type]
    # Override esplicito tenuto a False.
    assert _config.GRAPH_EXTRACT_ENABLED is False
    # No override → auto-enable.
    assert _config.GRAPH_RAG_ENABLED is True
