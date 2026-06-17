"""Conversation endpoints — manage persisted chat threads.

CRUD over the thread store: list (optionally workspace-scoped), open a full
thread (with its turns), rename, clear and delete. The chat *turn* itself is
streamed by :mod:`ai_router`; this router owns thread lifecycle only.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..chat_models import (
    Conversation,
    ConversationCreate,
    ConversationMeta,
    ConversationUpdate,
)
from ..index_state import get_index

router = APIRouter(prefix="/api/ai/conversations", tags=["ai"])


@router.get("")
async def list_conversations(workspace: str | None = None) -> list[ConversationMeta]:
    return get_index().conversations.list(workspace)


@router.post("")
async def create_conversation(payload: ConversationCreate) -> Conversation:
    return get_index().conversations.create(payload)


@router.get("/{conv_id}")
async def get_conversation(conv_id: str) -> Conversation:
    conv = get_index().conversations.get(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conv


@router.patch("/{conv_id}")
async def rename_conversation(conv_id: str, patch: ConversationUpdate) -> Conversation:
    if not patch.title:
        raise HTTPException(status_code=400, detail="title required")
    conv = get_index().conversations.rename(conv_id, patch.title)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conv


@router.post("/{conv_id}/clear")
async def clear_conversation(conv_id: str) -> Conversation:
    conv = get_index().conversations.clear(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conv


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str) -> dict[str, bool]:
    return {"deleted": get_index().conversations.delete(conv_id)}
