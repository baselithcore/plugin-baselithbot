from __future__ import annotations

from typing import Any, List, Optional, Sequence, Tuple

from sentence_transformers import CrossEncoder

from agent_jira.cache import TTLCache
from agent_jira.metrics import (
    RERANK_CACHE_HIT_TOTAL,
    RERANK_CACHE_MISS_TOTAL,
    RERANK_LATENCY_SECONDS,
    RERANK_REQUESTS_TOTAL,
)
from agent_jira.telemetry import telemetry

HitType = Any
RankedHit = Tuple[HitType, float]


def _build_cache_key(
    normalized_query: str,
    payload: dict,
    hit_id: Any,
) -> Optional[Tuple[str, str, str, str]]:
    fingerprint = payload.get("fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        return None

    chunk_index = payload.get("chunk_index")
    document_id = payload.get("document_id") or hit_id

    return (
        normalized_query,
        fingerprint,
        str(chunk_index) if chunk_index is not None else "",
        str(document_id),
    )


def rerank_hits(
    user_query: str,
    normalized_query: str,
    hits: Sequence[HitType],
    *,
    reranker: CrossEncoder,
    cache: Optional[TTLCache],
) -> List[RankedHit]:
    RERANK_REQUESTS_TOTAL.inc()
    rerank_entries: List[Optional[RankedHit]] = [None] * len(hits)
    uncached_pairs: List[Tuple[str, str]] = []
    uncached_meta: List[Tuple[int, HitType, Optional[Tuple[str, str, str, str]]]] = []

    for idx, hit in enumerate(hits):
        payload = getattr(hit, "payload", None) or {}
        raw_chunk_text = payload.get("text") or ""
        chunk_text = raw_chunk_text.strip()
        cache_key = None
        cached_score = None

        if cache is not None and chunk_text:
            cache_key = _build_cache_key(
                normalized_query, payload, getattr(hit, "id", "")
            )
            if cache_key is not None:
                cached_score = cache.get(cache_key)

        if cached_score is not None:
            rerank_entries[idx] = (hit, cached_score)
            telemetry.increment("rerank_cache.hit")
            RERANK_CACHE_HIT_TOTAL.inc()
            continue

        uncached_pairs.append((user_query, raw_chunk_text))
        uncached_meta.append((idx, hit, cache_key))

    if uncached_pairs:
        with RERANK_LATENCY_SECONDS.time():
            predicted_scores = reranker.predict(uncached_pairs).tolist()
        for (idx, hit, cache_key), score in zip(uncached_meta, predicted_scores):
            if cache_key and cache is not None:
                cache.set(cache_key, score)
                telemetry.increment("rerank_cache.write")
            telemetry.increment("rerank_cache.miss")
            RERANK_CACHE_MISS_TOTAL.inc()
            rerank_entries[idx] = (hit, score)

    ranked_hits = [entry for entry in rerank_entries if entry is not None]
    if not ranked_hits:
        ranked_hits = [(hit, 0.0) for hit in hits]

    ranked_hits = sorted(ranked_hits, key=lambda item: item[1], reverse=True)
    return ranked_hits
