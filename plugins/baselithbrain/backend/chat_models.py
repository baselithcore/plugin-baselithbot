"""DTOs for conversational memory — chat threads over the vault.

A *conversation* is a persisted, multi-turn chat session with the second-brain
assistant. Unlike notes (Markdown files), conversations are bookkeeping state, so
they live as JSON under ``.brain/chats/`` and are modeled here as plain Pydantic
objects — the wire contract between backend and SPA.

The memory model is *summary-buffer*: the last few turns are kept verbatim while
older turns are folded into a rolling ``summary`` (see :mod:`memory`). Both the
verbatim window and the summary travel back to the LLM on every turn, so a long
thread stays coherent without an unbounded prompt.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatSource(BaseModel):
    """A cited note backing an assistant turn (the ``[n]`` markers)."""

    n: int
    id: str
    title: str
    snippet: str = ""


class ChatMessage(BaseModel):
    """One turn in a conversation."""

    role: str  # "user" | "assistant"
    content: str
    #: Citations attached to an assistant turn (empty for user turns).
    sources: list[ChatSource] = Field(default_factory=list)
    #: UTC ISO-8601 timestamp of when the turn was recorded.
    ts: str | None = None


class ConversationMeta(BaseModel):
    """Lightweight thread descriptor (history list / switcher)."""

    id: str
    title: str
    workspace: str = "default"
    created: str | None = None
    updated: str | None = None
    #: Number of turns — cheap signal for the UI without loading messages.
    message_count: int = 0


class Conversation(ConversationMeta):
    """A full thread: metadata + every turn + rolling memory state."""

    messages: list[ChatMessage] = Field(default_factory=list)
    #: Rolling natural-language summary of turns that fell out of the verbatim
    #: window. Empty until the thread grows past the window.
    summary: str = ""
    #: How many leading messages are already captured by ``summary`` — lets the
    #: summarizer fold only the *newly* aged-out turns (bounded LLM cost).
    summarized_count: int = 0


class ConversationCreate(BaseModel):
    """Payload to open a new thread."""

    title: str = "New chat"
    workspace: str | None = None


class ConversationUpdate(BaseModel):
    """Partial update (rename only, for now)."""

    title: str | None = None


class ChatRequest(BaseModel):
    """A chat turn. ``conversation_id`` is optional — omit it to start a thread.

    History is no longer sent by the client: the server owns conversational
    memory, so it loads the thread, builds the windowed history + summary, and
    persists both the question and the streamed answer.
    """

    question: str
    conversation_id: str | None = None
    workspace: str | None = None
