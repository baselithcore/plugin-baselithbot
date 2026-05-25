from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from typing import List, Union

import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer

from agent_jira.cache import RedisTTLCache, TTLCache, create_redis_client
from agent_jira.config import (
    CACHE_BACKEND,
    CACHE_REDIS_PREFIX,
    CACHE_REDIS_URL,
    EMBEDDER_MODEL,
    EMBEDDING_CACHE_TTL,
    RERANKER_MODEL,
)

logger = logging.getLogger(__name__)


class CachedEmbedder:
    """Wrapper around SentenceTransformer with caching capabilities."""

    def __init__(self, model: SentenceTransformer):
        self.model = model
        self._cache = None
        try:
            if CACHE_BACKEND == "redis":
                redis_client = create_redis_client(CACHE_REDIS_URL)
                self._cache = RedisTTLCache(
                    redis_client,
                    prefix=f"{CACHE_REDIS_PREFIX}:embed:{model.get_sentence_embedding_dimension()}",
                    default_ttl=EMBEDDING_CACHE_TTL,
                )
            else:
                self._cache = TTLCache(maxsize=10000, ttl=EMBEDDING_CACHE_TTL)
        except Exception as e:
            logger.warning(f"[embedder] Failed to initialize cache: {e}")

    def encode(
        self, sentences: Union[str, List[str]], **kwargs
    ) -> Union[List[float], np.ndarray, List[np.ndarray]]:
        # Passthrough if basic types not met or cache disabled
        if not self._cache:
            return self.model.encode(sentences, **kwargs)

        is_single = isinstance(sentences, str)
        inputs = [sentences] if is_single else sentences

        # 1. Identify hashes
        hashes = []
        for text in inputs:
            h = hashlib.md5(text.encode("utf-8")).hexdigest()
            hashes.append(h)

        # 2. Check cache
        results = [None] * len(inputs)
        missing_indices = []
        missing_texts = []

        for idx, h in enumerate(hashes):
            cached_val = self._cache.get(h)
            if cached_val is not None:
                results[idx] = cached_val
            else:
                missing_indices.append(idx)
                missing_texts.append(inputs[idx])

        # 3. Compute missing
        if missing_texts:
            # Force numpy for consistency in storage
            embeddings = self.model.encode(missing_texts, **kwargs)

            # 4. Update cache
            for i, emb in enumerate(embeddings):
                real_idx = missing_indices[i]
                results[real_idx] = emb
                self._cache.set(hashes[real_idx], emb)

        # 5. Format Output
        # SentenceTransformer.encode default logic:
        # If input is string -> return 1d array
        # If input is list -> return list of arrays or 2d array (if convert_to_numpy=True default)

        # Ensure we match expected return types
        final_results = results

        if kwargs.get("convert_to_numpy", True):
            final_results = np.array(results)

        if is_single:
            return final_results[0]

        return final_results

    def __getattr__(self, name):
        # Delegate other calls to model (e.g. get_sentence_embedding_dimension)
        return getattr(self.model, name)


@lru_cache(maxsize=None)
def get_embedder(
    model_name: str = EMBEDDER_MODEL,
) -> Union[SentenceTransformer, CachedEmbedder]:
    """
    Restituisce un'istanza (cachata) del modello di embedding.
    """
    base_model = SentenceTransformer(model_name)
    return CachedEmbedder(base_model)


@lru_cache(maxsize=None)
def get_reranker(model_name: str = RERANKER_MODEL) -> CrossEncoder:
    """Restituisce un'unica istanza condivisa del CrossEncoder per il reranking."""

    return CrossEncoder(model_name)


__all__ = ["get_embedder", "get_reranker", "CachedEmbedder"]
