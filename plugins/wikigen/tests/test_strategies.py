"""Step 4 smoke tests: PageTypeStrategy registration + dispatch."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from llm_wiki.domain.registry import load_pack, reset_pack_cache
from llm_wiki.domain.strategies import (
    DefaultPageTypeStrategy,
    get_strategies,
    reset_strategies_cache,
    select_page_type_strategy,
)


@pytest.fixture(autouse=True)
def _isolate() -> Iterator[None]:
    reset_pack_cache()
    reset_strategies_cache()
    yield
    reset_pack_cache()
    reset_strategies_cache()


def test_template_pack_has_no_strategies() -> None:
    load_pack("_template", force=True)
    bundle = get_strategies()
    assert bundle.page_types == []
    assert bundle.extractors == []


def test_template_pack_falls_back_to_default() -> None:
    load_pack("_template", force=True)
    strat = select_page_type_strategy(page_type="concept", subtype=None)
    assert isinstance(strat, DefaultPageTypeStrategy)


def test_insurance_pack_registers_three_strategies() -> None:
    load_pack("insurance", force=True)
    bundle = get_strategies()
    names = [s.name for s in bundle.page_types]
    assert "insurance.source" in names
    assert "insurance.garanzia" in names
    assert "insurance.entity" in names


def test_insurance_dispatch_garanzia() -> None:
    load_pack("insurance", force=True)
    strat = select_page_type_strategy(page_type="concept", subtype="garanzia-assicurativa")
    assert strat.name == "insurance.garanzia"


def test_insurance_dispatch_source() -> None:
    load_pack("insurance", force=True)
    strat = select_page_type_strategy(page_type="source", subtype=None)
    assert strat.name == "insurance.source"


def test_insurance_dispatch_unknown_falls_back() -> None:
    load_pack("insurance", force=True)
    strat = select_page_type_strategy(page_type="topic", subtype=None)
    assert isinstance(strat, DefaultPageTypeStrategy)
