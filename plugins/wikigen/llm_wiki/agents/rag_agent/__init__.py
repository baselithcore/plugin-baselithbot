"""RAG agent: retrieve (wiki + memorie) → render prompt → generate.

Domain-agnostic. Tutti i prompt vivono come Jinja2 templates sotto
``domains/<APP_DOMAIN>/prompts/`` e sono risolti via
:func:`llm_wiki.domain.prompts.render`.

Templates richiesti dal Domain Pack:

- ``system.j2``  — system prompt (no inputs).
- ``user.j2``    — user message; vars: ``context``, ``question``,
  ``history`` (str opzionale), ``memories`` (str opzionale).
- ``no_hits.j2`` — fallback retrieval vuoto.

Multi-tenancy (Fase 5)
======================

Wiki SHARED: il retrieval Qdrant non filtra per tenant — tutti gli
utenti vedono lo stesso corpus. RAG personale: aggiunto retrieval su
``memories`` Postgres+pgvector filtrato per ``user_id`` (RLS-isolated
per tenant). I due retrieval vengono mergiati nel context con header
distinti (`### Memoria personale` vs `### Wiki`).

History: se ``conversation_id`` è passato, l'agent legge
``latest_turns`` dalla conversation e li include nel prompt come
chronological dialog. L'append automatico del turno user + assistant
+ sources è responsabilità del **router** (`api/routers/chat.py`),
NON di questo modulo — separation of concerns: l'agent non sa di HTTP.

Modular layout (>500 LOC budget):
- :mod:`._result`    — :class:`RAGResult` dataclass
- :mod:`._loaders`   — memories + history retrieval (DB I/O, degraded-safe)
- :mod:`._citations` — validate + repair-loop helpers
- :mod:`._synth`     — sync + stream synthesis paths
- This module        — :class:`RAGAgent` orchestrator
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from llm_wiki.agents.rag_agent._loaders import load_history, load_memories
from llm_wiki.agents.rag_agent._query_rewriter import CondenseResult, condense_question
from llm_wiki.agents.rag_agent._result import RAGResult
from llm_wiki.agents.rag_agent._synth import (
    stream_synthesis_from_hits,
    synthesize_from_hits,
)
from llm_wiki.config import RETRIEVAL_TOP_K

# Re-exposed at package level so tests can ``monkeypatch.setattr(
# "llm_wiki.agents.rag_agent.generate", …)`` and the synthesis submodule
# (which dispatches via this namespace) picks up the patched callable.
from llm_wiki.domain.prompts import render  # noqa: F401 — re-exported for tests
from llm_wiki.utils import llm as _llm_module
from llm_wiki.vectorstore.core import search

# Re-export ``generate`` / ``stream`` from ``llm_wiki.utils.llm`` at this
# package's namespace so tests can ``monkeypatch.setattr(
# "llm_wiki.agents.rag_agent.generate", …)`` and the synthesis submodule
# (which dispatches via this namespace) picks up the patched callable.
# Assigned by attribute access (not ``from … import``) to avoid ruff
# F811 when the :class:`RAGAgent` method ``stream`` shares the name.
generate = _llm_module.generate
stream = _llm_module.stream

logger = logging.getLogger(__name__)

# Quanti turni precedenti (user+assistant pair) iniettare nel prompt.
# Tradeoff: troppo basso = perde contesto conversazione; troppo alto =
# context window si riempie + risposta lenta. 4 = sweet spot per
# llama3.1:8b @ 8k ctx.
_HISTORY_DEFAULT_TURNS = 4

# Quante memorie utente recuperare. Le memorie sono dichiarate
# manualmente dall'utente (basso volume → top-K piccolo è sufficiente).
_MEMORIES_DEFAULT_TOP_K = 3


class RAGAgent:
    """Stateless. Tutto lo stato (history, memorie) è caricato per
    chiamata da DB — l'agent non mantiene cache fra invocazioni."""

    def __init__(
        self,
        *,
        use_graph: bool = False,
        user_id: str | None = None,
        conversation_id: str | None = None,
        history_turns: int = _HISTORY_DEFAULT_TURNS,
        memories_top_k: int = _MEMORIES_DEFAULT_TOP_K,
    ) -> None:
        self.use_graph = use_graph
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.history_turns = max(0, history_turns)
        self.memories_top_k = max(0, memories_top_k)

    # --- public API --------------------------------------------------------

    def answer(self, question: str, *, limit: int = RETRIEVAL_TOP_K) -> RAGResult:
        history = self._load_history()
        condensed = self._condense(question, history)
        hits = search(condensed.query, limit=limit, expand_with_graph=self.use_graph)
        return self._synthesize_from_hits(question, hits, prefetched_history=history)

    def stream(self, question: str, *, limit: int = RETRIEVAL_TOP_K) -> Iterator[dict[str, Any]]:
        """Event stream: ``agent`` → ``step*`` → ``query_rewrite?`` →
        ``hits`` → ``memories`` → ``agent`` → ``step`` → ``token*`` →
        ``sources`` → ``done``."""
        # History caricata UNA volta — riusata per condense + synthesis
        # (evita doppio DB roundtrip).
        history = self._load_history()

        yield {"type": "agent", "content": "Retriever"}
        if history:
            yield {
                "type": "step",
                "content": f"Memoria conversazione: {len(history)} turni precedenti",
            }

        condensed = self._condense(question, history)
        if condensed.rewritten:
            yield {
                "type": "step",
                "content": "Riformulata in query autonoma per il retrieval (memoria conversazionale)",
            }
            yield {
                "type": "query_rewrite",
                "original": condensed.original,
                "rewritten": condensed.query,
            }

        yield {"type": "step", "content": "Hybrid retrieval (dense + sparse + ColBERT)…"}

        hits = search(condensed.query, limit=limit, expand_with_graph=self.use_graph)
        yield {"type": "step", "content": f"Trovati {len(hits)} chunk rilevanti"}
        yield {"type": "hits", "count": len(hits)}

        yield from self._stream_synthesis_from_hits(question, hits, prefetched_history=history)

    # --- hooks for subclasses (e.g. AgenticRAGAgent) -----------------------

    def _synthesize_from_hits(
        self,
        question: str,
        hits: list[dict[str, Any]],
        *,
        prefetched_history: list[dict[str, Any]] | None = None,
    ) -> RAGResult:
        """Sync synthesis path. Estratto per consentire ad agent agentic
        (:class:`AgenticRAGAgent`) di accumulare hit da più ricerche
        consecutive e poi invocare la sintesi una sola volta.

        ``prefetched_history``: se passata, sostituisce il load DB
        interno (evita roundtrip doppio quando il chiamante ha già
        caricato history per condense / planning)."""
        return synthesize_from_hits(self, question, hits, prefetched_history=prefetched_history)

    def _stream_synthesis_from_hits(
        self,
        question: str,
        hits: list[dict[str, Any]],
        *,
        prefetched_history: list[dict[str, Any]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Stream synthesis path. Permette ad agent agentic di
        accumulare hits da più ricerche e poi delegare la sintesi
        streaming a questo helper. ``prefetched_history`` come in
        :meth:`_synthesize_from_hits`."""
        yield from stream_synthesis_from_hits(
            self, question, hits, prefetched_history=prefetched_history
        )

    def _condense(self, question: str, history: list[dict[str, Any]]) -> CondenseResult:
        """History-aware query rewriting (conversational memory).

        Estratto come metodo per permettere a sottoclassi (es.
        :class:`AgenticRAGAgent`) di override / disabilitare e per
        rendere il path mockabile nei test."""
        return condense_question(question, history)

    # --- internals ---------------------------------------------------------

    def _build_messages(
        self,
        *,
        question: str,
        context: str,
        memories_block: str,
        history_block: str,
    ) -> list[dict[str, str]]:
        """Costruisce messaggi LLM. Tenta passaggio var ``history``/
        ``memories`` al template; se il pack non le accetta cade su
        prepend nel context (back-compat)."""
        try:
            user_content = render(
                "user.j2",
                context=context,
                question=question,
                history=history_block,
                memories=memories_block,
            )
        except Exception:
            extras = []
            if memories_block:
                extras.append(memories_block)
            if history_block:
                extras.append(history_block)
            enriched = "\n\n---\n\n".join([*extras, context]) if extras else context
            user_content = render("user.j2", context=enriched, question=question)
        return [
            {"role": "system", "content": render("system.j2")},
            {"role": "user", "content": user_content},
        ]

    def _load_memories(self, question: str) -> list[dict[str, Any]]:
        return load_memories(user_id=self.user_id, question=question, top_k=self.memories_top_k)

    def _load_history(self) -> list[dict[str, Any]]:
        return load_history(conversation_id=self.conversation_id, max_turns=self.history_turns)


__all__ = ["RAGAgent", "RAGResult"]
