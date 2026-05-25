"""Test per hierarchical (parent-child) chunking + retrieval collapse."""

from __future__ import annotations

import pytest

from llm_wiki.vectorstore.hierarchical import (
    HierarchicalChunk,
    build_parent_id,
    chunk_markdown_hierarchical,
    collapse_hits_by_parent,
)

# --- chunker ---------------------------------------------------------------


def test_empty_text_returns_empty() -> None:
    assert chunk_markdown_hierarchical("") == []
    assert chunk_markdown_hierarchical("   ") == []


def test_single_section_short_returns_one_chunk() -> None:
    text = "## Intro\n\nUn solo paragrafo breve."
    out = chunk_markdown_hierarchical(text, parent_size=1000, child_size=400)
    assert len(out) == 1
    chunk = out[0]
    assert chunk.section_path == ["Intro"]
    # Parent contiene heading + body, child contiene anche heading nella sezione corta
    assert "Un solo paragrafo breve." in chunk.parent_text
    assert "Un solo paragrafo breve." in chunk.child_text


def test_multiple_h2_sections_each_becomes_parent() -> None:
    text = (
        "## Sezione A\n\n" + ("Frase A. " * 50) + "\n\n" + "## Sezione B\n\n" + ("Frase B. " * 50)
    )
    out = chunk_markdown_hierarchical(text, parent_size=2000, child_size=400)
    # Due parent (anchor differente)
    parent_ids = {c.parent_id for c in out}
    assert len(parent_ids) == 2
    # Ogni parent → ≥1 child
    sections = {tuple(c.section_path) for c in out}
    assert ("Sezione A",) in sections
    assert ("Sezione B",) in sections


def test_long_section_split_into_multiple_parents() -> None:
    long_body = "\n\n".join([f"Paragrafo {i} contenuto." * 5 for i in range(40)])
    text = f"## Lunga\n\n{long_body}"
    out = chunk_markdown_hierarchical(text, parent_size=800, child_size=400)
    # Più parent windows con stesso anchor base ma idx diverso
    parent_ids = {c.parent_id for c in out}
    assert len(parent_ids) > 1
    assert all(pid.startswith("lunga:") for pid in parent_ids)


def test_child_smaller_than_parent() -> None:
    text = "## S\n\n" + ("Paragrafo. " * 200)
    out = chunk_markdown_hierarchical(text, parent_size=2000, child_size=300)
    for c in out:
        # Ogni child appartiene al parent
        assert c.child_text in c.parent_text or c.parent_text.startswith(c.child_text[:50])


def test_no_heading_falls_back_to_single_block() -> None:
    text = "Solo testo senza alcun heading. Più paragrafi.\n\nSecondo paragrafo."
    out = chunk_markdown_hierarchical(text, parent_size=1000, child_size=400)
    assert len(out) >= 1
    assert all(c.section_path == [] for c in out)


def test_chunk_indexes_are_unique_and_contiguous() -> None:
    text = "## A\n\n" + "x " * 1000 + "\n\n## B\n\n" + "y " * 1000
    out = chunk_markdown_hierarchical(text, parent_size=800, child_size=300)
    idxs = [c.chunk_index for c in out]
    assert idxs == list(range(len(out)))


# --- build_parent_id -------------------------------------------------------


def test_build_parent_id_format() -> None:
    assert build_parent_id("concepts/foo", "casi-duso:0") == "concepts/foo::casi-duso:0"


# --- collapse_hits_by_parent -----------------------------------------------


def _hit(
    point_id: str,
    parent_id: str | None,
    parent_text: str | None,
    text: str,
    score: float = 0.9,
) -> dict:
    payload: dict = {"text": text, "raw_text": text, "document_id": "concepts/foo"}
    if parent_id:
        payload["parent_id"] = parent_id
        payload["parent_text"] = parent_text
        payload["is_hierarchical"] = True
    return {"id": point_id, "point_id": point_id, "payload": payload, "score": score}


def test_collapse_empty_returns_empty() -> None:
    assert collapse_hits_by_parent([]) == []


