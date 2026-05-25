"""Test tolleranza schema su output LLM piccoli (qwen 7b, llama3 8b).

Questi modelli emettono frequentemente ``source_page`` / elementi di
``derived_pages`` come **stringa** (il path) invece dell'oggetto
strutturato. Senza coercion il primo round bruciava 3 retry × 30-60s
prima del fallimento. Coerce string → ``{"target_path": str}`` permette
al primo retry di passare.
"""

from __future__ import annotations

from llm_wiki.ingest_raw.schemas import IngestPlan


def test_source_page_as_string_coerced_to_dict() -> None:
    p = IngestPlan(source_page="wiki/sources/foo.md")  # type: ignore[arg-type]
    assert p.source_page.target_path == "wiki/sources/foo.md"
    # I campi non emessi prendono i default sicuri.
    assert p.source_page.title == ""
    assert p.source_page.page_type == ""


def test_source_page_as_dict_passes_through() -> None:
    p = IngestPlan(
        source_page={  # type: ignore[arg-type]
            "target_path": "wiki/sources/x.md",
            "title": "X",
            "page_type": "source",
        }
    )
    assert p.source_page.title == "X"
    assert p.source_page.page_type == "source"


def test_derived_pages_mixed_string_and_dict() -> None:
    p = IngestPlan(
        source_page={"target_path": "wiki/sources/x.md"},  # type: ignore[arg-type]
        derived_pages=[  # type: ignore[arg-type]
            "wiki/concepts/a.md",
            {"target_path": "wiki/topics/b.md", "page_type": "topic"},
        ],
    )
    assert p.derived_pages[0].target_path == "wiki/concepts/a.md"
    assert p.derived_pages[0].page_type == ""
    assert p.derived_pages[1].target_path == "wiki/topics/b.md"
    assert p.derived_pages[1].page_type == "topic"


def test_flat_pageplan_rewrap_under_source_page() -> None:
    """qwen 7b emette plan come PagePlan piatto → rewrap automatico."""
    p = IngestPlan(  # type: ignore[call-arg]
        target_path="wiki/sources/foo.md",
        page_type=None,  # qwen 7b emette null su required
        title="Best practices",
        source_sections=["Intro", "Conclusion"],
        wikilinks_expected=["log.md"],
    )
    assert p.source_page.target_path == "wiki/sources/foo.md"
    assert p.source_page.title == "Best practices"
    assert p.source_page.source_sections == ["Intro", "Conclusion"]
    assert p.source_page.wikilinks_expected == ["log.md"]
    # Nessuna leak: i campi root sono stati consumati.
    assert p.derived_pages == []


def test_flat_rewrap_idempotent_on_structured_input() -> None:
    p = IngestPlan(
        source_page={  # type: ignore[arg-type]
            "target_path": "wiki/sources/x.md",
            "title": "X",
        }
    )
    assert p.source_page.target_path == "wiki/sources/x.md"
    assert p.source_page.title == "X"


def test_derived_pages_none_becomes_empty_list() -> None:
    p = IngestPlan(
        source_page={"target_path": "wiki/sources/x.md"},  # type: ignore[arg-type]
        derived_pages=None,  # type: ignore[arg-type]
    )
    assert p.derived_pages == []
