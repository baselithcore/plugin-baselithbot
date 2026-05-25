"""Step 3 smoke tests: FrontmatterSchema + Grouping rules."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from llm_wiki.domain.registry import load_pack, reset_pack_cache
from llm_wiki.domain.schema import get_schema, reset_schema_cache


@pytest.fixture(autouse=True)
def _isolate() -> Iterator[None]:
    reset_pack_cache()
    reset_schema_cache()
    yield
    reset_pack_cache()
    reset_schema_cache()


def test_insurance_schema_payload_keys() -> None:
    load_pack("insurance", force=True)
    schema = get_schema()
    source_keys = set(schema.payload_keys("source"))
    concept_keys = set(schema.payload_keys("concept"))

    assert "edizione-iso" in source_keys
    assert "codice-prodotto" in source_keys
    assert "stato" in source_keys
    assert "rango" in source_keys

    assert "prodotto" in concept_keys
    assert "richiede-logica" in concept_keys
    # source-only keys must not bleed into concept payload
    assert "edizione" not in concept_keys


def test_template_schema_minimal() -> None:
    load_pack("_template", force=True)
    schema = get_schema()
    concept_keys = set(schema.payload_keys("concept"))
    source_keys = set(schema.payload_keys("source"))
    # Universal keys (apply to every page_type).
    assert "title" in concept_keys
    assert "type" in concept_keys
    assert "tags" in concept_keys
    # `doc_register` MUST appear in every page_type payload — è il signal
    # autoritativo letto dal RAG agent per il mismatch scope-detection.
    # Senza questa chiave dichiarata, `WikiPage.to_payload` lo droppa e
    # `intent_classifier.majority_register_from_hits` cade su `unknown`.
    assert "doc_register" in concept_keys
    assert "doc_register" in source_keys
    # source-specific keys: `source_type` deve essere proiettabile per le
    # source page (consumato a ingest per derivare `doc_register`).
    assert "source_type" in source_keys
    assert "source_file" in source_keys
    assert "source_hash" in source_keys
    assert "ingested" in source_keys
    # source-only keys non devono finire nel payload concept.
    assert "source_type" not in concept_keys


def test_validate_required_field_missing() -> None:
    load_pack("insurance", force=True)
    schema = get_schema()
    errors = schema.validate("source", {"type": "source"})
    assert any("title" in e for e in errors)


def test_validate_enum_violation() -> None:
    load_pack("insurance", force=True)
    schema = get_schema()
    errors = schema.validate(
        "source",
        {
            "title": "X",
            "type": "source",
            "stato": "vigentissimo",
        },
    )
    assert any("stato" in e for e in errors)


def test_insurance_pack_declares_editions_grouping() -> None:
    pack = load_pack("insurance", force=True)
    keys = [r.key for r in pack.grouping]
    assert "editions" in keys
    rule = next(r for r in pack.grouping if r.key == "editions")
    assert rule.page_type == "source"
    assert rule.group_by == ["codice-prodotto", "edizione-iso"]
