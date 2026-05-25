"""End-to-end scaffolding test.

Validates that ``python -m llm_wiki init --domain <name>`` produces a
self-contained Domain Pack that loads through the registry, exposes its
prompt suite, validates frontmatter, and dispatches via the default
strategy. This is the white-label acceptance test.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from llm_wiki.cli import app
from llm_wiki.domain.prompts import render, reset_registry_cache
from llm_wiki.domain.registry import load_pack, reset_pack_cache
from llm_wiki.domain.schema import get_schema, reset_schema_cache
from llm_wiki.domain.strategies import (
    DefaultPageTypeStrategy,
    reset_strategies_cache,
    select_page_type_strategy,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolate() -> Iterator[None]:
    reset_pack_cache()
    reset_registry_cache()
    reset_schema_cache()
    reset_strategies_cache()
    yield
    reset_pack_cache()
    reset_registry_cache()
    reset_schema_cache()
    reset_strategies_cache()


@pytest.fixture
def scaffolded(tmp_path: Path) -> Iterator[tuple[str, Path]]:
    """Run ``init`` against a real CLI invocation and clean up afterwards."""
    name = "smoke_legal"
    target = REPO_ROOT / "domains" / name
    if target.exists():
        shutil.rmtree(target)
    vault = tmp_path / "legal-vault"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            "--domain",
            name,
            "--label",
            "Wiki Smoke",
            "--description",
            "smoke test domain",
            "--language",
            "en",
            "--vault-root",
            str(vault),
            "--no-write-env",
        ],
    )
    assert result.exit_code == 0, result.output

    yield name, target

    if target.exists():
        shutil.rmtree(target)


def test_init_creates_full_pack_layout(scaffolded: tuple[str, Path]) -> None:
    name, target = scaffolded

    # files mandated by the engine to ingest end-to-end
    assert (target / "pack.yaml").is_file()
    assert (target / "schema.yaml").is_file()
    for prompt in ("system.j2", "user.j2", "no_hits.j2"):
        assert (target / "prompts" / prompt).is_file()
    for prompt in (
        "_base.j2",
        "classify_system.j2",
        "classify_user.j2",
        "plan_system.j2",
        "plan_user.j2",
        "source_page_system.j2",
        "source_page_user.j2",
        "entity_page_system.j2",
        "entity_page_user.j2",
        "refine_system.j2",
        "refine_user.j2",
    ):
        assert (target / "prompts" / "ingest" / prompt).is_file(), f"missing {prompt}"
    assert (target / "examples").is_dir()
    # strategies file ships as a renameable example, not active
    assert (target / "strategies.py.example").is_file()


def test_init_customises_pack_yaml(scaffolded: tuple[str, Path]) -> None:
    name, target = scaffolded
    text = (target / "pack.yaml").read_text(encoding="utf-8")
    assert f"name: {name}" in text
    assert 'label: "Wiki Smoke"' in text
    assert 'description: "smoke test domain"' in text
    assert "language: en" in text
    assert 'app_name: "Wiki Smoke"' in text


def test_scaffolded_pack_loads_through_registry(scaffolded: tuple[str, Path]) -> None:
    name, _ = scaffolded
    pack = load_pack(name, force=True)
    assert pack.name == name
    assert pack.label == "Wiki Smoke"
    assert pack.language == "en"
    assert {pt.id for pt in pack.page_types} == {"source", "concept", "entity", "topic"}


def test_scaffolded_pack_renders_rag_prompts(scaffolded: tuple[str, Path]) -> None:
    name, _ = scaffolded
    load_pack(name, force=True)
    system = render("system.j2")
    user = render("user.j2", context="ctx", question="q")
    no_hits = render("no_hits.j2")
    assert "Wiki Smoke" in system
    assert "ctx" in user
    assert "Wiki Smoke" in no_hits


def test_scaffolded_pack_renders_ingest_prompts(scaffolded: tuple[str, Path]) -> None:
    name, _ = scaffolded
    load_pack(name, force=True)
    classify_system = render("ingest/classify_system.j2")
    plan_system = render("ingest/plan_system.j2")
    refine_system = render("ingest/refine_system.j2")
    assert "Wiki Smoke" in classify_system
    assert "source | concept | entity | topic" in plan_system
    assert "linter" in refine_system


def test_scaffolded_pack_validates_frontmatter(scaffolded: tuple[str, Path]) -> None:
    name, _ = scaffolded
    load_pack(name, force=True)
    schema = get_schema()
    # `type` (non `page_type`) è il nome del campo scritto da
    # `ingest_raw.frontmatter.frontmatter_defaults` e letto da
    # `wiki.parser.parse_file`. Lo schema deve dichiararlo coerente.
    errors = schema.validate("source", {"title": "Foo", "type": "source"})
    assert errors == []
    bad = schema.validate("source", {"type": "source"})
    assert any("title" in e for e in bad)


def test_scaffolded_pack_dispatches_default_strategy(scaffolded: tuple[str, Path]) -> None:
    name, _ = scaffolded
    load_pack(name, force=True)
    strat = select_page_type_strategy(page_type="concept", subtype=None)
    assert isinstance(strat, DefaultPageTypeStrategy)


def test_init_refuses_reserved_template_name() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--domain", "_template"])
    assert result.exit_code != 0


def test_init_refuses_invalid_domain_name() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--domain", "Legal Wiki"])
    assert result.exit_code != 0
