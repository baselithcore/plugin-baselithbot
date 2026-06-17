"""ConversationService — persistence for chat threads.

Each conversation is a single JSON file ``.brain/chats/<id>.json`` beside the
notes. The hidden ``.brain`` dir is never globbed as a note, so the vault stays a
clean pile of Markdown while chat history lives alongside it (portable, no DB).

This layer owns *persistence only*: windowing, summarization and query rewriting
are the memory manager's job (:mod:`memory`).
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from .chat_models import (
    ChatMessage,
    Conversation,
    ConversationCreate,
    ConversationMeta,
)
from .workspaces import DEFAULT_WORKSPACE_ID

_ID_RE_OK = set("0123456789abcdef")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ConversationService:
    """CRUD over per-thread JSON files (one directory, no DB)."""

    def __init__(self, vault_root: Path) -> None:
        self._dir = vault_root / ".brain" / "chats"

    # ---- path helpers ----------------------------------------------------
    def _path(self, conv_id: str) -> Path:
        """Resolve a thread id to a confined file path (hex ids only)."""
        if not conv_id or any(c not in _ID_RE_OK for c in conv_id):
            raise ValueError(f"invalid conversation id: {conv_id!r}")
        return self._dir / f"{conv_id}.json"

    # ---- persistence -----------------------------------------------------
    def _read(self, path: Path) -> Conversation | None:
        try:
            return Conversation(**json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError, ValueError, TypeError):
            return None

    def _write(self, conv: Conversation) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path(conv.id).write_text(conv.model_dump_json(indent=2), encoding="utf-8")

    # ---- reads -----------------------------------------------------------
    def list(self, workspace: str | None = None) -> list[ConversationMeta]:
        """Thread metas (newest first), optionally scoped to a workspace."""
        if not self._dir.exists():
            return []
        out: list[ConversationMeta] = []
        for path in self._dir.glob("*.json"):
            conv = self._read(path)
            if conv is None:
                continue
            if workspace is not None and conv.workspace != workspace:
                continue
            out.append(
                ConversationMeta(
                    id=conv.id,
                    title=conv.title,
                    workspace=conv.workspace,
                    created=conv.created,
                    updated=conv.updated,
                    message_count=len(conv.messages),
                )
            )
        out.sort(key=lambda c: c.updated or "", reverse=True)
        return out

    def get(self, conv_id: str) -> Conversation | None:
        path = self._path(conv_id)
        return self._read(path) if path.exists() else None

    # ---- writes ----------------------------------------------------------
    def create(self, payload: ConversationCreate) -> Conversation:
        ts = _now()
        conv = Conversation(
            id=secrets.token_hex(8),
            title=(payload.title or "New chat").strip()[:80] or "New chat",
            workspace=payload.workspace or DEFAULT_WORKSPACE_ID,
            created=ts,
            updated=ts,
        )
        self._write(conv)
        return conv

    def append(self, conv_id: str, message: ChatMessage) -> Conversation | None:
        """Append a turn and bump ``updated`` (no-op if the thread is gone)."""
        conv = self.get(conv_id)
        if conv is None:
            return None
        message.ts = message.ts or _now()
        conv.messages.append(message)
        conv.updated = _now()
        self._write(conv)
        return conv

    def set_summary(self, conv_id: str, summary: str, summarized_count: int) -> None:
        """Persist rolling memory state after the summarizer folds aged turns."""
        conv = self.get(conv_id)
        if conv is None:
            return
        conv.summary = summary
        conv.summarized_count = summarized_count
        self._write(conv)

    def rename(self, conv_id: str, title: str) -> Conversation | None:
        conv = self.get(conv_id)
        if conv is None:
            return None
        conv.title = (title or conv.title).strip()[:80] or conv.title
        conv.updated = _now()
        self._write(conv)
        return conv

    def clear(self, conv_id: str) -> Conversation | None:
        """Wipe a thread's turns and memory, keeping the thread itself."""
        conv = self.get(conv_id)
        if conv is None:
            return None
        conv.messages = []
        conv.summary = ""
        conv.summarized_count = 0
        conv.updated = _now()
        self._write(conv)
        return conv

    def delete(self, conv_id: str) -> bool:
        path = self._path(conv_id)
        if path.exists():
            path.unlink()
            return True
        return False
