# app/vectorstore/qdrant_ops.py
"""Qdrant collection and point operations."""

from __future__ import annotations

import logging

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    VectorParams,
)

from agent_jira.tenant_context import get_current_tenant_id
from agent_jira.config import COLLECTION, QDRANT, QDRANT_MODE

logger = logging.getLogger(__name__)

# Constants
INDEX_SCROLL_PAGE_SIZE = 256


def create_collection() -> None:
    """Crea la collezione in Qdrant se non esiste già."""
    existing = [c.name for c in QDRANT.get_collections().collections]
    if COLLECTION not in existing:
        logger.info(
            "[vectorstore] Creo collezione '%s' su Qdrant (%s)",
            COLLECTION,
            QDRANT_MODE,
        )
        QDRANT.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
    else:
        logger.info(
            "[vectorstore] Collezione '%s' già presente in Qdrant (%s)",
            COLLECTION,
            QDRANT_MODE,
        )


def _delete_document_points(document_id: str) -> None:
    """Elimina tutti i chunk associati al documento indicato, filtrati per tenant."""
    must_conditions = [
        FieldCondition(
            key="document_id",
            match=MatchValue(value=document_id),
        )
    ]
    tenant_id = get_current_tenant_id()
    if tenant_id:
        must_conditions.append(
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
        )
    try:
        QDRANT.delete(
            collection_name=COLLECTION,
            points_selector=FilterSelector(filter=Filter(must=must_conditions)),
            wait=True,
        )
    except Exception as exc:  # pragma: no cover - best effort cleanup
        logger.warning(
            "[vectorstore] Failed to delete stale points for %s: %s",
            document_id,
            exc,
        )
