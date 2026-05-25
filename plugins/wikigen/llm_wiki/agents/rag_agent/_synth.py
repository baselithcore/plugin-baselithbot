"""Synthesis paths (sync + stream) used by :class:`RAGAgent`.

Both functions accept the agent instance via ``agent`` parameter so they
can be reused by ``AgenticRAGAgent`` which subclasses RAGAgent and
overrides retrieval.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from llm_wiki.agents.rag_agent._citations import maybe_repair as maybe_repair_citations
from llm_wiki.agents.rag_agent._result import RAGResult
from llm_wiki.agents.rag_context import (
    build_context,
    build_history_block,
    build_memories_block,
)
from llm_wiki.agents.rag_guards import (
    apply_intent_warning,
    maybe_check_code_blocks,
    maybe_check_numerics,
    maybe_intent_report,
    maybe_score_groundedness,
    maybe_strip_code_blocks,
    maybe_strip_numerics,
    rag_sampling_options,
)
from llm_wiki.config import RAG_GROUNDEDNESS_REPAIR


def _generate(*args: Any, **kw: Any) -> str:
    """Indirezione: legge ``generate`` dal namespace del package
    ``rag_agent`` così i test possono fare
    ``monkeypatch.setattr("…rag_agent.generate", …)`` e intercettarlo."""
    from llm_wiki.agents import rag_agent as _pkg

    return _pkg.generate(*args, **kw)


def _stream(*args: Any, **kw: Any):
    """Indirezione: vedi :func:`_generate`."""
    from llm_wiki.agents import rag_agent as _pkg

    return _pkg.stream(*args, **kw)


def _render(*args: Any, **kw: Any) -> str:
    """Indirezione: vedi :func:`_generate`."""
    from llm_wiki.agents import rag_agent as _pkg

    return _pkg.render(*args, **kw)


if TYPE_CHECKING:
    from llm_wiki.agents.rag_agent import RAGAgent

logger = logging.getLogger(__name__)


def synthesize_from_hits(
    agent: RAGAgent,
    question: str,
    hits: list[dict[str, Any]],
    *,
    prefetched_history: list[dict[str, Any]] | None = None,
) -> RAGResult:
    """Esegue tutto il path post-retrieval (sync): build_context → intent
    guard → memories/history → generate → guard di post-processing.

    ``prefetched_history``: se passata, evita il roundtrip DB interno.
    Usata dal caller (``RAGAgent.answer``) che ha già caricato history
    per il query condensing. ``None`` = back-compat (carica internamente).
    """
    context, sources = build_context(hits)
    intent_report = maybe_intent_report(question, context, hits=hits)
    context = apply_intent_warning(context, intent_report)
    memories = agent._load_memories(question)
    memories_block = build_memories_block(memories)
    history_turns = prefetched_history if prefetched_history is not None else agent._load_history()
    history_block = build_history_block(history_turns)

    if not hits:
        return RAGResult(
            answer=_render("no_hits.j2", question=question),
            sources=[],
            context="",
            hits=[],
            memories=memories,
            history_used=len(history_turns),
            intent_report=intent_report,
        )

    messages = agent._build_messages(
        question=question,
        context=context,
        memories_block=memories_block,
        history_block=history_block,
    )
    answer = _generate(messages=messages, options=rag_sampling_options())
    answer, _report = maybe_repair_citations(answer=answer, sources=sources, messages=messages)
    groundedness = maybe_score_groundedness(answer, context)
    if groundedness and groundedness.below_threshold and RAG_GROUNDEDNESS_REPAIR:
        from llm_wiki.agents.groundedness import repair_feedback as groundedness_repair_feedback

        feedback = groundedness_repair_feedback(groundedness)
        if feedback:
            repair_messages = [
                *messages,
                {"role": "assistant", "content": answer},
                {"role": "user", "content": feedback},
            ]
            try:
                answer = _generate(
                    messages=repair_messages,
                    options=rag_sampling_options(),
                    use_cache=False,
                )
                logger.info("[groundedness] repaired (%s)", groundedness.summary())
            except Exception as exc:
                logger.warning("[groundedness] repair failed (%s) — keep original", exc)
    code_report = maybe_check_code_blocks(answer, context)
    if code_report and code_report.has_violations:
        logger.warning("[code-block guard] %s", code_report.summary())
    answer = maybe_strip_code_blocks(answer, code_report)
    numeric_report = maybe_check_numerics(answer, context)
    if numeric_report and numeric_report.has_violations:
        logger.warning("[numeric guard] %s", numeric_report.summary())
    answer = maybe_strip_numerics(answer, numeric_report)
    return RAGResult(
        answer=answer,
        sources=sources,
        context=context,
        hits=hits,
        memories=memories,
        history_used=len(history_turns),
        intent_report=intent_report,
        groundedness_report=groundedness,
        code_block_report=code_report,
        numeric_guard_report=numeric_report,
    )


def stream_synthesis_from_hits(
    agent: RAGAgent,
    question: str,
    hits: list[dict[str, Any]],
    *,
    prefetched_history: list[dict[str, Any]] | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream solo il path post-retrieval. Permette ad agent agentic di
    accumulare hits da più ricerche e poi delegare la sintesi streaming
    a questo helper. ``prefetched_history`` come in
    :func:`synthesize_from_hits`."""
    memories = agent._load_memories(question)
    if memories:
        yield {
            "type": "step",
            "content": f"Recuperate {len(memories)} memorie personali pertinenti",
        }
        yield {"type": "memories", "items": memories}

    history_turns = prefetched_history if prefetched_history is not None else agent._load_history()
    if history_turns and prefetched_history is None:
        # Solo annuncia se NON pre-fetched (il caller ha già emesso lo
        # step "Memoria conversazione: N turni" — evita duplicato UX).
        yield {
            "type": "step",
            "content": f"Includo {len(history_turns)} turni di conversazione precedenti",
        }

    context, sources = build_context(hits)
    intent_report = maybe_intent_report(question, context, hits=hits)
    context = apply_intent_warning(context, intent_report)
    memories_block = build_memories_block(memories)
    history_block = build_history_block(history_turns)

    if not hits:
        yield {"type": "agent", "content": "RAG"}
        yield {"type": "token", "content": _render("no_hits.j2", question=question)}
        yield {"type": "sources", "items": []}
        yield {"type": "done"}
        return

    if intent_report and intent_report.mismatch:
        yield {
            "type": "intent_warning",
            "query_intent": intent_report.query_intent,
            "context_register": intent_report.context_register,
            "summary": (
                "Intento OPERATIVO della domanda vs CONTESTO concettuale: "
                "l'apertura della risposta dichiarerà esplicitamente il gap."
            ),
        }

    yield {"type": "agent", "content": "RAG"}
    yield {"type": "step", "content": "Generazione risposta in corso…"}

    accumulated: list[str] = []
    try:
        for piece in _stream(
            messages=agent._build_messages(
                question=question,
                context=context,
                memories_block=memories_block,
                history_block=history_block,
            ),
            options=rag_sampling_options(),
        ):
            accumulated.append(piece)
            yield {"type": "token", "content": piece}
    except Exception as exc:
        logger.error("[rag] streaming fallito: %s", exc)
        yield {"type": "error", "message": str(exc)}

    full_answer = "".join(accumulated)

    # UX: tokens già emessi → emetti sources + done **subito**, prima
    # dei guard post-stream (groundedness judge può aggiungere ~5-15s).
    yield {"type": "sources", "items": sources}
    yield {"type": "done"}

    # Citation validation post-streaming. Repair non applicabile in
    # stream — emette solo evento warning.
    from llm_wiki.agents.rag_agent._citations import validate as validate_citations

    report = validate_citations(answer=full_answer, sources=sources)
    if report and report.has_violations:
        yield {
            "type": "citation_warning",
            "summary": report.summary(),
            "violations": [
                {"raw": v.raw, "folder": v.folder, "slug": v.slug, "reason": v.reason}
                for v in report.violations
            ],
        }

    gr = maybe_score_groundedness(full_answer, context)
    if gr and gr.below_threshold:
        yield {
            "type": "groundedness_warning",
            "ratio": gr.supported_ratio,
            "threshold": gr.threshold,
            "summary": gr.summary(),
            "unsupported": [{"text": c.text, "note": c.note} for c in gr.unsupported_claims()],
        }

    cb = maybe_check_code_blocks(full_answer, context)
    if cb and cb.has_violations:
        yield {
            "type": "code_block_warning",
            "summary": cb.summary(),
            "answer_has_code_context_does_not": cb.answer_has_code_context_does_not,
            "fabricated_languages": cb.answer_only_langs,
        }

    nm = maybe_check_numerics(full_answer, context)
    if nm and nm.has_violations:
        yield {
            "type": "numeric_warning",
            "summary": nm.summary(),
            "unsupported": [
                {"raw": c.raw, "core": c.core, "family": c.family, "unit": c.unit}
                for c in nm.unsupported
            ],
        }
