"""Test AgenticRAGAgent: plan → multi-search → reflect → synthesize.

Mock di ``generate`` (per planner/reflector) e ``search`` (per
retrieval). Nessuna chiamata LLM o Qdrant reale.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from llm_wiki.agents.agentic_rag import AgenticRAGAgent, _parse_json_safe, _strip_fences

# --- helpers parsing -------------------------------------------------------


def test_strip_fences_no_fence() -> None:
    assert _strip_fences('{"a": 1}') == '{"a": 1}'


def test_strip_fences_with_json_fence() -> None:
    raw = '```json\n{"sub_queries": ["a"]}\n```'
    assert _strip_fences(raw).startswith("{")


def test_strip_fences_with_preamble() -> None:
    raw = 'Ecco il JSON:\n{"sub_queries": ["a"]}'
    cleaned = _strip_fences(raw)
    assert cleaned.startswith("{")


def test_parse_json_safe_valid() -> None:
    raw = '{"sub_queries": ["q1", "q2"], "rationale": "x"}'
    assert _parse_json_safe(raw, key="sub_queries") == ["q1", "q2"]


def test_parse_json_safe_invalid_returns_empty() -> None:
    assert _parse_json_safe("non-json garbage", key="sub_queries") == []


def test_parse_json_safe_missing_key_returns_empty() -> None:
    raw = '{"other": ["x"]}'
    assert _parse_json_safe(raw, key="sub_queries") == []


def test_parse_json_safe_non_string_items_filtered() -> None:
    raw = '{"sub_queries": ["valid", 42, null, "  ", "ok"]}'
    assert _parse_json_safe(raw, key="sub_queries") == ["valid", "ok"]


# --- planner / reflector ---------------------------------------------------


@pytest.fixture
def mock_generate(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Mock ``generate`` per LLM call planner/reflector + synthesis.

    Patcha BOTH ``agentic_rag.generate`` (planner/reflector) e
    ``rag_agent.generate`` (synthesis): condividono la stessa queue di
    response → l'ordine di pop riflette l'ordine reale delle LLM call
    nel flusso end-to-end.
    """
    state: dict[str, Any] = {"responses": [], "calls": []}

    def _fake_generate(*, messages: list[dict[str, str]], **kwargs: Any) -> str:
        state["calls"].append({"messages": messages, "kwargs": kwargs})
        if not state["responses"]:
            return "{}"
        return state["responses"].pop(0)

    monkeypatch.setattr("llm_wiki.agents.agentic_rag.generate", _fake_generate)
    monkeypatch.setattr("llm_wiki.agents.rag_agent.generate", _fake_generate)
    return state


