"""Vector store interface — abstracts Chroma (MVP) vs Qdrant (multi-tenant)."""

from typing import Any, Protocol


class VectorStore(Protocol):
    backend: str

    def upsert(
        self,
        collection: str,
        ids: list[str],
        vectors: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None: ...

    def query(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Returns list of {id, score, document, metadata}."""
        ...

    def delete(self, collection: str, ids: list[str]) -> None: ...

    def delete_collection(self, collection: str) -> None: ...
