"""Tests for history-aware query condensing (conversational memory).

Covers :mod:`llm_wiki.agents.rag_agent._query_rewriter` + the end-to-end
wiring in :class:`RAGAgent` and :class:`AgenticRAGAgent`.

No LLM/Qdrant calls — all external dependencies mocked.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from llm_wiki.agents.rag_agent._query_rewriter import (
    CondenseResult,
    _clean_llm_output,
    _format_history_for_condense,
    _looks_standalone,
    condense_question,
)

# --- heuristics ------------------------------------------------------------


def test_looks_standalone_long_no_anaphora_returns_true() -> None:
    q = "Quali sono le differenze fra retrieval ibrido e retrieval denso nel contesto RAG?"
    assert _looks_standalone(q) is True


def test_looks_standalone_anaphora_returns_false() -> None:
    # Even very long, presence of "quello" → follow-up.
    q = "Approfondiscilo nei dettagli tecnici e fornisci esempi pratici di applicazione"
    assert _looks_standalone(q) is False


def test_looks_standalone_short_returns_false() -> None:
    assert _looks_standalone("perché?") is False
    assert _looks_standalone("e per la v3?") is False


def test_looks_standalone_english_anaphora() -> None:
    assert _looks_standalone("expand on that please") is False
    assert _looks_standalone("what about it") is False


# --- formatting ------------------------------------------------------------


def test_format_history_caps_turns() -> None:
    turns = [{"role": "user", "content": f"q{i}"} for i in range(10)]
    out = _format_history_for_condense(turns, max_turns=4)
    # Keep last 4
    assert "q6" in out and "q9" in out
    assert "q0" not in out


def test_format_history_truncates_long_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llm_wiki.agents.rag_agent._query_rewriter.RAG_HISTORY_TURN_MAX_CHARS", 50
    )
    turns = [{"role": "assistant", "content": "a" * 200}]
    out = _format_history_for_condense(turns, max_turns=4)
    assert "…" in out
    # Body line fits within max (≈ 49 chars + ellipsis + role prefix)
    body_line = [line for line in out.splitlines() if line.startswith("Assistente:")][0]
    assert len(body_line) < 80


def test_format_history_skips_empty_turns() -> None:
    turns = [
        {"role": "user", "content": "  "},
        {"role": "assistant", "content": "real"},
    ]
    out = _format_history_for_condense(turns, max_turns=4)
    assert "real" in out
    assert "Utente" not in out


# --- output cleaning -------------------------------------------------------


def test_clean_strips_prefix_and_quotes() -> None:
    raw = '  Query autonoma: "come configurare X in produzione"  '
    assert _clean_llm_output(raw) == "come configurare X in produzione"


def test_clean_collapses_newlines() -> None:
    raw = "linea 1\n  linea 2"
    assert _clean_llm_output(raw) == "linea 1 linea 2"


def test_clean_clamps_length(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "llm_wiki.agents.rag_agent._query_rewriter.RAG_HISTORY_CONDENSE_MAX_OUTPUT_CHARS",
        20,
    )
    out = _clean_llm_output("x" * 100)
    assert len(out) <= 20
    assert out.endswith("…")


# --- condense_question (top-level) -----------------------------------------


def test_condense_skips_when_disabled() -> None:
    res = condense_question(
        "domanda", [{"role": "user", "content": "ctx"}], enabled=False
    )
    assert isinstance(res, CondenseResult)
    assert res.rewritten is False
    assert res.skip_reason == "disabled"
    assert res.query == "domanda"


def test_condense_skips_no_history(monkeypatch: pytest.MonkeyPatch) -> None:
    res = condense_question("domanda", [], enabled=True)
    assert res.skip_reason == "no_history"
    assert res.query == "domanda"


def test_condense_skips_standalone_question(monkeypatch: pytest.MonkeyPatch) -> None:
    # Long, no anaphora — heuristic short-circuits.
    q = "Quali sono i passaggi per configurare il retrieval ibrido in produzione?"
    history = [
        {"role": "user", "content": "prev"},
        {"role": "assistant", "content": "ans"},
    ]
    res = condense_question(q, history, enabled=True)
    assert res.skip_reason == "heuristic_standalone"
    assert res.query == q
    assert res.rewritten is False


def test_condense_rewrites_followup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Anaphoric follow-up → LLM rewrites to standalone."""
    calls: dict[str, Any] = {"n": 0, "last_messages": None}

    def _fake_generate(*, messages: list[dict[str, str]], **_kw: Any) -> str:
        calls["n"] += 1
        calls["last_messages"] = messages
        return "Quali sono gli aspetti operativi del retrieval ibrido?"

    monkeypatch.setattr("llm_wiki.agents.rag_agent.generate", _fake_generate)

    history = [
        {"role": "user", "content": "Cos'è il retrieval ibrido?"},
        {"role": "assistant", "content": "È un approccio dense + sparse + ColBERT."},
    ]
    res = condense_question("approfondiscilo", history, enabled=True)

    assert calls["n"] == 1
    assert res.rewritten is True
    assert res.skip_reason is None
    assert "retrieval ibrido" in res.query.lower()
    # Original preserved for synthesis
    assert res.original == "approfondiscilo"
    # History present in prompt
    sys_user = (calls["last_messages"] or [])[-1]["content"]
    assert "retrieval ibrido" in sys_user.lower()


