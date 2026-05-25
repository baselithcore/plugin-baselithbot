"""Smoke tests for ``/api/graph/*`` endpoints.

Driven entirely against ``TestClient`` with a monkey-patched
:class:`KnowledgeGraphStore` so they pass without FalkorDB running.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from llm_wiki.graphdb.store import EntityRecord


class _FakeStore:
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self._entities: dict[str, EntityRecord] = {
            "entity:foo": EntityRecord(id="entity:foo", name="Foo", kind="entity", aliases=[]),
            "entity:bar": EntityRecord(
                id="entity:bar", name="Bar", kind="entity", aliases=["Barr"]
            ),
        }

    def stats(self) -> dict[str, int]:
        return {"nodes": 2, "edges": 1, "entities": 2, "mentions": 0, "relations": 1}

    def get_entity(self, eid: str) -> EntityRecord | None:
        return self._entities.get(eid)

    def search_entities(
        self, q: str, *, kind: str | None = None, limit: int = 25
    ) -> list[EntityRecord]:
        out = [e for e in self._entities.values() if q.lower() in e.name.lower()]
        if kind:
            out = [e for e in out if e.kind == kind]
        return out[:limit]

    def neighbors(
        self,
        entity_id: str,
        *,
        hops: int = 1,
        confidence_min: float = 0.5,
        relation_kind: str | None = None,
        limit: int = 50,
    ) -> list[EntityRecord]:
        if entity_id == "entity:foo":
            return [self._entities["entity:bar"]]
        return []

    def shortest_path(self, src: str, dst: str, *, max_hops: int = 5) -> list[str]:
        if src in self._entities and dst in self._entities:
            return [src, dst]
        return []

    def to_networkx(self) -> object | None:
        """Build a tiny NetworkX graph backed by the fake entities so the
        algorithm endpoints have something to chew on.
        """
        try:
            import networkx as nx  # type: ignore[import-not-found]
        except ImportError:
            return None
        g = nx.DiGraph()
        for eid, rec in self._entities.items():
            g.add_node(eid, name=rec.name, kind=rec.kind)
        g.add_edge("entity:foo", "entity:bar", kind="RELATES_TO", confidence=0.9)
        return g


@pytest.fixture(autouse=True)
def _disable_postgres_for_graph_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disabilita POSTGRES_ENABLED per la durata di ogni test del modulo.

    Il router gate ``_require_graph_read_or_setup_mode`` (mig 013) cade in
    setup-mode bypass quando Postgres è off. Senza questo, i test
    falliscono con 401 perché non c'è bearer token e il TestClient non
    setup-pa una sessione auth. Questo riflette l'intent originale di
    questi smoke test: validare il router contro un fake store, NON
    l'integrazione auth.
    """
    monkeypatch.setattr("llm_wiki.config.POSTGRES_ENABLED", False)
    monkeypatch.setattr("llm_wiki.api.routers.graph.config.POSTGRES_ENABLED", False)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    fake = _FakeStore()
    monkeypatch.setattr("llm_wiki.api.routers.graph.get_kg_store", lambda: fake)
    from llm_wiki.api.routers.graph import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_stats_enabled(client: TestClient) -> None:
    r = client.get("/api/graph/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["entities"] == 2


def test_stats_disabled_returns_zeros(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeStore(enabled=False)
    monkeypatch.setattr("llm_wiki.api.routers.graph.get_kg_store", lambda: fake)
    from llm_wiki.api.routers.graph import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        r = c.get("/api/graph/stats")
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    assert r.json()["entities"] == 0


def test_entity_found(client: TestClient) -> None:
    r = client.get("/api/graph/entity/entity:foo")
    assert r.status_code == 200
    assert r.json()["name"] == "Foo"


def test_entity_404(client: TestClient) -> None:
    r = client.get("/api/graph/entity/entity:missing")
    assert r.status_code == 404


def test_search_query(client: TestClient) -> None:
    r = client.get("/api/graph/search", params={"q": "foo"})
    assert r.status_code == 200
    assert r.json()["count"] == 1
    assert r.json()["results"][0]["id"] == "entity:foo"


def test_neighbors_with_hops_clamp(client: TestClient) -> None:
    r = client.get("/api/graph/neighbors/entity:foo", params={"hops": 99})
    assert r.status_code == 422  # ge/le validation rejects out-of-range hops


def test_neighbors_ok(client: TestClient) -> None:
    r = client.get("/api/graph/neighbors/entity:foo", params={"hops": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["results"][0]["id"] == "entity:bar"


def test_path_ok(client: TestClient) -> None:
    r = client.get(
        "/api/graph/path",
        params={"src": "entity:foo", "dst": "entity:bar"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert body["length"] == 1


def test_disabled_endpoint_503(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeStore(enabled=False)
    monkeypatch.setattr("llm_wiki.api.routers.graph.get_kg_store", lambda: fake)
    from llm_wiki.api.routers.graph import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        r = c.get("/api/graph/entity/whatever")
    assert r.status_code == 503


# --- PR2 algorithm endpoints ---------------------------------------------


def test_centrality_pagerank(client: TestClient) -> None:
    pytest.importorskip("networkx")
    r = client.get("/api/graph/centrality", params={"metric": "pagerank", "top_n": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["metric"] == "pagerank"
    assert body["count"] >= 1


def test_centrality_invalid_metric(client: TestClient) -> None:
    r = client.get("/api/graph/centrality", params={"metric": "ghost"})
    assert r.status_code == 422


def test_communities_endpoint(client: TestClient) -> None:
    pytest.importorskip("networkx")
    r = client.get("/api/graph/communities", params={"members_preview": 3})
    assert r.status_code == 200
    body = r.json()
    assert "communities" in body
    assert body["count"] >= 1


def test_surprising_endpoint(client: TestClient) -> None:
    pytest.importorskip("networkx")
    r = client.get("/api/graph/surprising", params={"confidence_min": 0.5})
    assert r.status_code == 200
    body = r.json()
    assert "results" in body


def test_report_endpoint(client: TestClient, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("networkx")
    monkeypatch.setattr("llm_wiki.config.GRAPH_REPORT_DIR", str(tmp_path))
    # Force the report module to pick up the patched dir at call time.
    monkeypatch.setattr("llm_wiki.graphdb.report.GRAPH_REPORT_DIR", str(tmp_path))
    r = client.post("/api/graph/report")
    assert r.status_code == 200
    body = r.json()
    assert body["markdown"].endswith("GRAPH_REPORT.md")
    assert body["json"].endswith("graph.json")


# --- PR3 /data endpoint --------------------------------------------------


def test_data_endpoint_returns_full_payload(client: TestClient) -> None:
    pytest.importorskip("networkx")
    r = client.get("/api/graph/data")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert "stats" in body
    assert "nodes" in body
    assert "edges" in body
    assert "communities" in body
    assert "surprising" in body
    assert body["stats"]["node_count"] == len(body["nodes"])


def test_data_endpoint_disabled_returns_empty_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeStore(enabled=False)
    monkeypatch.setattr("llm_wiki.api.routers.graph.get_kg_store", lambda: fake)
    from llm_wiki.api.routers.graph import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        r = c.get("/api/graph/data")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["nodes"] == []
    assert body["edges"] == []


def test_data_endpoint_confidence_filter(client: TestClient) -> None:
    pytest.importorskip("networkx")
    r = client.get("/api/graph/data", params={"confidence_min": 0.99})
    assert r.status_code == 200
    body = r.json()
    # All seeded edges have confidence 0.9 → filtered out.
    assert body["stats"]["edge_count"] == 0
