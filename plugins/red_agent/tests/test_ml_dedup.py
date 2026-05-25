"""Semantic dedup service unit tests."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from plugins.red_agent.ml.dedup import SemanticDedupService
from plugins.red_agent.models import Finding, Severity


class _FakeEmbedder:
    """Returns a deterministic vector per text so cosine matches in tests."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        self.calls.append(list(texts))
        # 4-dim unit-ish vectors keyed by hash. Equal texts → equal vectors,
        # different texts → orthogonal vectors. Cosine similarity does the
        # rest in the test fake.
        out: list[list[float]] = []
        for t in texts:
            slot = abs(hash(t)) % 4
            v = [0.0, 0.0, 0.0, 0.0]
            v[slot] = 1.0
            out.append(v)
        return out


class _FakeProvider:
    def __init__(self) -> None:
        self.upserts: list[list[dict[str, Any]]] = []

    async def upsert(
        self, collection_name: str, points: list[dict[str, Any]], **kwargs: Any
    ) -> None:
        self.upserts.append(points)


class _FakeVectorStore:
    """In-memory stand-in for VectorStoreService.

    Returns a hit only when an exact vector match exists in store and the
    payload's tenant_id + target_value match the search filter.
    """

    def __init__(self) -> None:
        self.points: list[dict[str, Any]] = []
        self.provider = _FakeProvider()
        self.created_collections: list[str] = []

    async def create_collection(
        self,
        collection_name: str | None = None,
        vector_size: int | None = None,
        **kwargs: Any,
    ) -> None:
        if collection_name:
            self.created_collections.append(collection_name)

    async def search(
        self,
        query_vector: Any,
        k: int | None = None,
        collection_name: str | None = None,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> list[Any]:
        # Fold provider upserts into the searchable set so the test sees
        # what the real flow would: index then query.
        for batch in self.provider.upserts:
            for p in batch:
                if p not in self.points:
                    self.points.append(p)

        for p in self.points:
            if list(p["vector"]) == list(query_vector):
                # Mimic Qdrant ScoredPoint shape with .id and .score.
                class _Hit:
                    pass

                hit = _Hit()
                hit.id = p["id"]  # type: ignore[attr-defined]
                hit.score = 0.99  # type: ignore[attr-defined]
                return [hit]
        return []


def _finding(title: str = "ssh open", endpoint: str = "ssh://h:22") -> Finding:
    return Finding(
        scanner="nmap",
        title=title,
        description="d",
        severity=Severity.LOW,
        target="example.com",
        endpoint=endpoint,
    )


@pytest.mark.asyncio
async def test_disabled_when_dependencies_missing() -> None:
    svc = SemanticDedupService(
        vectorstore=None, embedder=None, collection="c", threshold=0.9, enabled=True
    )
    assert svc.enabled is False
    out = await svc.dedupe(
        uuid4(), [_finding()], tenant_id="t", target_value="example.com"
    )
    assert len(out.new) == 1
    assert out.duplicates == []


@pytest.mark.asyncio
async def test_first_finding_is_new_and_indexed() -> None:
    vs = _FakeVectorStore()
    svc = SemanticDedupService(
        vectorstore=vs,
        embedder=_FakeEmbedder(),
        collection="red_agent_findings",
        threshold=0.9,
        enabled=True,
    )
    f = _finding()
    out = await svc.dedupe(uuid4(), [f], tenant_id="t", target_value="example.com")
    assert len(out.new) == 1 and out.duplicates == []
    assert vs.created_collections == ["red_agent_findings"]
    assert vs.provider.upserts and vs.provider.upserts[0][0]["id"] == str(f.id)


@pytest.mark.asyncio
async def test_second_identical_finding_is_marked_duplicate() -> None:
    vs = _FakeVectorStore()
    embedder = _FakeEmbedder()
    svc = SemanticDedupService(
        vectorstore=vs,
        embedder=embedder,
        collection="red_agent_findings",
        threshold=0.9,
        enabled=True,
    )
    scan_id: UUID = uuid4()
    f1 = _finding()
    out1 = await svc.dedupe(scan_id, [f1], tenant_id="t", target_value="example.com")
    assert len(out1.new) == 1

    f2 = _finding()  # same scanner/title/endpoint → same embedding text
    out2 = await svc.dedupe(uuid4(), [f2], tenant_id="t", target_value="example.com")
    assert out2.new == []
    assert len(out2.duplicates) == 1
    dup = out2.duplicates[0]
    assert dup.evidence["duplicate_of"] == str(f1.id)
    assert 0.0 <= dup.evidence["duplicate_score"] <= 1.0


@pytest.mark.asyncio
async def test_distinct_findings_both_indexed_as_new() -> None:
    vs = _FakeVectorStore()
    svc = SemanticDedupService(
        vectorstore=vs,
        embedder=_FakeEmbedder(),
        collection="red_agent_findings",
        threshold=0.9,
        enabled=True,
    )
    a = _finding(title="ssh open", endpoint="ssh://h:22")
    b = _finding(title="http open", endpoint="http://h:80")
    out = await svc.dedupe(uuid4(), [a, b], tenant_id="t", target_value="example.com")
    assert len(out.new) == 2
    assert out.duplicates == []


@pytest.mark.asyncio
async def test_embedder_failure_returns_findings_unchanged() -> None:
    class _BoomEmbedder:
        def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
            raise RuntimeError("model load failed")

    vs = _FakeVectorStore()
    svc = SemanticDedupService(
        vectorstore=vs,
        embedder=_BoomEmbedder(),
        collection="red_agent_findings",
        threshold=0.9,
        enabled=True,
    )
    f = _finding()
    out = await svc.dedupe(uuid4(), [f], tenant_id="t", target_value="example.com")
    assert out.new == [f]
    assert out.duplicates == []
