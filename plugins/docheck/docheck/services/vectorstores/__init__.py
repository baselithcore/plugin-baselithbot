"""Vector store factory. Selects backend by `settings.vector_backend`."""

from functools import lru_cache

from ...core.config import settings
from .base import VectorStore


@lru_cache(maxsize=1)
def get_store() -> VectorStore:
    if settings.vector_backend == "qdrant":
        from .qdrant import QdrantStore

        return QdrantStore()
    from .chroma import ChromaStore

    return ChromaStore()


__all__ = ["VectorStore", "get_store"]
