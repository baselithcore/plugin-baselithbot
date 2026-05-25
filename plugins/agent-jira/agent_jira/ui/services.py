"""Runtime objects shared across UI helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from agent_jira.chat import ChatService, resolve_chat_service

_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = resolve_chat_service()
    return _chat_service


def __getattr__(name: str):
    if name == "chat_service":
        return get_chat_service()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    chat_service: ChatService


__all__ = ["chat_service", "get_chat_service"]
