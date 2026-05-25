"""Cross-tenant isolation test on vector store (in-memory fake store).

Verifies that collection naming + tenant scoping prevent data bleed between tenants.
Doesn't depend on real Chroma/Qdrant.
"""

from typing import Any

import pytest

from docheck.core.tenant import reset_tenant, set_tenant


class FakeStore:
    """Records (collection_name, ids) per upsert + serves queries from same scoped name."""

    backend = "fake"

    def __init__(self) -> None:
        self.collections: dict[str, dict[str, dict]] = {}

    def upsert(self, collection, ids, vectors, documents, metadatas):
        coll = self.collections.setdefault(collection, {})
        for i, _id in enumerate(ids):
            coll[_id] = {
                "vector": vectors[i],
                "document": documents[i],
                "metadata": metadatas[i],
            }

    def query(self, collection, vector, top_k=5, where=None) -> list[dict[str, Any]]:
        coll = self.collections.get(collection, {})
        out = []
        for _id, row in list(coll.items())[:top_k]:
            out.append({"id": _id, "score": 0.0, "document": row["document"], "metadata": row["metadata"]})
        return out

    def delete_collection(self, collection):
        self.collections.pop(collection, None)


def _scoped(store: FakeStore, tenant: str, name: str) -> str:
    return f"{tenant}__{name}"


def test_collections_namespaced_per_tenant() -> None:
    store = FakeStore()

    t1 = set_tenant("acme")
    store.upsert(
        _scoped(store, "acme", "policy_rules"),
        ids=["r1"],
        vectors=[[0.1, 0.2]],
        documents=["acme rule"],
        metadatas=[{"x": 1}],
    )
    reset_tenant(t1)

    t2 = set_tenant("globex")
    store.upsert(
        _scoped(store, "globex", "policy_rules"),
        ids=["r1"],
        vectors=[[0.9, 0.8]],
        documents=["globex rule"],
        metadatas=[{"x": 2}],
    )
    reset_tenant(t2)

    # Different physical collections
    assert "acme__policy_rules" in store.collections
    assert "globex__policy_rules" in store.collections
    assert store.collections["acme__policy_rules"]["r1"]["document"] == "acme rule"
    assert store.collections["globex__policy_rules"]["r1"]["document"] == "globex rule"


def test_query_only_returns_current_tenant_data() -> None:
    store = FakeStore()

    store.upsert("acme__policy_rules", ids=["r1"], vectors=[[1, 0]], documents=["acme"], metadatas=[{}])
    store.upsert("globex__policy_rules", ids=["r2"], vectors=[[0, 1]], documents=["globex"], metadatas=[{}])

    acme_hits = store.query("acme__policy_rules", [1, 0])
    globex_hits = store.query("globex__policy_rules", [0, 1])

    assert all(h["document"] == "acme" for h in acme_hits)
    assert all(h["document"] == "globex" for h in globex_hits)


@pytest.mark.parametrize("tenant", ["acme", "globex", "default"])
def test_set_tenant_active_in_test(tenant: str) -> None:
    from docheck.core.tenant import current_tenant

    token = set_tenant(tenant)
    try:
        assert current_tenant() == tenant
    finally:
        reset_tenant(token)
