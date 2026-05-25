"""
Utility batch per rigenerare archi SIMILAR nel grafo, opzionale e rate-limitato.

Esempio esecuzione:
    python -m app.graph_jobs --top-k 5 --sleep 0.05

Note:
- Usa il primo chunk di ogni documento come vettore di query.
- Limita gli archi a top_k per documento per evitare esplosioni.
- Se GraphDB è disabilitato, non fa nulla.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable, Tuple

from qdrant_client.models import FieldCondition, Filter, MatchValue

from agent_jira.graphdb import graph_db
from agent_jira.tenant_context import get_current_tenant_id
from agent_jira.vectorstore import INDEX_SCROLL_PAGE_SIZE
from agent_jira.config import COLLECTION, GRAPH_SIMILAR_TOP_K, QDRANT


def _tenant_filter() -> Filter | None:
    """Restituisce un Filter Qdrant che limita i punti al tenant corrente."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return None
    return Filter(
        must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
    )


def _iter_document_ids(batch: int = INDEX_SCROLL_PAGE_SIZE) -> Iterable[str]:
    """Scorre tutti i document_id presenti nella collezione (scoped al tenant corrente se presente)."""

    scroll_filter = _tenant_filter()
    offset = None
    while True:
        points, offset = QDRANT.scroll(  # type: ignore[arg-type]
            collection_name=COLLECTION,
            limit=batch,
            offset=offset,
            with_payload=True,
            with_vectors=False,
            scroll_filter=scroll_filter,
        )
        for point in points:
            payload = point.payload or {}
            doc_id = payload.get("document_id")
            if isinstance(doc_id, str) and doc_id.strip():
                yield doc_id.strip()
        if offset is None:
            break


def _first_vector_for_doc(doc_id: str) -> Tuple[list[float] | None, dict | None]:
    """Recupera il primo chunk (vector + payload) di un documento, se presente."""

    must_conditions = [
        FieldCondition(key="document_id", match=MatchValue(value=doc_id))
    ]
    tenant_id = get_current_tenant_id()
    if tenant_id:
        must_conditions.append(
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
        )
    filter_doc = Filter(must=must_conditions)
    points, _ = QDRANT.scroll(  # type: ignore[arg-type]
        collection_name=COLLECTION,
        limit=1,
        with_payload=True,
        with_vectors=True,
        scroll_filter=filter_doc,
    )
    if not points:
        return None, None
    pt = points[0]
    return getattr(pt, "vector", None), pt.payload or {}


def rebuild_similar_edges(top_k: int | None = None, sleep_seconds: float = 0.05) -> int:
    """
    Ricostruisce archi SIMILAR per tutti i documenti usando il primo chunk come query.
    Ritorna il numero di archi creati/aggiornati.
    """

    if not graph_db.is_enabled():
        return 0

    created = 0
    max_k = max(1, top_k or GRAPH_SIMILAR_TOP_K)
    for doc_id in _iter_document_ids():
        vector, payload = _first_vector_for_doc(doc_id)
        if vector is None:
            continue
        hits = QDRANT.query_points(  # type: ignore[arg-type]
            collection_name=COLLECTION,
            query=vector,
            limit=max_k + 1,
            with_payload=True,
            with_vectors=False,
            query_filter=_tenant_filter(),
        ).points
        doc_ids = []
        for hit in hits:
            hit_payload = getattr(hit, "payload", None) or {}
            hit_doc = hit_payload.get("document_id")
            if isinstance(hit_doc, str) and hit_doc.strip():
                doc_ids.append((hit_doc.strip(), getattr(hit, "score", None)))
        if not doc_ids:
            continue
        pivot, _ = doc_ids[0]
        for other_id, score in doc_ids[1 : max_k + 1]:
            if other_id == pivot:
                continue
            graph_db.upsert_similarity(pivot, other_id, score=score)
            created += 1
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rigenera archi SIMILAR nel grafo.")
    parser.add_argument(
        "--top-k", type=int, default=None, help="Top K similari per doc"
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.05,
        help="Pausa (secondi) tra documenti per rate limiting",
    )
    args = parser.parse_args(argv)
    created = rebuild_similar_edges(top_k=args.top_k, sleep_seconds=args.sleep)
    print(f"[graph_jobs] Archi SIMILAR creati/aggiornati: {created}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