@pytest.fixture
def mock_search(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Mock ``search`` di ``vectorstore.core``. Per-query results."""
    state: dict[str, Any] = {"per_query": {}, "calls": []}

    def _fake_search(query: str, **kwargs: Any) -> list[dict[str, Any]]:
        state["calls"].append({"query": query, "kwargs": kwargs})
        return list(state["per_query"].get(query, []))

    monkeypatch.setattr("llm_wiki.agents.agentic_rag.search", _fake_search)
    return state


def _hit(point_id: str, doc_id: str, title: str, **extra: Any) -> dict[str, Any]:
    payload = {"document_id": doc_id, "title": title, "text": title}
    payload.update(extra)
    return {"id": point_id, "point_id": point_id, "payload": payload, "score": 0.9}


# --- _plan -----------------------------------------------------------------


def test_plan_atomic_query_returns_single(
    monkeypatch: pytest.MonkeyPatch, mock_generate: dict[str, Any]
) -> None:
    mock_generate["responses"].append(
        json.dumps({"sub_queries": ["cos'è il chunking?"], "rationale": "atomic"})
    )
    agent = AgenticRAGAgent(planner_max_subqueries=3)
    plan = agent._plan("cos'è il chunking?")
    assert plan == ["cos'è il chunking?"]


def test_plan_composite_query_returns_multiple(
    monkeypatch: pytest.MonkeyPatch, mock_generate: dict[str, Any]
) -> None:
    mock_generate["responses"].append(
        json.dumps(
            {
                "sub_queries": [
                    "cos'è il RAG?",
                    "come si implementa il RAG?",
                ],
                "rationale": "definizione + procedura",
            }
        )
    )
    agent = AgenticRAGAgent(planner_max_subqueries=3)
    plan = agent._plan("cos'è il RAG e come si implementa?")
    assert len(plan) >= 2
    assert any("implementa" in p.lower() for p in plan)


def test_plan_fallback_to_original_on_llm_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(**_kw: Any) -> str:
        raise RuntimeError("llm down")

    monkeypatch.setattr("llm_wiki.agents.agentic_rag.generate", _boom)
    agent = AgenticRAGAgent()
    plan = agent._plan("qualsiasi domanda")
    assert plan == ["qualsiasi domanda"]


def test_plan_fallback_on_garbage_output(
    monkeypatch: pytest.MonkeyPatch, mock_generate: dict[str, Any]
) -> None:
    mock_generate["responses"].append("not json at all")
    agent = AgenticRAGAgent()
    plan = agent._plan("test")
    assert plan == ["test"]


def test_plan_cap_respected(monkeypatch: pytest.MonkeyPatch, mock_generate: dict[str, Any]) -> None:
    mock_generate["responses"].append(json.dumps({"sub_queries": ["q1", "q2", "q3", "q4", "q5"]}))
    agent = AgenticRAGAgent(planner_max_subqueries=2)
    plan = agent._plan("composita")
    # Cap=2 + injection di "composita" se non presente nelle prime 2
    assert len(plan) <= 3
    assert "composita" in plan


# --- _reflect --------------------------------------------------------------


def test_reflect_returns_empty_when_coverage_adequate(
    monkeypatch: pytest.MonkeyPatch, mock_generate: dict[str, Any]
) -> None:
    mock_generate["responses"].append(json.dumps({"missing_aspects": [], "extra_queries": []}))
    agent = AgenticRAGAgent()
    extras = agent._reflect("domanda", hits=[_hit("p1", "doc/foo", "Foo")])
    assert extras == []


def test_reflect_proposes_extras_on_gap(
    monkeypatch: pytest.MonkeyPatch, mock_generate: dict[str, Any]
) -> None:
    mock_generate["responses"].append(
        json.dumps(
            {
                "missing_aspects": ["aspetto operativo"],
                "extra_queries": ["come si implementa X?"],
            }
        )
    )
    agent = AgenticRAGAgent()
    extras = agent._reflect("cos'è X e come?", hits=[])
    assert extras == ["come si implementa X?"]


def test_reflect_caps_at_two(
    monkeypatch: pytest.MonkeyPatch, mock_generate: dict[str, Any]
) -> None:
    mock_generate["responses"].append(
        json.dumps(
            {
                "missing_aspects": ["a", "b", "c"],
                "extra_queries": ["q1", "q2", "q3", "q4"],
            }
        )
    )
    agent = AgenticRAGAgent()
    extras = agent._reflect("multi", hits=[])
    assert len(extras) == 2


def test_reflect_handles_llm_failure_silently(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(**_kw: Any) -> str:
        raise RuntimeError("offline")

    monkeypatch.setattr("llm_wiki.agents.agentic_rag.generate", _boom)
    agent = AgenticRAGAgent()
    extras = agent._reflect("x", hits=[])
    assert extras == []


# --- _search_multi + _dedup_merge -----------------------------------------


def test_search_multi_dedups_by_point_id(
    monkeypatch: pytest.MonkeyPatch, mock_search: dict[str, Any]
) -> None:
    mock_search["per_query"]["q1"] = [_hit("p1", "d1", "A"), _hit("p2", "d2", "B")]
    mock_search["per_query"]["q2"] = [_hit("p2", "d2", "B"), _hit("p3", "d3", "C")]
    agent = AgenticRAGAgent()
    out = agent._search_multi(["q1", "q2"], limit=5)
    ids = [h["point_id"] for h in out]
    assert ids == ["p1", "p2", "p3"]


def test_search_multi_continues_on_individual_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"calls": 0}

    def _fake_search(query: str, **_kw: Any) -> list[dict[str, Any]]:
        state["calls"] += 1
        if query == "boom":
            raise RuntimeError("qdrant down")
        return [_hit(f"p_{query}", f"d_{query}", query)]

    monkeypatch.setattr("llm_wiki.agents.agentic_rag.search", _fake_search)
    agent = AgenticRAGAgent()
    out = agent._search_multi(["ok1", "boom", "ok2"], limit=5)
    # Le due query ok hanno prodotto un hit ciascuna; "boom" è skippata
    assert {h["point_id"] for h in out} == {"p_ok1", "p_ok2"}


def test_dedup_merge_preserves_existing_order() -> None:
    existing = [_hit("p1", "d1", "A"), _hit("p2", "d2", "B")]
    new = [_hit("p2", "d2", "B-dup"), _hit("p3", "d3", "C")]
    out = AgenticRAGAgent._dedup_merge(existing, new)
    assert [h["point_id"] for h in out] == ["p1", "p2", "p3"]


# --- end-to-end answer -----------------------------------------------------


def test_answer_end_to_end_with_reflect(
    monkeypatch: pytest.MonkeyPatch,
    mock_generate: dict[str, Any],
    mock_search: dict[str, Any],
) -> None:
    """Planner produce 2 sub_queries, reflect propone 1 extra, sintesi
    riceve l'union dedupata."""
    # 1) Plan response
    mock_generate["responses"].append(
        json.dumps({"sub_queries": ["cos'è X?", "come si implementa X?"], "rationale": "comp"})
    )
    # 2) Reflect response
    mock_generate["responses"].append(
        json.dumps({"missing_aspects": ["esempi"], "extra_queries": ["esempi di X"]})
    )
    # 3) Synthesis LLM call → la mock di generate ritornerà la risposta finale.
    mock_generate["responses"].append("Risposta finale sintetizzata.")

    mock_search["per_query"]["cos'è X?"] = [_hit("p1", "concepts/x", "X concept")]
    mock_search["per_query"]["come si implementa X?"] = [_hit("p2", "sources/x", "X impl source")]
    mock_search["per_query"]["esempi di X"] = [_hit("p3", "sources/x-ex", "X esempi")]

    # Disable post-synthesis guards che farebbero LLM call extra non in queue.
    monkeypatch.setattr("llm_wiki.config.POSTGRES_ENABLED", False)
    monkeypatch.setattr("llm_wiki.agents.rag_guards.RAG_GROUNDEDNESS_ENABLED", False)
    monkeypatch.setattr("llm_wiki.config.CITATION_REPAIR_ENABLED", False)

    # Patch render per non dipendere dal pack attivo nei test
    monkeypatch.setattr("llm_wiki.agents.rag_agent.render", lambda name, **kw: f"<template:{name}>")

    agent = AgenticRAGAgent(planner_max_subqueries=3, reflect_enabled=True)
    result = agent.answer("cos'è X e come si implementa?", limit=5)

    # 3 ricerche eseguite: 2 plan + 1 reflect-extra
    queries_done = [c["query"] for c in mock_search["calls"]]
    assert "cos'è X?" in queries_done
    assert "come si implementa X?" in queries_done
    assert "esempi di X" in queries_done
    # Hits unionati e dedupati
    assert len(result.hits) == 3
    assert {h["point_id"] for h in result.hits} == {"p1", "p2", "p3"}
    assert "sintetizzata" in result.answer


def test_answer_no_reflect_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    mock_generate: dict[str, Any],
    mock_search: dict[str, Any],
) -> None:
    mock_generate["responses"].append(json.dumps({"sub_queries": ["q1"], "rationale": "atomic"}))
    # Solo synthesis (no reflect call)
    mock_generate["responses"].append("Risposta.")
    mock_search["per_query"]["q1"] = [_hit("p1", "d/x", "X")]

    monkeypatch.setattr("llm_wiki.config.POSTGRES_ENABLED", False)
    monkeypatch.setattr("llm_wiki.agents.rag_guards.RAG_GROUNDEDNESS_ENABLED", False)
    monkeypatch.setattr("llm_wiki.config.CITATION_REPAIR_ENABLED", False)
    monkeypatch.setattr("llm_wiki.agents.rag_agent.render", lambda name, **kw: f"<template:{name}>")

    agent = AgenticRAGAgent(reflect_enabled=False)
    agent.answer("test", limit=5)
    # 2 generate call: 1 plan + 1 synthesis. NON 3 (reflect skipped).
    assert len(mock_generate["calls"]) == 2
