"""AI layer — talk to your knowledge.

The differentiator of a second brain hosted *inside* BaselithCore: the host
already ships an LLM client, embeddings and a graph, so AI-over-your-notes is
native, not a bolt-on. This module turns the passive vault into a thinking
partner:

* **RAG chat** — retrieve the most relevant notes (keyword/semantic), enrich
  with their graph neighbors (linked notes carry context the query misses),
  build a grounded prompt and stream a cited answer.
* **Inline actions** — summarize / expand / improve a note, or have the model
  propose tags and related links.

Everything degrades gracefully: if no LLM provider is reachable the rest of the
plugin keeps working and the UI shows a clear "not configured" state. All host
imports are lazy so a missing optional dependency never breaks plugin import.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from core.observability.logging import get_logger

from . import memory
from .chat_models import ChatMessage, ChatSource, Conversation
from .index_state import BrainIndex

logger = get_logger(__name__)

#: How many top search hits seed retrieval, and the per-note context budget.
_SEED_HITS = 4
_MAX_CONTEXT_NOTES = 8
_PER_NOTE_CHARS = 900

_SYSTEM = (
    "You are the user's second brain — a helpful thinking and writing partner. "
    "The user's notes are provided as your primary knowledge; lean on them and "
    "cite them inline as [n] (matching the context markers) whenever you draw on "
    "them. You can ALSO help with open-ended tasks — writing posts, drafting, "
    "brainstorming, reasoning — using the notes as grounding and inspiration even "
    "when they don't contain a direct answer. Never refuse a creative or "
    "generative request just because the notes lack the exact information; only "
    "flag missing information for purely factual questions the notes cannot "
    "support. "
    "IMPORTANT: always reply in the SAME LANGUAGE as the user's latest message. "
    "Be concise and use Markdown."
)

_ACTIONS = {
    "summarize": "Summarize the note below in 3-5 tight bullet points. Markdown only.",
    "expand": "Expand the note below with more depth and structure, preserving its "
    "meaning and voice. Return Markdown only.",
    "improve": "Improve the clarity, grammar and structure of the note below. "
    "Return only the rewritten Markdown, no commentary.",
}


class AIService:
    """RAG chat + inline transforms over the note vault."""

    def __init__(self, index: BrainIndex) -> None:
        self._index = index

    # ---- provider status -------------------------------------------------
    def status(self) -> dict[str, Any]:
        """Report whether an LLM provider looks usable (best-effort)."""
        try:
            from core.config import get_llm_config  # noqa: PLC0415

            cfg = get_llm_config()
            provider = getattr(cfg, "provider", "ollama")
            has_key = bool(getattr(cfg, "api_key", None))
            configured = provider == "ollama" or has_key
            return {
                "configured": configured,
                "provider": provider,
                "model": getattr(cfg, "model", None),
            }
        except Exception as exc:  # noqa: BLE001
            logger.info("BaselithBrain AI status unavailable: %s", exc)
            return {"configured": False, "provider": None, "model": None}

    # ---- retrieval (graph-aware) ----------------------------------------
    async def retrieve(self, question: str) -> list[tuple[str, str, str]]:
        """Return ``(id, title, body)`` for notes relevant to ``question``.

        Seeds from search, then pulls 1-hop graph neighbors of the top hits —
        linked notes often hold context the raw query never matches. This is
        what makes the answer use the *web* of knowledge, not just one note.
        """
        hits = await self._index.search.search(question, top_k=_SEED_HITS * 2)
        ordered: list[str] = []
        seen: set[str] = set()

        def add(nid: str) -> None:
            if nid not in seen and self._index.notes.exists(nid):
                seen.add(nid)
                ordered.append(nid)

        for hit in hits[:_SEED_HITS]:
            add(hit.id)
        for hit in hits[:_SEED_HITS]:
            for nb in self._index.graph.forward_links(
                hit.id
            ) + self._index.graph.backlinks(hit.id):
                add(nb)
        for hit in hits[_SEED_HITS:]:
            add(hit.id)

        out: list[tuple[str, str, str]] = []
        for nid in ordered[:_MAX_CONTEXT_NOTES]:
            note = self._index.notes.get(nid)
            out.append((nid, note.title, note.body[:_PER_NOTE_CHARS]))
        return out

    def _context(self, notes: list[tuple[str, str, str]]) -> str:
        blocks = [
            f"[{i}] {title}\n{body}"
            for i, (_id, title, body) in enumerate(notes, start=1)
        ]
        return "\n\n".join(blocks) if blocks else "(no relevant notes found)"

    def _build_prompt(self, question: str, context: str, history: str) -> str:
        parts: list[str] = []
        if history.strip():
            parts.append(f"# Conversation so far\n{history}")
        parts.append(f"# Notes from the user's vault (cite as [n])\n{context}")
        parts.append(f"# User request\n{question}")
        return "\n\n".join(parts)

    # ---- chat (streaming, cited, memory-aware) --------------------------
    async def chat_stream(
        self, conv: Conversation, question: str
    ) -> AsyncIterator[str]:
        """Stream a cited answer for ``question`` within thread ``conv``.

        Yields NDJSON events: ``{type:meta}`` (thread id/title) first, then
        ``{type:token}`` … and finally ``{type:sources}``. The full exchange
        (question + answer) is persisted to the thread, and rolling memory is
        maintained, so the next turn stays coherent without an unbounded prompt.

        On any LLM failure, emits a single ``{type:error}`` event so the UI can
        show a friendly message instead of hanging.
        """
        yield (
            json.dumps(
                {"type": "meta", "conversation_id": conv.id, "title": conv.title}
            )
            + "\n"
        )

        try:
            from core.services.llm.service import get_llm_service  # noqa: PLC0415

            llm = get_llm_service()
            # History-aware retrieval: rewrite follow-ups into a standalone query.
            _older, recent = memory.split_window(conv.messages)
            search_query = await memory.contextualize(llm, question, recent)
            notes = await self.retrieve(search_query)
            sources = self._sources(notes)

            # Build our own prompt — core's build_prompt injects a strict
            # "use only the context" RAG instruction that makes the model refuse
            # generative requests (write a post, brainstorm). The behavior we
            # want is defined entirely by _SYSTEM.
            history = memory.render_history(conv.summary, recent)
            context_text = self._context(notes)
            prompt = self._build_prompt(question, context_text, history)

            answer: list[str] = []
            async for chunk in llm.generate_response_stream(
                prompt=prompt, system_prompt=_SYSTEM
            ):
                if chunk:
                    answer.append(chunk)
                    yield json.dumps({"type": "token", "text": chunk}) + "\n"
            yield json.dumps({"type": "sources", "sources": sources}) + "\n"

            full_answer = "".join(answer)
            await self._persist_turn(conv, question, full_answer, sources, llm)

            # Off the critical path: score how grounded the answer is in the
            # cited notes and emit a trailing trust badge. Best-effort — any
            # failure simply omits the event.
            async for event in self._groundedness_event(
                llm, question, context_text, full_answer, notes
            ):
                yield event
        except Exception as exc:  # noqa: BLE001
            logger.warning("BaselithBrain chat failed: %s", exc)
            yield (
                json.dumps({"type": "error", "message": f"AI unavailable: {exc}"})
                + "\n"
            )

    async def _groundedness_event(
        self,
        llm: Any,
        question: str,
        context_text: str,
        answer: str,
        notes: list[tuple[str, str, str]],
    ) -> AsyncIterator[str]:
        """Yield a single ``{type:groundedness}`` NDJSON event, or nothing.

        Gated on config + the presence of cited notes (faithfulness is
        meaningless for a no-context generative reply).
        """
        from .config_proxy import get_settings  # noqa: PLC0415
        from .groundedness import score_groundedness  # noqa: PLC0415

        if not notes or not get_settings().groundedness_enabled:
            return
        verdict = await score_groundedness(llm, question, context_text, answer)
        if verdict is not None:
            yield json.dumps({"type": "groundedness", **verdict}) + "\n"

    def _sources(self, notes: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
        return [
            {"n": i, "id": nid, "title": t, "snippet": " ".join(body.split())[:240]}
            for i, (nid, t, body) in enumerate(notes, 1)
        ]

    async def _persist_turn(
        self,
        conv: Conversation,
        question: str,
        answer: str,
        sources: list[dict[str, Any]],
        llm: Any,
    ) -> None:
        """Append the exchange and fold any aged-out turns into the summary."""
        convs = self._index.conversations
        convs.append(conv.id, ChatMessage(role="user", content=question))
        convs.append(
            conv.id,
            ChatMessage(
                role="assistant",
                content=answer,
                sources=[ChatSource(**s) for s in sources],
            ),
        )
        fresh = convs.get(conv.id)
        if fresh is None:
            return
        target = max(0, len(fresh.messages) - memory.WINDOW_MESSAGES)
        if target > fresh.summarized_count:
            new_older = fresh.messages[fresh.summarized_count : target]
            summary = await memory.summarize(llm, fresh.summary, new_older)
            convs.set_summary(conv.id, summary, target)

    # ---- inline transforms ----------------------------------------------
    async def transform(
        self, action: str, text: str, title: str = ""
    ) -> dict[str, Any]:
        """Run an inline AI action on note text. Returns a typed result dict."""
        from core.services.llm.service import get_llm_service  # noqa: PLC0415

        llm = get_llm_service()
        header = f"# {title}\n\n" if title else ""

        if action in _ACTIONS:
            out = await llm.generate_response(
                prompt=f"{_ACTIONS[action]}\n\n---\n{header}{text}",
                system_prompt=(
                    "You are a precise editing assistant. Always respond in the "
                    "same language as the note content."
                ),
            )
            return {"action": action, "result": out.strip()}

        if action == "autotag":
            raw = await llm.generate_response(
                prompt=(
                    'Return JSON {"tags": [..]} with 3-6 lowercase, hyphenated '
                    f"topical tags for this note.\n\n{header}{text}"
                ),
                json=True,
            )
            return {"action": action, "tags": _parse_list(raw, "tags")}

        if action == "suggest_links":
            raw = await llm.generate_response(
                prompt=(
                    'Return JSON {"suggestions": [..]} with up to 6 short note '
                    "titles this note should link to or that are worth creating.\n\n"
                    f"{header}{text}"
                ),
                json=True,
            )
            return {"action": action, "suggestions": _parse_list(raw, "suggestions")}

        return {"action": action, "error": "unknown action"}


def _parse_list(raw: str, key: str) -> list[str]:
    """Best-effort extract a string list from a model JSON reply."""
    try:
        data = json.loads(raw)
        items = data.get(key, []) if isinstance(data, dict) else []
        return [str(x).strip() for x in items if str(x).strip()][:8]
    except (json.JSONDecodeError, TypeError, AttributeError):
        return []
