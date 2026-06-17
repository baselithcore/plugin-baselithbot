"""Deep-research mode — multi-hop reasoning over the vault.

Where :mod:`ai_service` chat does a single grounded retrieval+answer, this runs
the host's ReAct agent (``core.reasoning.ReActAgent``) with the vault wired in as
tools. The agent *reasons*: it searches, reads notes, follows links across
several hops and synthesises a cited report — the kind of cross-note research a
flat RAG turn can't do.

The agent loop is bounded by ``research_max_iterations`` (a LoopBudget-style hard
cap on cost/latency). Everything is best-effort: if the reasoning stack or LLM is
unavailable the endpoint surfaces a clean error and the rest of the plugin is
untouched.
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger

from .config_proxy import get_settings
from .index_state import BrainIndex

logger = get_logger(__name__)

#: How many hits a single ``search_notes`` call surfaces to the agent.
_SEARCH_HITS = 6
#: Per-note body budget when the agent reads a note (keeps the trace bounded).
_READ_CHARS = 1500

_SYSTEM_EXTRA = (
    "You are researching the user's personal note vault. Prefer evidence from "
    "their notes; follow links between notes to connect ideas across the graph. "
    "Cite note ids inline as [id] when you use them. Answer in the user's "
    "language, in Markdown. If the notes don't cover something, say so plainly."
)


class ResearchService:
    """Runs a bounded ReAct loop with vault-backed tools."""

    def __init__(self, index: BrainIndex) -> None:
        self._index = index

    def _build_tools(self, cited: set[str]) -> list[Any]:
        """Vault tools for the agent; ``cited`` collects note ids actually read."""
        from core.reasoning import ToolDefinition  # noqa: PLC0415

        idx = self._index

        async def search_notes(query: str) -> str:
            hits = await idx.search.search(query, top_k=_SEARCH_HITS)
            if not hits:
                return "No matching notes."
            return "\n".join(f"[{h.id}] {h.title} — {h.snippet}" for h in hits)

        async def read_note(note_id: str) -> str:
            note_id = note_id.strip()
            if not idx.notes.exists(note_id):
                return f"No note with id '{note_id}'."
            note = idx.notes.get(note_id)
            cited.add(note_id)
            return f"# {note.title}\n{note.body[:_READ_CHARS]}"

        async def list_links(note_id: str) -> str:
            note_id = note_id.strip()
            if not idx.notes.exists(note_id):
                return f"No note with id '{note_id}'."
            fwd = idx.graph.forward_links(note_id)
            back = idx.graph.backlinks(note_id)
            if not fwd and not back:
                return f"Note '{note_id}' has no links."
            return f"forward links: {fwd}\nbacklinks: {back}"

        return [
            ToolDefinition(
                "search_notes",
                search_notes,
                "Search the note vault for a query. Returns up to "
                f"{_SEARCH_HITS} hits as '[id] title — snippet' lines.",
            ),
            ToolDefinition(
                "read_note",
                read_note,
                "Read a note's full text by its id (from a search result).",
            ),
            ToolDefinition(
                "list_links",
                list_links,
                "List a note's forward links and backlinks by id — use it to "
                "hop across related notes.",
            ),
        ]

    async def research(self, question: str) -> dict[str, Any]:
        """Run the bounded ReAct loop and return a cited report."""
        from core.reasoning import ReActAgent  # noqa: PLC0415

        max_iter = get_settings().research_max_iterations
        cited: set[str] = set()
        agent = ReActAgent(
            tools=self._build_tools(cited),
            max_iterations=max_iter,
            system_prompt_extra=_SYSTEM_EXTRA,
        )
        result = await agent.run(question)

        sources = [
            {"id": nid, "title": self._index.notes.get_meta(nid).title}
            for nid in cited
            if self._index.notes.exists(nid)
        ]
        trace = [
            {
                "type": step.step_type.value,
                "content": step.content,
                "tool": step.tool_name,
            }
            for step in result.trace
        ]
        return {
            "answer": result.final_answer,
            "sources": sources,
            "trace": trace,
            "iterations": result.iterations_used,
            "hit_limit": result.hit_limit,
        }
