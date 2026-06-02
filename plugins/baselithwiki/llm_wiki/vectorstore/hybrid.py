"""Hybrid search via Qdrant Query API.

Pipeline:
1. Prefetch dense (semantico) + sparse (BM25-like lexical)
2. Fusione RRF
3. Re-ranking ColBERT multi-vector late-interaction (opzionale)

Fallback trasparente a dense-only quando collection/embedder non supportano hybrid.
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from typing import Any

from qdrant_client.models import (  # type: ignore[import-not-found]
    Filter,
    Fusion,
    FusionQuery,
    Prefetch,
    SparseVector,
)

from llm_wiki.config import (
    COLLECTION_NAME,
    HYBRID_PREFETCH_LIMIT,
    HYBRID_USE_COLBERT,
    QUERY_EMBED_CACHE_SIZE,
)
from llm_wiki.vectorstore.embedder import EmbeddingOutput, get_embedder
from llm_wiki.vectorstore.qdrant_ops import (
    COLBERT_VECTOR,
    DENSE_VECTOR,
    SPARSE_VECTOR,
    get_qdrant,
    is_hybrid_collection,
)

logger = logging.getLogger(__name__)


# LRU cache di EmbeddingOutput per query string. Bounded a
# ``QUERY_EMBED_CACHE_SIZE`` entries; 0 = disabilitata. Thread-safe via lock.
# Chiave = (embedder_name, query). Aggiunta del nome difende da scenari
# embedder swap a runtime (reset_embedder()) — entries con embedder stale non
# matchano e cadono per LRU eviction.
_embed_cache: OrderedDict[tuple[str, str], EmbeddingOutput] = OrderedDict()
_embed_cache_lock = threading.Lock()


def reset_query_embed_cache() -> None:
    """Svuota la cache query→embedding (call dopo reset_embedder)."""
    with _embed_cache_lock:
        _embed_cache.clear()


def _embed_query(query: str) -> EmbeddingOutput | None:
    emb = get_embedder()
    if not emb:
        return None

    cache_size = QUERY_EMBED_CACHE_SIZE
    cache_key: tuple[str, str] | None = None
    if cache_size > 0:
        cache_key = (emb.name, query)
        with _embed_cache_lock:
            cached = _embed_cache.get(cache_key)
            if cached is not None:
                _embed_cache.move_to_end(cache_key)
                return cached

    try:
        out = emb.encode([query], is_query=True)
    except Exception as exc:
        logger.error("[hybrid] embed query fallito: %s", exc)
        return None

    if cache_key is not None and out and out.dense:
        with _embed_cache_lock:
            _embed_cache[cache_key] = out
            _embed_cache.move_to_end(cache_key)
            while len(_embed_cache) > cache_size:
                _embed_cache.popitem(last=False)

    return out


def _sparse_to_qdrant(sparse: tuple[list[int], list[float]]) -> SparseVector:
    indices, values = sparse
    return SparseVector(indices=indices, values=values)


def _dense_only(
    vector: list[float],
    *,
    limit: int,
    qfilter: Filter | None,
    collection: str,
) -> list[dict[str, Any]]:
    client = get_qdrant()
    if not client:
        return []
    resp = client.query_points(
        collection_name=collection,
        query=vector,
        limit=limit,
        query_filter=qfilter,
        with_payload=True,
    )
    return [
        {"id": str(p.id), "score": float(p.score), "payload": p.payload or {}}
        for p in resp.points
    ]


def hybrid_search(
    query: str,
    *,
    limit: int = 8,
    qfilter: Filter | None = None,
    collection: str = COLLECTION_NAME,
) -> list[dict[str, Any]]:
    client = get_qdrant()
    if not client:
        return []

    emb_out = _embed_query(query)
    if not emb_out or not emb_out.dense:
        return []

    dense_vec = emb_out.dense[0]

    # Fast path dense-only
    if not is_hybrid_collection(collection) or not emb_out.has_sparse():
        return _dense_only(
            dense_vec, limit=limit, qfilter=qfilter, collection=collection
        )

    sparse_vec = _sparse_to_qdrant(emb_out.sparse[0])

    prefetches = [
        Prefetch(
            query=dense_vec,
            using=DENSE_VECTOR,
            limit=HYBRID_PREFETCH_LIMIT,
            filter=qfilter,
        ),
        Prefetch(
            query=sparse_vec,
            using=SPARSE_VECTOR,
            limit=HYBRID_PREFETCH_LIMIT,
            filter=qfilter,
        ),
    ]

    try:
        if HYBRID_USE_COLBERT and emb_out.has_colbert():
            rrf_stage = Prefetch(
                prefetch=prefetches,
                query=FusionQuery(fusion=Fusion.RRF),
                limit=HYBRID_PREFETCH_LIMIT,
                filter=qfilter,
            )
            resp = client.query_points(
                collection_name=collection,
                prefetch=[rrf_stage],
                query=emb_out.colbert[0],
                using=COLBERT_VECTOR,
                limit=limit,
                with_payload=True,
                query_filter=qfilter,
            )
        else:
            resp = client.query_points(
                collection_name=collection,
                prefetch=prefetches,
                query=FusionQuery(fusion=Fusion.RRF),
                limit=limit,
                with_payload=True,
                query_filter=qfilter,
            )
    except Exception as exc:
        logger.warning("[hybrid] query fallita (%s); fallback dense-only", exc)
        return _dense_only(
            dense_vec, limit=limit, qfilter=qfilter, collection=collection
        )

    return [
        {"id": str(p.id), "score": float(p.score), "payload": p.payload or {}}
        for p in resp.points
    ]
