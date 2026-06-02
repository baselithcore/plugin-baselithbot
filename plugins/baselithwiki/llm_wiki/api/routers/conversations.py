"""HTTP router conversations + messages.

Sostituisce ``localStorage.llm-wiki:conversations`` lato frontend.

Endpoints
=========

- ``GET    /api/conversations``                 — lista
- ``POST   /api/conversations``                 — crea
- ``GET    /api/conversations/{id}``            — dettaglio
- ``PATCH  /api/conversations/{id}``            — rename / pin / lock
- ``DELETE /api/conversations/{id}``            — cancellazione (CASCADE messages)
- ``GET    /api/conversations/{id}/messages``   — turni paginati
- ``POST   /api/conversations/{id}/messages``   — append turno (no LLM call)

Il chat streaming (``POST /api/chat/stream``) resta separato: in Fase 5
il router /api/chat accetterà ``conversation_id`` opzionale e farà
append automatico (user msg + assistant msg + sources). Qui esponiamo
solo CRUD raw — utile a frontend per import/export, sync multi-tab,
e debug.

Auth
====

Tutte le rotte richiedono ``require_user``. Tenant ricavato dal
contextvar (popolato da TenantMiddleware) — RLS Postgres garantisce
che query non vedano dati di altri tenant anche con bug applicativi.

Authorization granulare
=======================

Lookup conv prima di qualsiasi op write/read: se ``conversation.user_id
!= current_user.id`` → 404 (non 403, evita oracle che rivela esistenza).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from llm_wiki.auth.dependencies import require_permission, require_user
from llm_wiki.auth.permissions import Permission
from llm_wiki.db.conversations import (
    append_message,
    create_conversation,
    delete_conversation,
    delete_messages_from,
    get_conversation,
    list_conversations,
    list_messages,
    update_conversation,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# --- models ----------------------------------------------------------------


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="Nuova conversazione", max_length=200)


class ConversationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    pinned: bool | None = None
    title_locked: bool | None = None


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=20000)
    sources: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


# --- helpers ---------------------------------------------------------------


def _ensure_owner(conversation_id: str, user: dict[str, Any]) -> dict[str, Any]:
    conv = get_conversation(conversation_id)
    if not conv or conv["user_id"] != user["id"]:
        # 404 non 403 — non leakare l'esistenza di conv di altri.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversazione non trovata",
        )
    return conv


# --- conversations ---------------------------------------------------------


@router.get("")
def list_my_conversations(user: dict[str, Any] = Depends(require_user)) -> dict:
    items = list_conversations(user_id=user["id"])
    return {"count": len(items), "conversations": items}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_my_conversation(
    body: ConversationCreate,
    user: dict[str, Any] = Depends(require_permission(Permission.CONVERSATION_WRITE)),
) -> dict[str, Any]:
    return create_conversation(user_id=user["id"], title=body.title)


@router.get("/{conversation_id}")
def get_my_conversation(
    conversation_id: str,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    return _ensure_owner(conversation_id, user)


@router.patch("/{conversation_id}")
def update_my_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    user: dict[str, Any] = Depends(require_permission(Permission.CONVERSATION_WRITE)),
) -> dict[str, Any]:
    _ensure_owner(conversation_id, user)
    updated = update_conversation(
        conversation_id,
        title=body.title,
        pinned=body.pinned,
        title_locked=body.title_locked,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="conversazione non trovata")
    return updated


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_my_conversation(
    conversation_id: str,
    user: dict[str, Any] = Depends(require_permission(Permission.CONVERSATION_DELETE)),
) -> None:
    _ensure_owner(conversation_id, user)
    delete_conversation(conversation_id)


# --- messages --------------------------------------------------------------


@router.get("/{conversation_id}/messages")
def list_conversation_messages(
    conversation_id: str,
    limit: int = 200,
    offset: int = 0,
    user: dict[str, Any] = Depends(require_user),
) -> dict:
    _ensure_owner(conversation_id, user)
    items = list_messages(conversation_id=conversation_id, limit=limit, offset=offset)
    return {"count": len(items), "messages": items}


@router.post(
    "/{conversation_id}/messages",
    status_code=status.HTTP_201_CREATED,
)
def create_conversation_message(
    conversation_id: str,
    body: MessageCreate,
    user: dict[str, Any] = Depends(require_permission(Permission.CONVERSATION_WRITE)),
) -> dict[str, Any]:
    """Append turno raw (no LLM call). Path normale chat-streaming
    in Fase 5 farà append automatico — qui per import/sync/manual edit."""
    _ensure_owner(conversation_id, user)
    return append_message(
        conversation_id=conversation_id,
        role=body.role,
        content=body.content,
        sources=body.sources,
        metadata=body.metadata,
    )


@router.delete(
    "/{conversation_id}/messages/{message_id}/and_after",
    status_code=status.HTTP_200_OK,
)
def truncate_messages_from(
    conversation_id: str,
    message_id: str,
    user: dict[str, Any] = Depends(require_permission(Permission.CONVERSATION_DELETE)),
) -> dict[str, int]:
    """Tronca: cancella ``message_id`` e tutti i successivi.

    Usato da `useChat.regenerate` / `editAndResend`: il client tronca la
    cronologia locale e poi chiama questo per allineare il server, così
    il prossimo `latest_turns` non re-inietta i turni rimossi nel
    context RAG.
    """
    _ensure_owner(conversation_id, user)
    deleted = delete_messages_from(
        conversation_id=conversation_id,
        from_message_id=message_id,
    )
    return {"deleted": deleted}
