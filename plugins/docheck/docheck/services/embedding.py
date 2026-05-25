"""BGE-M3 multilingue embedding client. Vector storage via vectorstores abstraction."""

import hashlib
from functools import lru_cache
from typing import Any

from FlagEmbedding import BGEM3FlagModel

from ..core.config import settings
from .vectorstores import get_store


@lru_cache(maxsize=1)
def get_embedder() -> BGEM3FlagModel:
    return BGEM3FlagModel(settings.embedding_model, use_fp16=True)


def embed(texts: list[str]) -> list[list[float]]:
    out = get_embedder().encode(texts, return_dense=True)
    return [list(map(float, v)) for v in out["dense_vecs"]]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_or_create_collection(name: str) -> "_ChromaCollectionShim":
    """Compatibility shim. New code should use `vectorstores.get_store()`."""
    return _ChromaCollectionShim(name)


class _ChromaCollectionShim:
    """Adapter so legacy `coll.query(...)` / `coll.upsert(...)` calls keep working."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._store = get_store()

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        self._store.upsert(self._name, ids, embeddings, documents, metadatas)

    def query(
        self,
        query_embeddings: list[list[float]],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, list[list[Any]]]:
        hits = self._store.query(self._name, query_embeddings[0], top_k=n_results, where=where)
        return {
            "ids": [[h["id"] for h in hits]],
            "distances": [[h["score"] for h in hits]],
            "documents": [[h["document"] for h in hits]],
            "metadatas": [[h["metadata"] for h in hits]],
        }
