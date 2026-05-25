"""Tests per :mod:`llm_wiki.vectorstore.query_classifier`.

Heuristic-only — niente Qdrant, niente LLM, niente mock complessi.
"""

from __future__ import annotations

import pytest

from llm_wiki.domain.pack import DomainPack, PageType, UILabels
from llm_wiki.vectorstore.query_classifier import (
    detect_archetype,
    infer,
    resolve_page_type,
)


def _pack(page_type_ids: list[tuple[str, str, str]]) -> DomainPack:
    """Costruisci un pack minimale per i test.

    Ogni tupla = (id, label, plural).
    """
    return DomainPack(
        schema_version=1,
        name="test",
        label="Test",
        language="it",
        page_types=[
            PageType(id=pid, label=lbl, plural=plr, folder=pid + "s")
            for pid, lbl, plr in page_type_ids
        ],
        subtypes={},
        frontmatter_schema="schema.yaml",
        grouping=[],
        ui=UILabels(app_name="Test"),
    )


# --- detect_archetype -------------------------------------------------------


@pytest.mark.parametrize(
    "query,expected_archetype,expected_conf",
    [
        ("Cos'è un knowledge graph?", "definitional", "strict"),
        ("cos'è il RAG", "definitional", "strict"),
        ("che cos'è la vettorializzazione semantica?", "definitional", "strict"),
        ("Definizione di chunking nel contesto NLP", "definitional", "strict"),
        ("what is contextual retrieval?", "definitional", "strict"),
        ("Quali sono i casi d'uso del nostro sistema?", "example", "strict"),
        ("esempi di prompt injection", "example", "strict"),
        ("Mostrami un esempio di sistema RAG", "example", "strict"),
        ("use cases for LLM in production", "example", "strict"),
        ("come configurare un retriever ibrido?", "procedural", "strict"),
        ("how to deploy a vector database", "procedural", "strict"),
        ("procedura per il backup", "procedural", "strict"),
        ("step by step per setup", "procedural", "strict"),
    ],
)
def test_strict_archetypes(
    query: str, expected_archetype: str, expected_conf: str
) -> None:
    archetype, conf, _ = detect_archetype(query)
    assert archetype == expected_archetype
    assert conf == expected_conf


@pytest.mark.parametrize(
    "query,expected_archetype,expected_conf",
    [
        (
            "Vorrei capire il significato del RAG nel contesto industriale",
            "definitional",
            "soft",
        ),
        ("Hai qualche esempio interessante da mostrarmi?", "example", "soft"),
        ("Mi serve un tutorial generale sul tema", "procedural", "soft"),
    ],
)
def test_soft_archetypes(
    query: str, expected_archetype: str, expected_conf: str
) -> None:
    archetype, conf, _ = detect_archetype(query)
    assert archetype == expected_archetype
    assert conf == expected_conf


@pytest.mark.parametrize(
    "query",
    [
        "",
        "   ",
        "discuti del rapporto tra agenti autonomi e governance",
        "valutiamo i compromessi architetturali del sistema",
    ],
)
def test_unknown_archetype(query: str) -> None:
    archetype, conf, _ = detect_archetype(query)
    assert archetype == "unknown"
    assert conf == "none"


# --- resolve_page_type ------------------------------------------------------


def test_resolve_definitional_to_concept() -> None:
    pack = _pack([("source", "Fonte", "fonti"), ("concept", "Concetto", "concetti")])
    assert resolve_page_type("definitional", pack) == "concept"


def test_resolve_example_prefers_case_study_over_source() -> None:
    pack = _pack(
        [
            ("source", "Fonte", "fonti"),
            ("case_study", "Caso di studio", "casi di studio"),
        ]
    )
    assert resolve_page_type("example", pack) == "case_study"


def test_resolve_example_falls_back_to_source() -> None:
    pack = _pack([("source", "Fonte", "fonti"), ("concept", "Concetto", "concetti")])
    assert resolve_page_type("example", pack) == "source"


def test_resolve_procedural_to_source_when_no_runbook() -> None:
    pack = _pack([("source", "Fonte", "fonti"), ("concept", "Concetto", "concetti")])
    assert resolve_page_type("procedural", pack) == "source"


def test_resolve_returns_none_when_no_match() -> None:
    pack = _pack([("article", "Articolo", "articoli")])
    assert resolve_page_type("definitional", pack) is None
    assert resolve_page_type("example", pack) is None


def test_resolve_returns_none_when_pack_missing() -> None:
    assert resolve_page_type("definitional", None) is None


def test_resolve_unknown_returns_none() -> None:
    pack = _pack([("concept", "Concetto", "concetti")])
    assert resolve_page_type("unknown", pack) is None


def test_resolve_matches_via_label_substring() -> None:
    """Pack che non usa l'id 'concept' ma ha un label che contiene 'concet'."""
    pack = _pack([("entity_def", "Concetto teorico", "concetti")])
    assert resolve_page_type("definitional", pack) == "entity_def"


# --- infer end-to-end -------------------------------------------------------


def test_infer_end_to_end_definitional() -> None:
    pack = _pack([("concept", "Concetto", "concetti"), ("source", "Fonte", "fonti")])
    result = infer("cos'è il chunking?", pack)
    assert result.archetype == "definitional"
    assert result.confidence == "strict"
    assert result.page_type_id == "concept"
    assert result.matched_pattern == "definitional_strict"


def test_infer_end_to_end_example_strict() -> None:
    pack = _pack(
        [
            ("source", "Fonte", "fonti"),
            ("case_study", "Caso di studio", "casi"),
        ]
    )
    result = infer("Quali sono i casi d'uso del retrieval ibrido?", pack)
    assert result.archetype == "example"
    assert result.confidence == "strict"
    assert result.page_type_id == "case_study"


def test_infer_returns_none_page_type_when_pack_lacks_match() -> None:
    """Query chiaramente definitional ma pack senza concept/entity → page_type None."""
    pack = _pack([("article", "Articolo", "articoli")])
    result = infer("cos'è il deployment?", pack)
    assert result.archetype == "definitional"
    assert result.confidence == "strict"
    assert result.page_type_id is None


def test_infer_unknown_query() -> None:
    pack = _pack([("concept", "Concetto", "concetti")])
    result = infer("discutiamo del progetto in generale", pack)
    assert result.archetype == "unknown"
    assert result.confidence == "none"
    assert result.page_type_id is None


def test_infer_without_pack() -> None:
    result = infer("cos'è il chunking?", None)
    assert result.archetype == "definitional"
    assert result.page_type_id is None
