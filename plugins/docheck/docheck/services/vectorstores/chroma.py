"""ChromaDB implementation of VectorStore (MVP single-process)."""

from functools import lru_cache
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from ...core.config import settings
from ...core.tenant import current_tenant


@lru_cache(maxsize=1)
def _client() -> chromadb.api.ClientAPI:
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(settings.chroma_persist_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _scoped(collection: str) -> str:
    """Prefix collection name with tenant for namespace isolation."""
    return f"{current_tenant()}__{collection}"


class ChromaStore:
    backend = "chroma"

    def upsert(
        self,
        collection: str,
        ids: list[str],
        vectors: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        coll = _client().get_or_create_collection(
            name=_scoped(collection),
            metadata={"hnsw:space": "cosine"},
        )
        coll.upsert(
            ids=ids,
            embeddings=vectors,  # type: ignore[arg-type, unused-ignore]
            documents=documents,
            metadatas=metadatas,  # type: ignore[arg-type, unused-ignore]
        )

    def query(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        coll = _client().get_or_create_collection(name=_scoped(collection))
        res = coll.query(
            query_embeddings=[vector],  # type: ignore[arg-type, unused-ignore]
            n_results=top_k,
            where=where,
        )
        out: list[dict[str, Any]] = []
        ids = (res.get("ids") or [[]])[0]
        for i, _id in enumerate(ids):
            out.append(
                {
                    "id": _id,
                    "score": (res.get("distances") or [[0]])[0][i],
                    "document": (res.get("documents") or [[""]])[0][i],
                    "metadata": (res.get("metadatas") or [[{}]])[0][i] or {},
                }
            )
        return out

    def delete(self, collection: str, ids: list[str]) -> None:
        if not ids:
            return
        coll = _client().get_or_create_collection(name=_scoped(collection))
        coll.delete(ids=ids)

    def delete_collection(self, collection: str) -> None:
        _client().delete_collection(_scoped(collection))
