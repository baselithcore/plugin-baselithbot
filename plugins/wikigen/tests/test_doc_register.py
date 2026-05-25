"""Test inferenza ``doc_register`` da ``source_type`` libero."""

from __future__ import annotations

from llm_wiki.ingest_raw.register import infer_doc_register, register_hint


def test_conceptual_keywords_map_to_conceptual() -> None:
    assert infer_doc_register("whitepaper") == "conceptual"
    assert infer_doc_register("Whitepaper") == "conceptual"
    assert infer_doc_register("white-paper") == "conceptual"
    assert infer_doc_register("ebook strategic vision") == "conceptual"
    assert infer_doc_register("executive summary") == "conceptual"
    assert infer_doc_register("case-study") == "conceptual"


def test_operational_keywords_map_to_operational() -> None:
    assert infer_doc_register("runbook") == "operational"
    assert infer_doc_register("ADR") == "operational"
    assert infer_doc_register("openapi") == "operational"
    assert infer_doc_register("playbook deploy") == "operational"
    assert infer_doc_register("manuale") == "operational"
    assert infer_doc_register("sentenza Cassazione") == "operational"


def test_mixed_signal_returns_mixed() -> None:
    # "manual whitepaper" → entrambi presenti → mixed
    assert infer_doc_register("manual whitepaper") == "mixed"


def test_unknown_falls_back() -> None:
    assert infer_doc_register("") == "unknown"
    assert infer_doc_register(None) == "unknown"
    assert infer_doc_register("foo bar baz nessun match") == "unknown"


def test_register_hint_per_class() -> None:
    assert "operativo" in register_hint("operational")
    assert "concettuale" in register_hint("conceptual")
    assert "misto" in register_hint("mixed")
    assert register_hint("unknown") == ""
