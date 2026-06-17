"""Conversational memory — summary-buffer window + history-aware retrieval.

Two best-practice ingredients sit between a raw chat log and a good RAG answer:

* **Summary-buffer memory.** Keeping every past turn in the prompt is wasteful
  and eventually overflows the context. Instead we keep the last few turns
  *verbatim* and fold everything older into a rolling natural-language summary.
  The prompt always carries ``summary + recent turns`` — bounded, yet coherent.

* **History-aware retrieval (query contextualization).** A follow-up like "expand
  on that" or "why?" retrieves nothing on its own. Before searching the vault we
  rewrite the latest question into a standalone query using recent context, so
  retrieval keys off what the user *means*, not just what they typed.

Every LLM call here degrades gracefully: on any failure we fall back to the raw
question / previous summary, so memory never breaks the chat.
"""

from __future__ import annotations

from core.observability.logging import get_logger

from .chat_models import ChatMessage

logger = get_logger(__name__)

#: Turns kept verbatim in the prompt; older turns live only in the summary.
WINDOW_MESSAGES = 6
#: Skip contextualization for short, already-standalone questions.
_MIN_CONTEXTUALIZE_LEN = 12

_CONTEXTUALIZE_SYSTEM = (
    "You rewrite a user's latest message into a single, self-contained search "
    "query for a note database, resolving pronouns and ellipsis from the chat "
    "history. Output ONLY the rewritten query — no quotes, no preamble. If the "
    "message is already self-contained, echo it unchanged. Keep the user's "
    "language."
)

_SUMMARIZE_SYSTEM = (
    "You maintain a running summary of a conversation between a user and their "
    "second-brain assistant. Given the summary so far and the new turns, return "
    "an updated summary that preserves durable facts, decisions, names and open "
    "threads. Be terse (a few sentences). Output only the summary, same language "
    "as the conversation."
)


def split_window(
    messages: list[ChatMessage],
) -> tuple[list[ChatMessage], list[ChatMessage]]:
    """Partition into ``(older, recent)`` — recent is the verbatim window."""
    if len(messages) <= WINDOW_MESSAGES:
        return [], messages
    return messages[:-WINDOW_MESSAGES], messages[-WINDOW_MESSAGES:]


def _render_turns(messages: list[ChatMessage]) -> str:
    lines = [
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.content.strip()}"
        for m in messages
        if m.content.strip()
    ]
    return "\n".join(lines)


def render_history(summary: str, recent: list[ChatMessage]) -> str:
    """Build the history block injected into the answer prompt."""
    parts: list[str] = []
    if summary.strip():
        parts.append(f"## Earlier in this conversation (summary)\n{summary.strip()}")
    turns = _render_turns(recent)
    if turns:
        parts.append(f"## Recent turns\n{turns}")
    return "\n\n".join(parts)


async def contextualize(llm, question: str, recent: list[ChatMessage]) -> str:
    """Rewrite ``question`` into a standalone search query using ``recent``.

    Falls back to the raw question when there is no usable history, the question
    is already long/standalone, or the LLM call fails.
    """
    turns = _render_turns(recent)
    if not turns or len(question.strip()) >= 80:
        return question
    if len(question.strip()) < _MIN_CONTEXTUALIZE_LEN and "?" not in question:
        # Very short follow-ups ("why?", "more") need context the most.
        pass
    try:
        rewritten = await llm.generate_response(
            prompt=f"# Chat history\n{turns}\n\n# Latest message\n{question}",
            system_prompt=_CONTEXTUALIZE_SYSTEM,
        )
        rewritten = rewritten.strip().strip('"').strip()
        return rewritten or question
    except Exception as exc:  # noqa: BLE001
        logger.info("BaselithBrain contextualize fell back: %s", exc)
        return question


async def summarize(llm, prior_summary: str, new_older: list[ChatMessage]) -> str:
    """Fold newly aged-out turns into the rolling summary (best-effort)."""
    turns = _render_turns(new_older)
    if not turns:
        return prior_summary
    prior = prior_summary.strip() or "(none yet)"
    try:
        out = await llm.generate_response(
            prompt=f"# Summary so far\n{prior}\n\n# New turns to fold in\n{turns}",
            system_prompt=_SUMMARIZE_SYSTEM,
        )
        return out.strip() or prior_summary
    except Exception as exc:  # noqa: BLE001
        logger.info("BaselithBrain summarize skipped: %s", exc)
        return prior_summary


def derive_title(question: str) -> str:
    """A short thread title from the opening question."""
    text = " ".join(question.split())
    return (text[:60].rstrip() + "…") if len(text) > 60 else (text or "New chat")