def test_collapse_no_parent_passes_through() -> None:
    hits = [
        _hit("p1", None, None, "frammento 1"),
        _hit("p2", None, None, "frammento 2"),
    ]
    out = collapse_hits_by_parent(hits)
    assert out == hits


def test_collapse_three_children_one_parent() -> None:
    parent_text = "Sezione completa con tutti i 3 case study."
    hits = [
        _hit("c1", "doc::sec:0", parent_text, "case study 1", score=0.95),
        _hit("c2", "doc::sec:0", parent_text, "case study 2", score=0.80),
        _hit("c3", "doc::sec:0", parent_text, "case study 3", score=0.70),
    ]
    out = collapse_hits_by_parent(hits)
    assert len(out) == 1
    merged = out[0]
    assert merged["hierarchical_collapsed"] is True
    assert merged["merged_child_count"] == 3
    # Il testo principale è ora il parent
    assert merged["payload"]["text"] == parent_text
    assert merged["payload"]["raw_text"] == parent_text
    # Il child originale è conservato in payload.child_text per audit
    assert merged["payload"]["child_text"] == "case study 1"


def test_collapse_keeps_first_score_default() -> None:
    parent_text = "P"
    hits = [
        _hit("c1", "doc::p:0", parent_text, "first", score=0.7),
        _hit("c2", "doc::p:0", parent_text, "second", score=0.95),  # migliore ma dopo
    ]
    out = collapse_hits_by_parent(hits)
    assert len(out) == 1
    # Default keep_first_score=True: rimane lo score del primo (0.7).
    assert out[0]["score"] == pytest.approx(0.7)


def test_collapse_updates_score_when_keep_first_false() -> None:
    parent_text = "P"
    hits = [
        _hit("c1", "doc::p:0", parent_text, "first", score=0.7),
        _hit("c2", "doc::p:0", parent_text, "second", score=0.95),
    ]
    out = collapse_hits_by_parent(hits, keep_first_score=False)
    assert len(out) == 1
    assert out[0]["score"] == pytest.approx(0.95)


def test_collapse_distinct_parents_kept_separate() -> None:
    hits = [
        _hit("c1", "doc::A:0", "Parent A text", "child A1"),
        _hit("c2", "doc::B:0", "Parent B text", "child B1"),
        _hit("c3", "doc::A:0", "Parent A text", "child A2"),
    ]
    out = collapse_hits_by_parent(hits)
    assert len(out) == 2
    parent_ids_out = {o["payload"]["parent_id"] for o in out}
    assert parent_ids_out == {"doc::A:0", "doc::B:0"}


def test_collapse_mixed_hierarchical_and_legacy_hits() -> None:
    """Pre-hierarchical hits (no parent_id) coexist con nuovi hits."""
    hits = [
        _hit("legacy1", None, None, "vecchio chunk piatto"),
        _hit("c1", "doc::p:0", "new parent text", "new child"),
        _hit("legacy2", None, None, "altro vecchio"),
    ]
    out = collapse_hits_by_parent(hits)
    assert len(out) == 3
    assert out[0]["id"] == "legacy1"
    assert out[2]["id"] == "legacy2"
    # Il middle è il collapsed con parent_text
    assert out[1]["payload"]["text"] == "new parent text"


# --- chunker integration smoke --------------------------------------------


def test_isinstance_hierarchical_chunk() -> None:
    text = "## H\n\nTest text content."
    out = chunk_markdown_hierarchical(text)
    assert all(isinstance(c, HierarchicalChunk) for c in out)


def test_short_children_filtered() -> None:
    """Child < 20 char devono essere filtrati."""
    # Sezione che produrrebbe un child cortissimo se non filtrato
    text = "## a\n\nx"
    out = chunk_markdown_hierarchical(text, parent_size=500, child_size=400)
    # Il child è troppo corto (< 20 char), viene escluso.
    # Il parent_text "## a\n\nx" è ~7 char.
    assert out == [] or all(len(c.child_text) >= 20 for c in out)
