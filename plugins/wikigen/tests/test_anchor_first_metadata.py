"""Anchor-first metadata: hierarchical chunker espone heading fine,
citation validator valida anchor quando il flag è ON, doc_register
fallback infierisce da page_type quando il payload tace.

Copre i gap del wave 1:
- ``section_heading_fine`` punta al heading più profondo (H3+) sotto cui
  ricade il child quando il parent_window contiene sotto-sezioni;
- ``CitationReport.valid`` ora è ``(folder, slug, anchor)`` — tuple a 3;
- ``validate(..., validate_anchors=True)`` solleva ``unknown_anchor`` su
  citation con ``#section`` non presente fra i source recuperati;
- fallback registro: ``runbook`` → operational, ``concept`` → conceptual.
"""

from __future__ import annotations

from llm_wiki.agents.citation_validator import validate
from llm_wiki.agents.rag_context import _infer_register_from_page_type
from llm_wiki.vectorstore.hierarchical import chunk_markdown_hierarchical

# --- hierarchical heading_fine -------------------------------------------


def test_child_resolves_to_finest_heading() -> None:
    text = "## Capitolo A\n\nIntro del capitolo.\n\n" "### Sezione A.1\n\n" + (
        "Frase A.1. " * 30
    ) + "\n\n### Sezione A.2\n\n" + ("Frase A.2. " * 30)
    out = chunk_markdown_hierarchical(text, parent_size=2000, child_size=200)
    # Heading fine deve essere "Sezione A.1" o "Sezione A.2" per la parte
    # di testo che ricade sotto di esse.
    headings = {c.section_heading_fine for c in out}
    assert "Sezione A.1" in headings or "Sezione A.2" in headings
    # Anchor coerente con slug del heading fine
    for c in out:
        if c.section_heading_fine == "Sezione A.1":
            assert c.section_anchor_fine == "sezione-a1"
            break


def test_child_falls_back_to_parent_heading_when_no_inner_heading() -> None:
    text = "## Capitolo A\n\n" + ("Solo prosa nessun heading interno. " * 50)
    out = chunk_markdown_hierarchical(text, parent_size=2000, child_size=200)
    assert out
    # Tutti i child ricadono sotto "Capitolo A"; nessun heading interno
    # → fine_heading == fallback "Capitolo A".
    for c in out:
        assert c.section_heading_fine == "Capitolo A"
        assert c.section_anchor_fine == "capitolo-a"


def test_section_heading_fine_field_present_on_dataclass() -> None:
    text = "## H\n\nbody body body body body body body body."
    out = chunk_markdown_hierarchical(text, parent_size=500, child_size=200)
    assert all(hasattr(c, "section_heading_fine") for c in out)
    assert all(hasattr(c, "section_anchor_fine") for c in out)


# --- citation_validator anchor validation --------------------------------


_FOLDERS = {"concepts", "runbooks"}
_SOURCES = [
    {
        "document_id": "concepts/rag-pattern",
        "section_heading": "Casi d'uso",
        "section_anchor": "casi-duso",
    },
    {
        "document_id": "concepts/rag-pattern",
        "section_heading": "Limiti",
        "section_anchor": "limiti",
    },
]


def test_valid_returns_three_tuple_with_anchor() -> None:
    report = validate(
        "Vedi [[concepts/rag-pattern#Casi d'uso]] per dettagli.",
        allowed_folders=_FOLDERS,
        sources=_SOURCES,
        strict_grounding=True,
        validate_anchors=True,
    )
    assert not report.violations
    assert len(report.valid) == 1
    folder, slug, anchor = report.valid[0]
    assert folder == "concepts"
    assert slug == "rag-pattern"
    assert anchor == "casi-duso"


def test_anchor_validation_off_ignores_unknown_anchor() -> None:
    report = validate(
        "Vedi [[concepts/rag-pattern#Sezione inesistente]].",
        allowed_folders=_FOLDERS,
        sources=_SOURCES,
        strict_grounding=True,
        validate_anchors=False,
    )
    # Comportamento storico: anchor non validato → wikilink valido.
    # L'anchor viene comunque estratto e normalizzato nel tuple per
    # observability (debug / scorer eval), ma non solleva violazione.
    assert not report.violations
    assert report.valid[0][2] == "sezione-inesistente"


def test_anchor_validation_on_flags_unknown_anchor() -> None:
    report = validate(
        "Vedi [[concepts/rag-pattern#Sezione inesistente]].",
        allowed_folders=_FOLDERS,
        sources=_SOURCES,
        strict_grounding=True,
        validate_anchors=True,
    )
    assert report.has_violations
    assert report.violations[0].reason == "unknown_anchor"
    assert report.violations[0].anchor == "Sezione inesistente"


def test_wikilink_without_anchor_unaffected_by_validation() -> None:
    report = validate(
        "Vedi [[concepts/rag-pattern]].",
        allowed_folders=_FOLDERS,
        sources=_SOURCES,
        strict_grounding=True,
        validate_anchors=True,
    )
    assert not report.violations
    assert report.valid[0][2] == ""


def test_unknown_folder_still_caught() -> None:
    report = validate(
        "Vedi [[ghost/page#anything]].",
        allowed_folders=_FOLDERS,
        sources=_SOURCES,
        strict_grounding=True,
        validate_anchors=True,
    )
    assert report.has_violations
    assert report.violations[0].reason == "unknown_folder"


# --- doc_register fallback inference -------------------------------------


def test_register_fallback_operational() -> None:
    assert _infer_register_from_page_type("runbook") == "operational"
    assert _infer_register_from_page_type("procedure") == "operational"
    assert _infer_register_from_page_type("HOWTO") == "operational"


def test_register_fallback_conceptual() -> None:
    assert _infer_register_from_page_type("concept") == "conceptual"
    assert _infer_register_from_page_type("topic") == "conceptual"
    assert _infer_register_from_page_type("entity") == "conceptual"


def test_register_fallback_ambiguous_is_empty() -> None:
    # `source` può essere whitepaper o runbook → no fallback.
    assert _infer_register_from_page_type("source") == ""
    assert _infer_register_from_page_type("case_study") == ""
    assert _infer_register_from_page_type(None) == ""
    assert _infer_register_from_page_type("") == ""
