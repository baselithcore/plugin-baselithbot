"""Operazioni Qdrant: client factory, creazione collezione hybrid-aware, upsert/delete.

Modello mutuato da `graphrag/vectorstore/qdrant_ops.py`:
- hybrid → named vectors (dense + sparse) ± multivector ColBERT
- legacy → singolo vector dense
- fallback automatico quando embedder non supporta hybrid
"""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient  # type: ignore[import-not-found]
from qdrant_client.models import (  # type: ignore[import-not-found]
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    MultiVectorComparator,
    MultiVectorConfig,
    PayloadSchemaType,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from llm_wiki.config import (
    COLLECTION_NAME,
    HYBRID_ENABLED,
    HYBRID_USE_COLBERT,
    QDRANT_API_KEY,
    QDRANT_GRPC_PORT,
    QDRANT_MODE,
    QDRANT_PATH,
    QDRANT_PREFER_GRPC,
    QDRANT_TIMEOUT,
    QDRANT_UPSERT_BATCH_SIZE,
    QDRANT_URL,
)
from llm_wiki.vectorstore.embedder import dense_dim, embedder_supports_hybrid

logger = logging.getLogger(__name__)

DENSE_VECTOR = "dense"
SPARSE_VECTOR = "sparse"
COLBERT_VECTOR = "colbert"

_PAYLOAD_INDEXES: list[tuple[str, PayloadSchemaType]] = [
    ("document_id", PayloadSchemaType.KEYWORD),
    ("page_type", PayloadSchemaType.KEYWORD),
    ("subtype", PayloadSchemaType.KEYWORD),
    ("category", PayloadSchemaType.KEYWORD),
    ("source_file", PayloadSchemaType.KEYWORD),
    ("tags", PayloadSchemaType.KEYWORD),
    # Filtro vigenza: usato in core.search() su ogni query con
    # prefer_vigente=true (must_not su 'superata'/'abrogata'). Senza
    # indice = full-payload scan a ogni retrieval.
    ("stato", PayloadSchemaType.KEYWORD),
    ("edizione-stato", PayloadSchemaType.KEYWORD),
    # Follow-the-link retrieval: expansions.py interroga per articolo
    # citato durante l'espansione rinvii (1 query/hit espandibile).
    ("articoli_citati", PayloadSchemaType.KEYWORD),
]


_client: QdrantClient | None = None


def get_qdrant() -> QdrantClient | None:
    global _client
    if _client is not None:
        return _client
    try:
        if QDRANT_MODE == "embedded":
            QDRANT_PATH.mkdir(parents=True, exist_ok=True)
            _client = QdrantClient(path=str(QDRANT_PATH))
        else:
            kwargs: dict[str, Any] = {
                "url": QDRANT_URL,
                "timeout": QDRANT_TIMEOUT,
            }
            # gRPC (porta 6334) serializza multi-vector/ColBERT ~10× più veloce
            # e senza limiti di payload HTTP. Obbligatorio con ColBERT attivo.
            if QDRANT_PREFER_GRPC:
                kwargs["prefer_grpc"] = True
                kwargs["grpc_port"] = QDRANT_GRPC_PORT
                logger.info(
                    "[qdrant] connessione via gRPC su porta %d (preferred)", QDRANT_GRPC_PORT
                )
            if QDRANT_API_KEY:
                kwargs["api_key"] = QDRANT_API_KEY
            _client = QdrantClient(**kwargs)
    except Exception as exc:
        logger.error("[qdrant] init fallita: %s", exc)
        _client = None
    return _client


def upsert_in_batches(
    points: list[Any],
    *,
    collection: str = COLLECTION_NAME,
    batch_size: int = QDRANT_UPSERT_BATCH_SIZE,
) -> int:
    """Upsert suddiviso in micro-batch per evitare payload > limit Qdrant.

    Limit server REST default: 32 MB (`service.max_request_size_mb`). Un point
    con ColBERT multi-vector pesa ~3-5 MB serializzato (≈200 token × dim float
    per ogni chunk). Quindi:
    - ColBERT on: batch ≤ 4 (≈20 MB/batch, margine).
    - ColBERT off: batch 64 OK.
    Default dinamico in `config.QDRANT_UPSERT_BATCH_SIZE`.

    Logga progresso per visibilità durante ingest. Ritorna totale points inseriti.
    """
    client = get_qdrant()
    if not client:
        return 0
    if HYBRID_USE_COLBERT and not QDRANT_PREFER_GRPC:
        logger.warning(
            "[qdrant] ColBERT attivo senza gRPC: payload REST può sforare 32 MB. "
            "Imposta QDRANT_PREFER_GRPC=true in .env."
        )
    total = 0
    n = len(points)
    start = 0
    current_batch = max(1, batch_size)
    while start < n:
        chunk = points[start : start + current_batch]
        try:
            client.upsert(collection_name=collection, points=chunk, wait=True)
            total += len(chunk)
            logger.info(
                "[qdrant] upsert batch %d/%d (%d points, size=%d)",
                total,
                n,
                len(chunk),
                current_batch,
            )
            start += len(chunk)
        except Exception as exc:
            msg = str(exc)
            # Qdrant rifiuta payload > limit con "JSON payload (N bytes) is larger
            # than allowed". Auto-retry dimezzando finché batch ≥ 1.
            is_payload_too_big = "Payload error" in msg or "is larger than allowed" in msg
            if is_payload_too_big and current_batch > 1:
                new_batch = max(1, current_batch // 2)
                logger.warning(
                    "[qdrant] payload over limit con batch=%d → riduco a %d e ritento",
                    current_batch,
                    new_batch,
                )
                current_batch = new_batch
                continue
            logger.error(
                "[qdrant] upsert batch %d-%d fallito: %s: %s",
                start,
                start + len(chunk),
                type(exc).__name__,
                msg[:300],
            )
            # Salta il chunk corrente per non incantarsi (non blocca i successivi).
            start += len(chunk)
    return total


def _hybrid_mode() -> bool:
    return HYBRID_ENABLED and embedder_supports_hybrid()


def is_hybrid_collection(collection: str = COLLECTION_NAME) -> bool:
    client = get_qdrant()
    if not client:
        return False
    try:
        info = client.get_collection(collection)
        vectors = info.config.params.vectors
        if isinstance(vectors, dict):
            return DENSE_VECTOR in vectors
        return False
    except Exception:
        return False


def _ensure_payload_indexes(collection: str = COLLECTION_NAME) -> None:
    client = get_qdrant()
    if not client:
        return
    for field_name, schema in _PAYLOAD_INDEXES:
        try:
            client.create_payload_index(
                collection_name=collection,
                field_name=field_name,
                field_schema=schema,
            )
        except Exception as exc:
            if "exists" in str(exc).lower():
                continue
            logger.debug("[qdrant] index %s: %s", field_name, exc)


def _collection_dim(client: Any, collection: str) -> int | None:
    """Dim del vettore dense della collection, None se schema non compatibile."""
    try:
        info = client.get_collection(collection)
        vectors = info.config.params.vectors
        if isinstance(vectors, dict) and DENSE_VECTOR in vectors:
            return int(vectors[DENSE_VECTOR].size)
        # legacy single-vector layout (VectorParams direttamente, non dict)
        size = getattr(vectors, "size", None)
        if size is not None:
            return int(size)
    except Exception:
        pass
    return None


def create_collection(collection: str = COLLECTION_NAME) -> None:
    """Idempotente, ma **detecta dim mismatch** e ricrea la collection se
    il vettore dense su disco ha dimensione diversa dall'embedder attivo.

    Caso tipico: `llm-wiki ingest` eseguito con fallback MiniLM (dim=384) e poi
    con BGE-M3 (dim=1024) attivato → la vecchia collection invalida ogni query
    silenziosamente. Qui invece droppiamo + ricreiamo automaticamente.
    """
    client = get_qdrant()
    if not client:
        logger.error("[qdrant] client non disponibile")
        return

    expected_dim = dense_dim()
    existing = {c.name for c in client.get_collections().collections}

    if collection in existing:
        actual_dim = _collection_dim(client, collection)
        if actual_dim is not None and actual_dim != expected_dim:
            logger.warning(
                "[qdrant] DIM MISMATCH su '%s': collection dim=%d, embedder dim=%d → drop + recreate",
                collection,
                actual_dim,
                expected_dim,
            )
            try:
                client.delete_collection(collection_name=collection)
            except Exception as exc:
                logger.error("[qdrant] delete_collection fallito: %s", exc)
                return
        else:
            _ensure_payload_indexes(collection)
            return

    dim = expected_dim

    if _hybrid_mode():
        vectors_config: dict[str, VectorParams] = {
            DENSE_VECTOR: VectorParams(size=dim, distance=Distance.COSINE),
        }
        if HYBRID_USE_COLBERT:
            vectors_config[COLBERT_VECTOR] = VectorParams(
                size=dim,
                distance=Distance.COSINE,
                multivector_config=MultiVectorConfig(comparator=MultiVectorComparator.MAX_SIM),
            )
        sparse_config = {SPARSE_VECTOR: SparseVectorParams()}
        logger.info(
            "[qdrant] creo collection hybrid '%s' (dense=%d%s)",
            collection,
            dim,
            ", colbert" if HYBRID_USE_COLBERT else "",
        )
        client.create_collection(
            collection_name=collection,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_config,
        )
    else:
        logger.info("[qdrant] creo collection LEGACY '%s' (dense=%d)", collection, dim)
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    _ensure_payload_indexes(collection)


def build_point_vector(
    dense: list[float],
    sparse: tuple[list[int], list[float]] | None = None,
    colbert: list[list[float]] | None = None,
) -> Any:
    """Costruisce il field `vector=` della PointStruct in base allo schema."""
    if not _hybrid_mode() and not is_hybrid_collection():
        return dense

    out: dict[str, Any] = {DENSE_VECTOR: dense}
    if sparse is not None:
        indices, values = sparse
        if indices:
            out[SPARSE_VECTOR] = SparseVector(indices=indices, values=values)
    if colbert and HYBRID_USE_COLBERT:
        out[COLBERT_VECTOR] = colbert
    return out


def delete_document_points(document_id: str, collection: str = COLLECTION_NAME) -> None:
    """Elimina tutti i chunk di un documento (deduplica prima di re-ingest)."""
    client = get_qdrant()
    if not client:
        return
    try:
        client.delete(
            collection_name=collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                )
            ),
            wait=True,
        )
    except Exception as exc:
        logger.debug("[qdrant] delete_document_points %s: %s", document_id, exc)


def collection_stats(collection: str = COLLECTION_NAME) -> dict[str, Any]:
    client = get_qdrant()
    if not client:
        return {"status": "unavailable"}
    try:
        info = client.get_collection(collection)
        return {
            "status": str(info.status),
            "points": int(info.points_count or 0),
            "hybrid": is_hybrid_collection(collection),
        }
    except Exception as exc:
        return {"status": "missing", "error": str(exc)}
