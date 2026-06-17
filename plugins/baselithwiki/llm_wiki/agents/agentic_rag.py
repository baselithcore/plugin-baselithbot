"""Agentic RAG agent: plan → multi-search → reflect → synthesize.

Difesa contro il fallimento classico del RAG monolitico: domanda
composita ("cos'è X e come si implementa Y") che, con UNA sola
retrieval, recupera evidenza solo per uno degli aspetti, portando il
modello a concludere falsamente "il documento non parla di Y" anche
quando il vault ha un intero capitolo dedicato a Y.

Strategia plan-and-execute (più semplice di ReAct, meno LLM call):

1. **Plan** (1 LLM call) — il planner scompone la domanda in 1-N
   sotto-domande indipendenti che, prese insieme, coprono TUTTI gli
   aspetti. Domande atomiche restano una sola sotto-domanda.
2. **Search** (N retrieval) — per ogni sotto-domanda, una pipeline
   retrieval completa via :func:`vectorstore.core.search`. Risultati
   dedupati per ``point_id``.
3. **Reflect** opzionale (1 LLM call) — dopo le ricerche iniziali, il
   reflector ispeziona i titoli/registri recuperati e propone fino a 2
   sotto-domande aggiuntive per coprire aspetti residui. Vuoto = fine.
4. **Search extras** — se ``reflect`` ha proposto query, eseguile e
   mergia gli hits.
5. **Synthesize** (1 LLM call) — :class:`RAGAgent._synthesize_from_hits`
   (riusa tutto il path post-retrieval esistente: guards, citations,
   groundedness, code-block, numeric).

Costo: baseline ~1 LLM call retrieval + 1 LLM call synthesis = 2.
Agentic plan-only: 2 + 1 plan = 3. Agentic + reflect: 4. Latenza 2-3×
del baseline. Gated da ``AGENTIC_RAG_ENABLED`` (default OFF).

Riuso completo del ``RAGAgent``: l'agentic è una sottoclasse che
override ``answer``/``stream`` ma delega la sintesi al parent — tutti i
guard (citation, groundedness, code-block, numeric, intent) sono
ereditati gratuitamente.

Prompt templates and JSON utils live in :mod:`_agentic_prompts`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from llm_wiki.agents._agentic_prompts import (
    _PLANNER_SYSTEM,
    _REFLECTOR_SYSTEM,
    _evidence_summary,
    _parse_json_safe,
)
from llm_wiki.agents.rag_agent import RAGAgent, RAGResult
from llm_wiki.config import (
    AGENTIC_RAG_MAX_ITERATIONS,
    AGENTIC_RAG_PARALLEL_SEARCHES,
    AGENTIC_RAG_PLANNER_MAX_SUBQUERIES,
    AGENTIC_RAG_REFLECT_ENABLED,
    RETRIEVAL_TOP_K,
)
from llm_wiki.utils.llm import generate
from llm_wiki.vectorstore.core import search
from llm_wiki.vectorstore.parallel import is_parallel_safe, parallel_map

logger = logging.getLogger(__name__)


class AgenticRAGAgent(RAGAgent):
    """RAG agent con multi-step reasoning.

    Sottoclasse di :class:`RAGAgent` — riusa tutti i guard di
    post-processing (citation, groundedness, code-block, numeric,
    intent) via ``_synthesize_from_hits`` / ``_stream_synthesis_from_hits``.

    Args:
        max_iterations: numero massimo di round di ricerca. 1 = plan
            only (no reflect). 2+ = plan + reflect.
        reflect_enabled: abilita il round di reflection. Override del
            default env ``AGENTIC_RAG_REFLECT_ENABLED``.
        planner_max_subqueries: cap sulle sub-query del planner.
    """

    def __init__(
        self,
        *,
        max_iterations: int | None = None,
        reflect_enabled: bool | None = None,
        planner_max_subqueries: int | None = None,
        **base_kwargs: Any,
    ) -> None:
        super().__init__(**base_kwargs)
        self.max_iterations = max(
            1,
            max_iterations
            if max_iterations is not None
            else AGENTIC_RAG_MAX_ITERATIONS,
        )
        self.reflect_enabled = (
            reflect_enabled
            if reflect_enabled is not None
            else AGENTIC_RAG_REFLECT_ENABLED
        )
        self.planner_max_subqueries = max(
            1,
            planner_max_subqueries
            if planner_max_subqueries is not None
            else AGENTIC_RAG_PLANNER_MAX_SUBQUERIES,
        )

    # --- public API --------------------------------------------------------

    def answer(self, question: str, *, limit: int = RETRIEVAL_TOP_K) -> RAGResult:
        history = self._load_history()
        # Single condense informs both planner (history-aware) and the
        # fallback monolithic search when the planner yields one sub_query.
        condensed = self._condense(question, history)
        sub_queries = self._plan(condensed.query, history=history)
        hits = self._search_multi(sub_queries, limit=limit)

        if self.reflect_enabled and self.max_iterations >= 2:
            extras = self._reflect(condensed.query, hits)
            if extras:
                logger.info(
                    "[agentic] reflect propose %d extra queries: %s",
                    len(extras),
                    extras,
                )
                more_hits = self._search_multi(extras, limit=limit)
                hits = self._dedup_merge(hits, more_hits)

        # Cap finale per non saturare context window.
        hits = hits[: limit * 2]
        return self._synthesize_from_hits(question, hits, prefetched_history=history)

    def stream(
        self, question: str, *, limit: int = RETRIEVAL_TOP_K
    ) -> Iterator[dict[str, Any]]:
        history = self._load_history()
        if history:
            yield {
                "type": "step",
                "content": f"Memoria conversazione: {len(history)} turni precedenti",
            }
        condensed = self._condense(question, history)
        if condensed.rewritten:
            yield {
                "type": "step",
                "content": "Riformulata in query autonoma per planning + retrieval",
            }
            yield {
                "type": "query_rewrite",
                "original": condensed.original,
                "rewritten": condensed.query,
            }

        yield {"type": "agent", "content": "Planner"}
        yield {"type": "step", "content": "Pianificazione delle ricerche…"}
        sub_queries = self._plan(condensed.query, history=history)
        if len(sub_queries) > 1:
            yield {
                "type": "step",
                "content": f"Domanda composita: {len(sub_queries)} sotto-domande identificate",
            }
        yield {"type": "plan", "sub_queries": list(sub_queries)}

        yield {"type": "agent", "content": "Retriever"}
        # Annuncia il fan-out: l'utente vede subito le ricerche pianificate,
        # poi i risultati vengono raccolti in parallelo (o serial in embedded
        # mode). Niente progress per-step quando parallelo — sarebbe
        # disordinato — ma il count finale arriva nello stesso stream.
        parallel = (
            AGENTIC_RAG_PARALLEL_SEARCHES
            and is_parallel_safe()
            and len(sub_queries) > 1
        )
        if parallel:
            yield {
                "type": "step",
                "content": f"Esecuzione parallela di {len(sub_queries)} ricerche…",
            }
            hits = self._search_multi(sub_queries, limit=limit)
        else:
            hits = []
            for i, sq in enumerate(sub_queries, start=1):
                yield {
                    "type": "step",
                    "content": f"Ricerca {i}/{len(sub_queries)}: {sq[:60]}…",
                }
                sub_hits = search(sq, limit=limit, expand_with_graph=self.use_graph)
                hits = self._dedup_merge(hits, sub_hits)
        yield {"type": "hits", "count": len(hits)}

        if self.reflect_enabled and self.max_iterations >= 2:
            yield from self._stream_reflect_phase(question, hits, limit=limit)

        hits = hits[: limit * 2]
        yield from self._stream_synthesis_from_hits(
            question, hits, prefetched_history=history
        )

    def _stream_reflect_phase(
        self,
        question: str,
        hits: list[dict[str, Any]],
        *,
        limit: int,
    ) -> Iterator[dict[str, Any]]:
        """Reflection sub-phase for :meth:`stream`.

        Extracted to keep ``stream`` under the 500-LOC cap while
        preserving identical behaviour.
        """
        yield {"type": "agent", "content": "Reflector"}
        yield {"type": "step", "content": "Analisi copertura evidenze…"}
        extras = self._reflect(question, hits)
        if extras:
            yield {
                "type": "step",
                "content": f"Coperture mancanti: {len(extras)} ricerche addizionali",
            }
            yield {"type": "reflect", "extra_queries": list(extras)}
            yield {"type": "agent", "content": "Retriever"}
            parallel_extra = (
                AGENTIC_RAG_PARALLEL_SEARCHES and is_parallel_safe() and len(extras) > 1
            )
            if parallel_extra:
                yield {
                    "type": "step",
                    "content": f"Esecuzione parallela di {len(extras)} ricerche extra…",
                }
                more = self._search_multi(extras, limit=limit)
                hits[:] = self._dedup_merge(hits, more)
            else:
                for i, eq in enumerate(extras, start=1):
                    yield {
                        "type": "step",
                        "content": f"Ricerca extra {i}/{len(extras)}: {eq[:60]}…",
                    }
                    extra_hits = search(
                        eq, limit=limit, expand_with_graph=self.use_graph
                    )
                    hits[:] = self._dedup_merge(hits, extra_hits)
            yield {"type": "hits", "count": len(hits)}
        else:
            yield {
                "type": "step",
                "content": "Copertura adeguata, sintesi immediata",
            }

    # --- internals ---------------------------------------------------------

    def _plan(
        self,
        question: str,
        *,
        history: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Planner: 1 LLM call → list di sub-queries.

        ``history``: turni precedenti, inseriti come blocco "Conversazione
        precedente" nel user-message così il planner emette sub_queries
        AUTONOMICHE (no anaphora). Vuoto/None = comportamento legacy.

        Fallback: in caso di errore o output non parsabile, ritorna
        ``[question]`` (degrade graceful a RAG monolitico).
        """
        system_msg = _PLANNER_SYSTEM.format(max_subs=self.planner_max_subqueries)
        user_msg = self._planner_user_message(question, history)
        try:
            raw = generate(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                json_mode=True,
                use_cache=True,
            )
        except Exception as exc:
            logger.warning("[agentic] planner failed (%s) — fallback monolitico", exc)
            return [question]
        subs = _parse_json_safe(raw, key="sub_queries")
        if not subs:
            return [question]
        # Dedup case-insensitive preservando ordine, cap, garantisce
        # presenza della domanda originale (segnale dell'utente non si
        # perde dietro le riformulazioni).
        seen: set[str] = set()
        out: list[str] = []
        for s in subs[: self.planner_max_subqueries]:
            key = s.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(s.strip())
        if not out:
            return [question]
        if question.strip().lower() not in {o.lower() for o in out}:
            out.insert(0, question.strip())
        logger.info("[agentic] plan: '%s' → %d sub_queries", question[:40], len(out))
        return out

    def _reflect(self, question: str, hits: list[dict[str, Any]]) -> list[str]:
        """Reflector: 1 LLM call → list di extra queries. Vuoto = stop."""
        evidence = _evidence_summary(hits)
        try:
            raw = generate(
                messages=[
                    {
                        "role": "system",
                        "content": _REFLECTOR_SYSTEM.format(
                            question=question.strip(),
                            evidence_summary=evidence,
                        ),
                    },
                    {
                        "role": "user",
                        "content": "Restituisci il JSON di valutazione.",
                    },
                ],
                json_mode=True,
                use_cache=True,
            )
        except Exception as exc:
            logger.warning("[agentic] reflector failed (%s) — skip extras", exc)
            return []
        extras = _parse_json_safe(raw, key="extra_queries")
        # Filtra duplicati case-insensitive vs hits documenti già visti
        seen_keys: set[str] = set()
        out: list[str] = []
        for e in extras[:2]:  # hard cap: max 2 extra queries per reflection
            key = e.strip().lower()
            if key and key not in seen_keys:
                seen_keys.add(key)
                out.append(e.strip())
        return out

    def _search_multi(self, queries: list[str], *, limit: int) -> list[dict[str, Any]]:
        """Esegue ``search`` per ciascuna query, mergia con dedup.

        Parallelizzato via thread pool quando ``AGENTIC_RAG_PARALLEL_SEARCHES``
        è ON e il client Qdrant è server-mode (thread-safe). In embedded mode
        oppure con flag OFF cade su esecuzione serial.
        """

        def _run(q: str) -> list[dict[str, Any]]:
            try:
                return search(q, limit=limit, expand_with_graph=self.use_graph)
            except Exception as exc:
                logger.warning("[agentic] search '%s…' failed (%s)", q[:40], exc)
                return []

        if AGENTIC_RAG_PARALLEL_SEARCHES and is_parallel_safe() and len(queries) > 1:
            per_query_hits = parallel_map(_run, queries)
        else:
            per_query_hits = [_run(q) for q in queries]

        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for sub_hits in per_query_hits:
            for h in sub_hits:
                key = str(h.get("point_id") or h.get("id") or "")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                merged.append(h)
        return merged

    @staticmethod
    def _planner_user_message(
        question: str, history: list[dict[str, Any]] | None
    ) -> str:
        """Format planner user-message. Quando ``history`` non-vuota,
        prepend block "Conversazione precedente" così le sub_queries
        emesse sono autonomiche."""
        q = question.strip()
        if not history:
            return q
        from llm_wiki.agents.rag_agent._query_rewriter import (
            _format_history_for_condense,
        )
        from llm_wiki.config import RAG_HISTORY_CONDENSE_MAX_TURNS

        block = _format_history_for_condense(
            history, max_turns=RAG_HISTORY_CONDENSE_MAX_TURNS
        )
        if not block:
            return q
        return (
            "Conversazione precedente (usala per risolvere riferimenti impliciti "
            "nella nuova domanda):\n"
            f"{block}\n\n"
            f"Nuova domanda dell'utente: {q}"
        )

    @staticmethod
    def _dedup_merge(
        existing: list[dict[str, Any]], new: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Mergia ``new`` in ``existing`` dedupando per ``point_id``/``id``."""
        if not new:
            return existing
        seen: set[str] = set()
        for h in existing:
            key = str(h.get("point_id") or h.get("id") or "")
            if key:
                seen.add(key)
        out = list(existing)
        for h in new:
            key = str(h.get("point_id") or h.get("id") or "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            out.append(h)
        return out


__all__ = ["AgenticRAGAgent"]
