"""Smoke tests for the Jinja2 prompt registry.

Step 2 acceptance: an active Domain Pack exposes its prompt templates and
renders them with arbitrary variables. Tests run against both the
``_template`` and ``insurance`` packs to lock the public template names.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from llm_wiki.domain.prompts import PromptNotFoundError, get_registry, render
from llm_wiki.domain.registry import load_pack, reset_pack_cache


@pytest.fixture(autouse=True)
def _isolate_cache() -> Iterator[None]:
    reset_pack_cache()
    yield
    reset_pack_cache()


def test_template_pack_renders_rag_prompts() -> None:
    load_pack("_template", force=True)
    system = render("system.j2")
    user = render("user.j2", context="ctx-block", question="why?")
    no_hits = render("no_hits.j2")

    assert "Template Wiki" in system
    assert "ctx-block" in user
    assert "why?" in user
    assert "Template Wiki" in no_hits


def test_insurance_pack_renders_full_prompt_suite() -> None:
    load_pack("insurance", force=True)

    system = render("system.j2")
    assert "polizze assicurative italiane" in system
    assert "FRANCHIGIA" in system.upper()

    user = render("user.j2", context="ctx", question="cosa copre la garanzia furto?")
    assert "ctx" in user

    classify_system = render("ingest/classify_system.j2")
    assert "polizza-set-informativo" in classify_system

    plan_user = render(
        "ingest/plan_user.j2",
        classification={"source_type": "polizza-set-informativo"},
        outline="# Sezione 1\n# Sezione 2",
        existing_pages=[],
    )
    assert "polizza-set-informativo" in plan_user
    assert "Sezione 1" in plan_user

    source_page_user = render(
        "ingest/source_page_user.j2",
        plan={"source_page": {}, "derived_pages": []},
        classification={"title": "X"},
        source_path="raw/foo.pdf",
        outline="o",
        examples_block="(nessuno)",
        today_iso="2025-04-29",
    )
    assert "raw/foo.pdf" in source_page_user
    assert "2025-04-29" in source_page_user

    garanzia_user = render(
        "ingest/garanzia_page_user.j2",
        plan_entry={"title": "Furto"},
        plan_context={},
        source_slug="sources/foo",
        today_iso="2025-04-29",
        section_markdown="testo",
        tables_json=[],
        examples_block="(nessuno)",
    )
    assert "[[sources/foo]]" in garanzia_user


def test_unknown_template_raises() -> None:
    load_pack("_template", force=True)
    with pytest.raises(PromptNotFoundError):
        render("does_not_exist.j2")


def test_registry_rebuilds_when_pack_changes() -> None:
    load_pack("_template", force=True)
    first = get_registry()
    assert first.pack.name == "_template"

    load_pack("insurance", force=True)
    second = get_registry()
    assert second.pack.name == "insurance"
    assert first is not second
