"""Smoke tests for the Domain Pack contract.

Step 1 acceptance: a pack on disk loads through the registry and exposes
its declared page types and UI labels. Tests run against the `_template`
pack so they keep working even when verticals are added or removed.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from llm_wiki.domain.pack import DomainPack
from llm_wiki.domain.registry import (
    DomainPackNotFoundError,
    load_pack,
    reset_pack_cache,
)


@pytest.fixture(autouse=True)
def _isolate_cache() -> Iterator[None]:
    reset_pack_cache()
    yield
    reset_pack_cache()


def test_load_template_pack() -> None:
    pack = load_pack("_template", force=True)
    assert isinstance(pack, DomainPack)
    assert pack.name == "_template"
    assert pack.label == "Template Wiki"
    assert pack.has_page_type("source")
    assert pack.has_page_type("concept")
    assert pack.page_type("source").folder == "sources"
    assert pack.ui.app_name == "Template Wiki"
    assert pack.prompts_path.name == "prompts"
    assert pack.schema_path.name == "schema.yaml"


def test_unknown_domain_raises() -> None:
    with pytest.raises(DomainPackNotFoundError):
        load_pack("does-not-exist", force=True)


def test_missing_app_domain_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_DOMAIN", raising=False)
    with pytest.raises(DomainPackNotFoundError):
        load_pack(force=True)


def test_cache_returns_same_instance() -> None:
    first = load_pack("_template", force=True)
    second = load_pack("_template")
    assert first is second
