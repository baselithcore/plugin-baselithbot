"""HTTP router memorie utente — RAG personale.

Post-migration 019 lo storage vettoriale è demandato a Qdrant via
:class:`llm_wiki.memories.store.MemoriesStore`. Postgres conserva solo
metadata (id, tenant, user, kind, key, value, metadata, timestamps).

Endpoints
=========

- ``GET    /api/memories``                 — lista (filtrabile per kind)
- ``POST   /api/memories``                 — crea (embed + index Qdrant)
- ``PUT    /api/memories/preferences``     — upsert preferenza key/value
- ``GET    /api/memories/{id}``            — dettaglio
- ``DELETE /api/memories/{id}``            — cancellazione (Qdrant + Postgres)
- ``POST   /api/memories/search``          — top-K similarity (RAG-side)

Embedding sincrono on-write (BGE-M3 ~10ms su GPU, ~80ms su CPU): non
giustifica una task queue separata. Se l'embedder non è disponibile
(setup mode senza modello caricato) → 503.

Per il RAG agent: usare :class:`MemoriesStore` direttamente (no HTTP
overhead) — l'endpoint /search è esposto per debug + frontend
"memorie pertinenti".
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from llm_wiki.auth.audit import write_event
from llm_wiki.auth.dependencies import require_permission, require_user
from llm_wiki.auth.permissions import Permission
from llm_wiki.db.memories import (
    delete_memory_row,
    get_memory,
    list_memories,
)
from llm_wiki.memories.store import get_memories_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memories", tags=["memories"])


# --- models ----------------------------------------------------------------


class MemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(..., min_length=1, max_length=4000)
    kind: str = Field(default="note", pattern="^(note|fact|preference)$")
    key: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] | None = None


class PreferenceUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1, max_length=80)
    value: str = Field(..., min_length=1, max_length=4000)
    metadata: dict[str, Any] | None = None


class MemorySearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    kind: str | None = Field(default=None, pattern="^(note|fact|preference)$")
    min_similarity: float = Field(default=0.0, ge=-1.0, le=1.0)
    only_mine: bool = True


# --- helpers ---------------------------------------------------------------


def _require_embedder() -> Any:
    """Recupera l'embedder globale, 503 se non pronto."""
    try:
        from llm_wiki.vectorstore.embedder import get_embedder

        emb = get_embedder()
        if emb is None:
            raise RuntimeError("embedder non inizializzato")
        return emb
    except Exception as exc:
        logger.error("[memories] embedder unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"embedder non disponibile: {exc}",
        ) from exc


def _ensure_owner(memory_id: str, user: dict[str, Any]) -> dict[str, Any]:
    mem = get_memory(memory_id)
    if not mem or mem["user_id"] != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="memoria non trovata",
        )
    return mem


# --- endpoints -------------------------------------------------------------


@router.get("")
def list_my_memories(
    kind: str | None = None,
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    items = list_memories(user_id=user["id"], kind=kind)
    return {"count": len(items), "memories": items}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_my_memory(
    body: MemoryCreate,
    user: dict[str, Any] = Depends(require_permission(Permission.MEMORY_WRITE)),
) -> dict[str, Any]:
    if body.kind == "preference" and not body.key:
        raise HTTPException(status_code=400, detail="kind='preference' richiede 'key'")
    embedder = _require_embedder()
    store = get_memories_store()
    return await store.add(
        user_id=user["id"],
        value=body.value,
        kind=body.kind,
        key=body.key,
        metadata=body.metadata,
        embedder=embedder,
    )


@router.put("/preferences")
async def upsert_my_preference(
    body: PreferenceUpsert,
    user: dict[str, Any] = Depends(require_permission(Permission.MEMORY_WRITE)),
) -> dict[str, Any]:
    embedder = _require_embedder()
    store = get_memories_store()
    return await store.upsert_preference(
        user_id=user["id"],
        key=body.key,
        value=body.value,
        metadata=body.metadata,
        embedder=embedder,
    )


@router.get("/{memory_id}")
def get_my_memory(
    memory_id: str,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    return _ensure_owner(memory_id, user)


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_my_memory(
    memory_id: str,
    user: dict[str, Any] = Depends(require_permission(Permission.MEMORY_DELETE)),
) -> None:
    _ensure_owner(memory_id, user)
    store = get_memories_store()
    deleted = await store.delete(memory_id)
    if not deleted:
        # Riga Postgres mancante (race con altra delete) — Qdrant
        # comunque pulito. Idempotent: nessun errore al chiamante.
        logger.debug("[memories] delete %s no-op (row already gone)", memory_id)
    write_event(
        "memory.delete",
        tenant_id=user["tenant_id"],
        user_id=user["id"],
        payload={"memory_id": memory_id},
    )


@router.post("/search")
async def search_my_memories(
    body: MemorySearch,
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    """Top-K similarity. ``only_mine=True`` (default) limita alle memorie
    dell'utente; ``False`` cerca su tutte le memorie del tenant — utile
    in workspace condivisi (oggi 1:1, ma future-proof)."""
    embedder = _require_embedder()
    store = get_memories_store()
    items = await store.search(
        user_id=user["id"] if body.only_mine else None,
        query=body.query,
        top_k=body.top_k,
        kind=body.kind,
        min_similarity=body.min_similarity,
        embedder=embedder,
    )
    return {"count": len(items), "results": items}


# Re-export per compatibilità back-compat con import esterni.
__all__ = [
    "router",
    "delete_memory_row",
]
