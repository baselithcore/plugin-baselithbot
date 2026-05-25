"""Unit tests for ``planner.extract_verbatim_atoms`` and the source-page
dispatch path in ``DefaultPageTypeStrategy``.

Why this exists: the source-page generator used to receive only the
heading outline (``extract_outline``) — every code fence, table,
admonition and CLI command was silently dropped before the LLM saw the
document. On technical packs (runbooks, ADRs, API specs) this meant the
generated source page lost most of the high-signal content. The two
covered surfaces are:

1. :func:`extract_verbatim_atoms` — deterministic extractor that pulls
   atoms verbatim, preserves source order, dedupes, and respects a
   character budget without truncating mid-fence.
2. :class:`DefaultPageTypeStrategy` — must dispatch ``page_type=source``
   to :func:`source_page_bundle` (passing the atoms) and other page
   types to :func:`entity_page_bundle`. The pre-fix default rendered
   the *RAG* system prompt and a 4000-char head slice — a vestigial
   path that bypassed the pack's editorial templates.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from llm_wiki.domain.registry import load_pack, reset_pack_cache
from llm_wiki.domain.strategies import (
    DefaultPageTypeStrategy,
    GenerationContext,
    reset_strategies_cache,
)
from llm_wiki.ingest_raw.extractor import ExtractedDocument
from llm_wiki.ingest_raw.planner import extract_verbatim_atoms
from llm_wiki.ingest_raw.schemas import IngestPlan, PagePlan


@pytest.fixture(autouse=True)
def _isolate() -> Iterator[None]:
    reset_pack_cache()
    reset_strategies_cache()
    yield
    reset_pack_cache()
    reset_strategies_cache()


# --- extract_verbatim_atoms -------------------------------------------------


def test_extract_returns_empty_on_pure_prose() -> None:
    md = "This is narrative prose without any code, tables, or commands."
    assert extract_verbatim_atoms(md) == ""


def test_extract_preserves_code_fence_verbatim() -> None:
    md = "Intro.\n\n```bash\nkubectl get pods -n prod\n```\n\nOutro."
    out = extract_verbatim_atoms(md)
    assert "```bash" in out
    assert "kubectl get pods -n prod" in out
    assert "<!-- atom:code -->" in out


def test_extract_preserves_markdown_table() -> None:
    md = "Text.\n\n| col1 | col2 |\n|------|------|\n| a    | b    |\n\nEnd."
    out = extract_verbatim_atoms(md)
    assert "| col1 | col2 |" in out
    assert "<!-- atom:table -->" in out


def test_extract_preserves_obsidian_callout() -> None:
    md = "Before.\n\n> [!warning] Destructive\n> Run only with backup.\n\nAfter."
    out = extract_verbatim_atoms(md)
    assert "[!warning]" in out
    assert "Run only with backup." in out


def test_extract_captures_cli_lines() -> None:
    md = "Setup:\n\n$ ls -la /etc\n\nThen:\n\nPS C:\\> Get-Service\n"
    out = extract_verbatim_atoms(md)
    assert "$ ls -la /etc" in out
    assert "PS C:\\> Get-Service" in out


def test_extract_captures_inline_cli_tokens() -> None:
    md = "Apply config with kubectl apply -f manifest.yaml to deploy."
    out = extract_verbatim_atoms(md)
    assert "kubectl apply -f manifest.yaml" in out


def test_extract_preserves_source_order() -> None:
    md = (
        "First a table:\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        "Then code:\n\n```python\nprint('hi')\n```\n\n"
        "Then a callout:\n\n> [!note] x\n> y\n"
    )
    out = extract_verbatim_atoms(md)
    # Table atom comes before code atom, code before callout.
    table_idx = out.index("<!-- atom:table -->")
    code_idx = out.index("<!-- atom:code -->")
    callout_idx = out.index("<!-- atom:callout -->")
    assert table_idx < code_idx < callout_idx


def test_extract_dedupes_cli_inside_code_fence() -> None:
    md = "```bash\nkubectl apply -f x.yaml\n```\n\n"
    out = extract_verbatim_atoms(md)
    # The bare CLI heuristic would re-pick the kubectl line inside the
    # fence — the dedup pass must suppress that to avoid duplication.
    assert out.count("kubectl apply -f x.yaml") == 1


def test_extract_respects_char_budget_without_splitting_atoms() -> None:
    big = "```bash\n" + ("x" * 500) + "\n```"
    second = "```python\nprint(1)\n```"
    md = f"{big}\n\n{second}\n"
    out = extract_verbatim_atoms(md, max_chars=300)
    # Budget too small for the first atom: it's truncated explicitly,
    # but the second atom is not appended after a partial atom.
    assert "...[truncated]" in out
    assert "python" not in out


def test_extract_returns_empty_on_zero_budget() -> None:
    md = "```bash\nls\n```"
    assert extract_verbatim_atoms(md, max_chars=0) == ""


# --- DefaultPageTypeStrategy dispatch ---------------------------------------


def _make_ctx(*, page_type: str, markdown: str, title: str = "Demo") -> GenerationContext:
    plan_entry = PagePlan(
        page_type=page_type,
        target_path=f"wiki/{'sources' if page_type == 'source' else 'concepts'}/demo.md",
        title=title,
        subtype=None,
        priority=1,
    )
    source_entry = PagePlan(
        page_type="source",
        target_path="wiki/sources/source-doc.md",
        title="Source Doc",
        subtype=None,
        priority=0,
    )
    plan = IngestPlan(
        source_file="raw/source-doc.pdf",
        source_type="documento-tecnico",
        edizione=None,
        edizione_iso=None,
        source_page=source_entry,
        derived_pages=[] if page_type == "source" else [plan_entry],
    )
    doc = ExtractedDocument(
        source_path=Path("/tmp/raw/source-doc.pdf"),
        backend="fallback",
        markdown=markdown,
        pages=[],
        tables=[],
        metadata={},
    )
    return GenerationContext(
        plan_entry=plan_entry,
        plan=plan,
        extracted=doc,
        today=date(2025, 5, 23),
        model=None,
    )


def test_default_strategy_routes_source_page_to_source_bundle() -> None:
    load_pack("_template", force=True)
    md = "# Doc\n\nProse.\n\n```yaml\nkey: value\n```\n"
    ctx = _make_ctx(page_type="source", markdown=md, title="Demo")

    captured: dict[str, Any] = {}

    def fake_generate_text(*, messages: list[dict[str, str]], model: Any = None) -> str:
        captured["messages"] = messages
        return "ok"

    with patch("llm_wiki.ingest_raw.llm_client.generate_text", new=fake_generate_text):
        out = DefaultPageTypeStrategy().generate(ctx)
    assert out == "ok"
    # Source bundle must produce a system prompt grounded in the
    # ingest/source_page_system.j2 template (not the RAG system prompt).
    sys_msg = captured["messages"][0]["content"]
    assert "wiki/sources/" in sys_msg or "Snippet e comandi rilevanti" in sys_msg
    # User prompt must include the verbatim atom block.
    user_msg = captured["messages"][1]["content"]
    assert "key: value" in user_msg
    assert "Atomi verbatim" in user_msg


def test_default_strategy_routes_entity_page_to_entity_bundle() -> None:
    load_pack("_template", force=True)
    md = "# Doc\n\nThe Foo Component handles requests.\n\n```bash\nfoo --help\n```\n"
    ctx = _make_ctx(page_type="concept", markdown=md, title="Foo Component")

    captured: dict[str, Any] = {}

    def fake_generate_text(*, messages: list[dict[str, str]], model: Any = None) -> str:
        captured["messages"] = messages
        return "ok"

    with patch("llm_wiki.ingest_raw.llm_client.generate_text", new=fake_generate_text):
        DefaultPageTypeStrategy().generate(ctx)

    sys_msg = captured["messages"][0]["content"]
    user_msg = captured["messages"][1]["content"]
    # Entity bundle uses ingest/entity_page_system.j2 which mentions
    # concept/entity explicitly.
    assert "concept" in sys_msg.lower() or "entity" in sys_msg.lower()
    # The window around the title must surface the prose mentioning it,
    # and the verbatim atom block must be appended.
    assert "Foo Component" in user_msg
    assert "foo --help" in user_msg