def test_condense_fallback_on_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(**_kw: Any) -> str:
        raise RuntimeError("llm down")

    monkeypatch.setattr("llm_wiki.agents.rag_agent.generate", _boom)
    history = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}]
    res = condense_question("approfondiscilo", history, enabled=True)
    assert res.skip_reason == "llm_failed"
    assert res.query == "approfondiscilo"
    assert res.rewritten is False


def test_condense_fallback_on_empty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.agents.rag_agent.generate", lambda **_kw: "   ")
    history = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}]
    res = condense_question("approfondisci", history, enabled=True)
    assert res.skip_reason == "empty_output"
    assert res.query == "approfondisci"


def test_condense_detects_model_kept_original(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model echoes back same query → not flagged as rewrite (UX noise)."""
    monkeypatch.setattr(
        "llm_wiki.agents.rag_agent.generate",
        lambda **_kw: "approfondiscilo",
    )
    history = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}]
    res = condense_question("approfondiscilo", history, enabled=True)
    assert res.rewritten is False
    assert res.skip_reason == "model_kept_original"


# --- RAGAgent integration --------------------------------------------------


def test_rag_agent_uses_condensed_query_for_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: history + follow-up → search receives rewritten query,
    synthesis receives ORIGINAL question."""
    from llm_wiki.agents.rag_agent import RAGAgent

    # Stub history loader (avoid Postgres)
    monkeypatch.setattr(
        "llm_wiki.agents.rag_agent.load_history",
        lambda **_kw: [
            {"role": "user", "content": "Cos'è il retrieval ibrido?"},
            {"role": "assistant", "content": "Dense + sparse + ColBERT."},
        ],
    )

    # generate is called by:
    # 1. condense → returns rewritten query
    # 2. synthesis → returns final answer
    responses = iter(
        [
            "Quali sono gli aspetti operativi del retrieval ibrido?",
            "Risposta finale.",
        ]
    )
    captured_synth_messages: list[list[dict[str, str]]] = []

    def _fake_generate(*, messages: list[dict[str, str]], **_kw: Any) -> str:
        # Synthesis call carries 2 messages (system+user); condense carries 2 too,
        # distinguish by content of system message.
        sys_content = messages[0].get("content", "")
        if "riformulatore di query" in sys_content.lower():
            return next(responses)
        captured_synth_messages.append(messages)
        return next(responses)

    monkeypatch.setattr("llm_wiki.agents.rag_agent.generate", _fake_generate)
    monkeypatch.setattr(
        "llm_wiki.agents.rag_agent.render",
        lambda name, **kw: f"<template:{name}>:{kw.get('question', '')}",
    )

    # Track search query
    search_calls: list[str] = []

    def _fake_search(query: str, **_kw: Any) -> list[dict[str, Any]]:
        search_calls.append(query)
        return [
            {
                "id": "p1",
                "point_id": "p1",
                "payload": {"document_id": "doc/x", "title": "X", "text": "body"},
                "score": 0.9,
            }
        ]

    monkeypatch.setattr("llm_wiki.agents.rag_agent.search", _fake_search)
    # Disable guards
    monkeypatch.setattr("llm_wiki.agents.rag_guards.RAG_GROUNDEDNESS_ENABLED", False)
    monkeypatch.setattr("llm_wiki.config.CITATION_REPAIR_ENABLED", False)

    agent = RAGAgent(conversation_id="conv-1")
    # Force condense ON regardless of POSTGRES_ENABLED env
    monkeypatch.setattr(
        agent, "_condense", lambda q, h: condense_question(q, h, enabled=True)
    )

    result = agent.answer("approfondiscilo", limit=5)

    # Retrieval received REWRITTEN query
    assert len(search_calls) == 1
    assert "retrieval ibrido" in search_calls[0].lower()
    # Synthesis user message contains ORIGINAL question (template rendered with it)
    assert captured_synth_messages
    user_msg = captured_synth_messages[0][-1]["content"]
    assert "approfondiscilo" in user_msg
    # history_used reflects prefetched turns
    assert result.history_used == 2


def test_rag_agent_stream_emits_query_rewrite_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from llm_wiki.agents.rag_agent import RAGAgent

    monkeypatch.setattr(
        "llm_wiki.agents.rag_agent.load_history",
        lambda **_kw: [
            {"role": "user", "content": "Cos'è X?"},
            {"role": "assistant", "content": "X è ..."},
        ],
    )

    def _fake_generate(*, messages: list[dict[str, str]], **_kw: Any) -> str:
        sys_content = messages[0].get("content", "")
        if "riformulatore" in sys_content.lower():
            return "Quali sono gli aspetti operativi di X?"
        return "Risposta sintetizzata."

    def _fake_stream(*, messages: list[dict[str, str]], **_kw: Any) -> Any:
        yield "Risposta "
        yield "sintetizzata."

    monkeypatch.setattr("llm_wiki.agents.rag_agent.generate", _fake_generate)
    monkeypatch.setattr("llm_wiki.agents.rag_agent.stream", _fake_stream)
    monkeypatch.setattr(
        "llm_wiki.agents.rag_agent.render",
        lambda name, **kw: f"<template:{name}>",
    )
    monkeypatch.setattr(
        "llm_wiki.agents.rag_agent.search",
        lambda q, **_kw: [
            {
                "id": "p1",
                "point_id": "p1",
                "payload": {"document_id": "doc/x", "title": "X", "text": "body"},
                "score": 0.9,
            }
        ],
    )
    monkeypatch.setattr("llm_wiki.agents.rag_guards.RAG_GROUNDEDNESS_ENABLED", False)

    agent = RAGAgent(conversation_id="conv-2")
    monkeypatch.setattr(
        agent, "_condense", lambda q, h: condense_question(q, h, enabled=True)
    )

    events = list(agent.stream("approfondiscilo", limit=5))
    rewrite_events = [e for e in events if e.get("type") == "query_rewrite"]
    assert len(rewrite_events) == 1
    assert rewrite_events[0]["original"] == "approfondiscilo"
    assert "aspetti operativi" in rewrite_events[0]["rewritten"].lower()


def test_rag_agent_no_rewrite_event_when_history_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Back-compat: chat senza history persistita → niente rewrite, niente
    nuovi eventi, comportamento identico a Fase pre-memoria."""
    from llm_wiki.agents.rag_agent import RAGAgent

    monkeypatch.setattr(
        "llm_wiki.agents.rag_agent._loaders.load_history", lambda **_kw: []
    )

    def _fake_generate(**_kw: Any) -> str:
        return "Risposta."

    def _fake_stream(**_kw: Any) -> Any:
        yield "Risposta."

    monkeypatch.setattr("llm_wiki.agents.rag_agent.generate", _fake_generate)
    monkeypatch.setattr("llm_wiki.agents.rag_agent.stream", _fake_stream)
    monkeypatch.setattr("llm_wiki.agents.rag_agent.render", lambda name, **kw: "<t>")
    monkeypatch.setattr(
        "llm_wiki.agents.rag_agent.search",
        lambda q, **_kw: [
            {
                "id": "p1",
                "point_id": "p1",
                "payload": {"document_id": "doc/x", "title": "X", "text": "body"},
                "score": 0.9,
            }
        ],
    )
    monkeypatch.setattr("llm_wiki.agents.rag_guards.RAG_GROUNDEDNESS_ENABLED", False)

    agent = RAGAgent()
    events = list(agent.stream("qualsiasi domanda atomica", limit=5))
    rewrite_events = [e for e in events if e.get("type") == "query_rewrite"]
    assert rewrite_events == []


# --- AgenticRAGAgent planner integration -----------------------------------


def test_agentic_planner_user_message_includes_history() -> None:
    from llm_wiki.agents.agentic_rag import AgenticRAGAgent

    history = [
        {"role": "user", "content": "Cos'è X?"},
        {"role": "assistant", "content": "X è ..."},
    ]
    msg = AgenticRAGAgent._planner_user_message("approfondiscilo", history)
    assert "Conversazione precedente" in msg
    assert "Cos'è X?" in msg
    assert "approfondiscilo" in msg


def test_agentic_planner_user_message_no_history_returns_question() -> None:
    from llm_wiki.agents.agentic_rag import AgenticRAGAgent

    msg = AgenticRAGAgent._planner_user_message("test", None)
    assert msg == "test"
    msg = AgenticRAGAgent._planner_user_message("test", [])
    assert msg == "test"


def test_agentic_plan_with_history_calls_generate_with_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from llm_wiki.agents.agentic_rag import AgenticRAGAgent

    captured: dict[str, Any] = {}

    def _fake_generate(*, messages: list[dict[str, str]], **_kw: Any) -> str:
        captured["user"] = messages[-1]["content"]
        return json.dumps({"sub_queries": ["aspetti operativi di X"], "rationale": "x"})

    monkeypatch.setattr("llm_wiki.agents.agentic_rag.generate", _fake_generate)
    agent = AgenticRAGAgent()
    plan = agent._plan(
        "approfondiscilo",
        history=[
            {"role": "user", "content": "Cos'è X?"},
            {"role": "assistant", "content": "X è ..."},
        ],
    )
    assert "Conversazione precedente" in captured["user"]
    # Planner output is augmented with the original question at position 0
    # (preserve user's wording as retrieval signal), so the LLM-generated
    # subquery is at >=1.
    assert any("X" in sq for sq in plan)
