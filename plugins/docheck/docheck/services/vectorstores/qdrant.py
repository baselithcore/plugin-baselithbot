"""Qdrant implementation of VectorStore (multi-tenant via per-tenant namespace)."""

from functools import lru_cache
from typing import Any

from ...core.config import settings
from ...core.tenant import current_tenant


@lru_cache(maxsize=1)
def _client() -> Any:
    from qdrant_client import QdrantClient

    if not settings.qdrant_url:
        raise RuntimeError("DOCHECK_QDRANT_URL required when vector_backend=qdrant")
    return QdrantClient(url=settings.qdrant_url, prefer_grpc=False)


def _scoped(collection: str) -> str:
    return f"{current_tenant()}__{collection}"


def _ensure(name: str, dim: int) -> None:
    from qdrant_client.http import models as qm

    client = _client()
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )


class QdrantStore:
    backend = "qdrant"

    def upsert(
        self,
        collection: str,
        ids: list[str],
        vectors: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        from qdrant_client.http import models as qm

        if not vectors:
            return
        name = _scoped(collection)
        _ensure(name, len(vectors[0]))
        points = [
            qm.PointStruct(
                id=ids[i],
                vector=vectors[i],
                payload={"document": documents[i], **metadatas[i]},
            )
            for i in range(len(ids))
        ]
        _client().upsert(collection_name=name, points=points)

    def query(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        from qdrant_client.http import models as qm

        name = _scoped(collection)
        flt = None
        if where:
            flt = qm.Filter(
                must=[
                    qm.FieldCondition(key=k, match=qm.MatchValue(value=v))
                    for k, v in where.items()
                ]
            )
        res = _client().search(
            collection_name=name,
            query_vector=vector,
            limit=top_k,
            query_filter=flt,
            with_payload=True,
        )
        out: list[dict[str, Any]] = []
        for hit in res:
            payload = hit.payload or {}
            out.append(
                {
                    "id": str(hit.id),
                    "score": float(hit.score),
                    "document": payload.pop("document", ""),
                    "metadata": payload,
                }
            )
        return out

    def delete(self, collection: str, ids: list[str]) -> None:
        if not ids:
            return
        try:
            from qdrant_client.models import PointIdsList

            _client().delete(
                collection_name=_scoped(collection),
                points_selector=PointIdsList(points=ids),
            )
        except Exception:
            pass

    def delete_collection(self, collection: str) -> None:
        _client().delete_collection(_scoped(collection))
