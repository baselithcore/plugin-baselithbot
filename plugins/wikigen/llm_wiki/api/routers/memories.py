"""HTTP router memorie utente — RAG personale.

Endpoints
=========

- ``GET    /api/memories``                 — lista (filtrabile per kind)
- ``POST   /api/memories``                 — crea (embed sincrono on-write)
- ``PUT    /api/memories/preferences``     — upsert preferenza key/value
- ``GET    /api/memories/{id}``            — dettaglio
- ``DELETE /api/memories/{id}``            — cancellazione
- ``POST   /api/memories/search``          — top-K similarity (RAG-side)

Embedding sincrono on-write: BGE-M3 ~10ms su GPU, ~80ms su CPU. Non
giustifica una task queue separata. Se l'embedder non è disponibile
(setup mode senza modello caricato) → 503.

Per il RAG agent, usare :func:`llm_wiki.db.memories.search_similar`
direttamente (no HTTP overhead). L'endpoint /search è esposto per
debug + uso da frontend (panel "memorie pertinenti").
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
    create_memory,
    delete_memory,
    get_memory,
    list_memories,
    search_similar,
    upsert_preference,
)

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


def _embed(text: str, *, is_query: bool = False) -> list[float]:
    """Calcola dense embedding via embedder globale. 503 se non pronto."""
    try:
        from llm_wiki.vectorstore.embedder import get_embedder

        emb = get_embedder()
        if emb is None:
            raise RuntimeError("embedder non inizializzato")
        out = emb.encode([text], is_query=is_query)
        if not out.dense or not out.dense[0]:
            raise RuntimeError("embedder ha restituito vector vuoto")
        return out.dense[0]
    except Exception as exc:
        logger.error("[memories] embed failed: %s", exc)
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
def create_my_memory(
    body: MemoryCreate,
    user: dict[str, Any] = Depends(require_permission(Permission.MEMORY_WRITE)),
) -> dict[str, Any]:
    if body.kind == "preference" and not body.key:
        raise HTTPException(status_code=400, detail="kind='preference' richiede 'key'")
    embedding = _embed(body.value)
    return create_memory(
        user_id=user["id"],
        value=body.value,
        embedding=embedding,
        kind=body.kind,
        key=body.key,
        metadata=body.metadata,
    )


@router.put("/preferences")
def upsert_my_preference(
    body: PreferenceUpsert,
    user: dict[str, Any] = Depends(require_permission(Permission.MEMORY_WRITE)),
) -> dict[str, Any]:
    embedding = _embed(body.value)
    return upsert_preference(
        user_id=user["id"],
        key=body.key,
        value=body.value,
        embedding=embedding,
        metadata=body.metadata,
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
def delete_my_memory(
    memory_id: str,
    user: dict[str, Any] = Depends(require_permission(Permission.MEMORY_DELETE)),
) -> None:
    _ensure_owner(memory_id, user)
    delete_memory(memory_id)
    write_event(
        "memory.delete",
        tenant_id=user["tenant_id"],
        user_id=user["id"],
        payload={"memory_id": memory_id},
    )


@router.post("/search")
def search_my_memories(
    body: MemorySearch,
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    """Top-K similarity. ``only_mine=True`` (default) limita alle memorie
    dell'utente; ``False`` cerca su tutte le memorie del tenant — utile
    in workspace condivisi (oggi 1:1, ma future-proof)."""
    embedding = _embed(body.query, is_query=True)
    items = search_similar(
        user_id=user["id"] if body.only_mine else None,
        query_embedding=embedding,
        top_k=body.top_k,
        kind=body.kind,
        min_similarity=body.min_similarity,
    )
    return {"count": len(items), "results": items}
