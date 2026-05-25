"""Regression tests per ottimizzazioni perf retrieval.

Copre:
- Query embedding cache (`hybrid._embed_query`): hit/miss, eviction LRU,
  flush su `reset_embedder`.
- `parallel.parallel_map`: ordine preservato, fallback serial in embedded
  mode, propagazione eccezioni.
- `expand_with_rinvii` post-refactor: 1 task per (doc_id, article), dedup.
"""

from __future__ import annotations

from typing import Any

import pytest

# --- parallel_map ----------------------------------------------------------


def test_parallel_map_preserves_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mappa preserva ordine input → output anche in modalità parallela."""
    monkeypatch.setattr("llm_wiki.config.QDRANT_MODE", "server")
    monkeypatch.setattr("llm_wiki.config.RETRIEVAL_PARALLEL_ENABLED", True)
    monkeypatch.setattr("llm_wiki.vectorstore.parallel.QDRANT_MODE", "server")
    monkeypatch.setattr(
        "llm_wiki.vectorstore.parallel.RETRIEVAL_PARALLEL_ENABLED", True
    )

    from llm_wiki.vectorstore.parallel import parallel_map

    items = list(range(20))
    out = parallel_map(lambda x: x * 2, items)
    assert out == [x * 2 for x in items]


def test_parallel_map_embedded_mode_runs_serial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In modalità embedded il fan-out è disabilitato → tutto sullo stesso thread."""
    monkeypatch.setattr("llm_wiki.vectorstore.parallel.QDRANT_MODE", "embedded")
    monkeypatch.setattr(
        "llm_wiki.vectorstore.parallel.RETRIEVAL_PARALLEL_ENABLED", True
    )

    import threading

    from llm_wiki.vectorstore.parallel import is_parallel_safe, parallel_map

    assert not is_parallel_safe()
    seen_threads: set[int] = set()

    def _capture(_x: int) -> int:
        seen_threads.add(threading.get_ident())
        return _x

    parallel_map(_capture, [1, 2, 3, 4])
    # Tutti sullo stesso thread (il caller) in embedded mode.
    assert len(seen_threads) == 1


