from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .dependencies import ChatDependencyConfig
from .factory import (
    create_chat_service_from_config,
    load_chat_dependency_config,
    resolve_chat_service,
)
from .service import ChatService

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


__all__ = [
    "ChatService",
    "chat_service",
    "get_chat_service",
    "resolve_chat_service",
    "create_chat_service_from_config",
    "load_chat_dependency_config",
    "ChatDependencyConfig",
]