def test_parallel_map_single_item_no_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lista di 1 elemento → niente overhead pool, esecuzione diretta."""
    monkeypatch.setattr("llm_wiki.vectorstore.parallel.QDRANT_MODE", "server")
    monkeypatch.setattr(
        "llm_wiki.vectorstore.parallel.RETRIEVAL_PARALLEL_ENABLED", True
    )

    from llm_wiki.vectorstore.parallel import parallel_map

    assert parallel_map(lambda x: x + 1, [42]) == [43]


def test_parallel_map_propagates_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.vectorstore.parallel.QDRANT_MODE", "server")
    monkeypatch.setattr(
        "llm_wiki.vectorstore.parallel.RETRIEVAL_PARALLEL_ENABLED", True
    )

    from llm_wiki.vectorstore.parallel import parallel_map

    def _boom(x: int) -> int:
        if x == 2:
            raise RuntimeError("nope")
        return x

    with pytest.raises(RuntimeError, match="nope"):
        parallel_map(_boom, [1, 2, 3])


# --- query embedding cache -------------------------------------------------


class _FakeEmbedder:
    name = "fake"
    dense_dim = 4
    supports_sparse = False
    supports_colbert = False

    def __init__(self) -> None:
        self.calls = 0

    def encode(self, texts: list[str], *, is_query: bool = False) -> Any:
        from llm_wiki.vectorstore.embedder import EmbeddingOutput

        self.calls += 1
        # 1 dense vec per testo. is_query è informativo per la cache key.
        return EmbeddingOutput(dense=[[float(len(t)) for _ in range(4)] for t in texts])


def test_embed_cache_hits_second_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.QUERY_EMBED_CACHE_SIZE", 8)
    monkeypatch.setattr("llm_wiki.vectorstore.hybrid.QUERY_EMBED_CACHE_SIZE", 8)

    from llm_wiki.vectorstore import hybrid

    hybrid.reset_query_embed_cache()
    fake = _FakeEmbedder()
    monkeypatch.setattr("llm_wiki.vectorstore.hybrid.get_embedder", lambda: fake)

    out1 = hybrid._embed_query("cos'è il chunking")
    out2 = hybrid._embed_query("cos'è il chunking")

    assert out1 is out2  # stessa istanza dalla cache
    assert fake.calls == 1


def test_embed_cache_disabled_when_size_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.QUERY_EMBED_CACHE_SIZE", 0)
    monkeypatch.setattr("llm_wiki.vectorstore.hybrid.QUERY_EMBED_CACHE_SIZE", 0)

    from llm_wiki.vectorstore import hybrid

    hybrid.reset_query_embed_cache()
    fake = _FakeEmbedder()
    monkeypatch.setattr("llm_wiki.vectorstore.hybrid.get_embedder", lambda: fake)

    hybrid._embed_query("a")
    hybrid._embed_query("a")
    assert fake.calls == 2  # nessuna cache → 2 chiamate


def test_embed_cache_lru_eviction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.QUERY_EMBED_CACHE_SIZE", 2)
    monkeypatch.setattr("llm_wiki.vectorstore.hybrid.QUERY_EMBED_CACHE_SIZE", 2)

    from llm_wiki.vectorstore import hybrid

    hybrid.reset_query_embed_cache()
    fake = _FakeEmbedder()
    monkeypatch.setattr("llm_wiki.vectorstore.hybrid.get_embedder", lambda: fake)

    hybrid._embed_query("q1")
    hybrid._embed_query("q2")
    hybrid._embed_query("q3")  # evict q1
    hybrid._embed_query("q1")  # cache miss → ri-encode

    # 4 chiamate totali: q1, q2, q3, q1-again (post-eviction)
    assert fake.calls == 4


def test_embed_cache_flushed_on_reset_embedder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.QUERY_EMBED_CACHE_SIZE", 8)
    monkeypatch.setattr("llm_wiki.vectorstore.hybrid.QUERY_EMBED_CACHE_SIZE", 8)

    from llm_wiki.vectorstore import embedder as embedder_mod
    from llm_wiki.vectorstore import hybrid

    hybrid.reset_query_embed_cache()
    fake = _FakeEmbedder()
    monkeypatch.setattr("llm_wiki.vectorstore.hybrid.get_embedder", lambda: fake)

    hybrid._embed_query("x")
    assert fake.calls == 1

    embedder_mod.reset_embedder()  # → flush hybrid cache via hook

    # Subito dopo il reset la cache è vuota → la prossima call re-encoda.
    hybrid._embed_query("x")
    assert fake.calls == 2


# --- expand_with_rinvii (post-refactor) ------------------------------------


class _FakePoint:
    def __init__(self, pid: str, doc_id: str, article: str) -> None:
        self.id = pid
        self.payload = {
            "document_id": doc_id,
            "articoli_citati": [article],
        }


class _FakeQdrant:
    def __init__(self, points_by_call: list[list[_FakePoint]] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._points_by_call = points_by_call or []

    def scroll(self, **kwargs: Any) -> tuple[list[_FakePoint], None]:
        self.calls.append(kwargs)
        if self._points_by_call:
            return self._points_by_call.pop(0), None
        return [], None


def test_rinvii_dedup_same_doc_article(monkeypatch: pytest.MonkeyPatch) -> None:
    """Due hit con stesso (doc_id, article) → 1 sola call scroll."""
    fake = _FakeQdrant()
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: fake)

    from llm_wiki.vectorstore.expansions import expand_with_rinvii

    hits = [
        {
            "id": "h1",
            "point_id": "h1",
            "payload": {"document_id": "X", "articoli_citati": ["A"]},
            "score": 0.9,
        },
        {
            "id": "h2",
            "point_id": "h2",
            "payload": {"document_id": "X", "articoli_citati": ["A"]},
            "score": 0.8,
        },
    ]
    expand_with_rinvii(hits, max_extra=5, per_hit_cap=2)
    assert len(fake.calls) == 1


def test_rinvii_qdrant_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: None)
    from llm_wiki.vectorstore.expansions import expand_with_rinvii

    hits = [
        {
            "id": "h1",
            "payload": {"document_id": "X", "articoli_citati": ["A"]},
            "score": 0.9,
        }
    ]
    assert expand_with_rinvii(hits) == hits


def test_rinvii_global_max_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    pts = [
        _FakePoint("p1", "X", "A"),
        _FakePoint("p2", "X", "A"),
        _FakePoint("p3", "X", "B"),
    ]
    # Stesso elenco per ogni call (FakeQdrant ritorna tutti i points).
    fake = _FakeQdrant(points_by_call=[[*pts], [*pts]])
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: fake)

    from llm_wiki.vectorstore.expansions import expand_with_rinvii

    hits = [
        {
            "id": "h1",
            "point_id": "h1",
            "payload": {"document_id": "X", "articoli_citati": ["A", "B"]},
            "score": 0.9,
        }
    ]
    out = expand_with_rinvii(hits, max_extra=2, per_hit_cap=5)
    extras = [h for h in out if h.get("via_rinvio")]
    assert len(extras) <= 2
