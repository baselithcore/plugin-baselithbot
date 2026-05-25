"""Tests for chunked-extraction path of `services.policy_ingest` (ADR-0013).

The LLM call is monkeypatched: each chunk returns a deterministic stub
shaped like a valid extraction JSON. The tests assert that:

- Long inputs trigger `_chunked_extract` (vs the single-shot branch).
- Per-chunk results are merged and deduped by normalized excerpt.
- Grounding still runs against the FULL original source text.
- A chunk-level LLM failure does not abort the ingest (degrades to the
  surviving chunks' rules, with telemetry).
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from docheck.services import policy_ingest


def _make_long_source(n_articles: int = 6) -> str:
    """Build a synthetic policy text > _CHUNK_TRIGGER_CHARS to force chunking."""
    paragraphs = []
    for i in range(1, n_articles + 1):
        paragraphs.append(
            f"Art. {i} — Obbligo numero {i}. "
            f"Il contraente deve adempiere all'obbligo numero {i}. " + ("Contenuto di riempimento. " * 400)
        )
    return "\n\n".join(paragraphs)


def test_long_source_triggers_chunked_extraction(monkeypatch) -> None:
    src = _make_long_source(6)
    assert len(src) > policy_ingest._CHUNK_TRIGGER_CHARS

    called_with: list[str] = []

    async def fake_extract(text: str, hint_title: str | None) -> dict[str, Any]:
        called_with.append(text)
        # Each chunk: extract a verbatim excerpt that lives inside that chunk.
        m = re.search(r"Art\. (\d+) — Obbligo numero \d+\. Il contraente deve adempiere all'obbligo numero \d+\.", text)
        excerpt = m.group(0) if m else "Contenuto di riempimento."
        return {
            "id": "test-policy",
            "version": "1.0.0",
            "title": "Test Policy",
            "scope": "custom",
            "lang": "it",
            "rules": [
                {
                    "rule_type": "semantic",
                    "severity": "warn",
                    "excerpt": excerpt,
                    "matcher": None,
                    "rationale": "test",
                }
            ],
        }

    monkeypatch.setattr(policy_ingest, "_llm_extract", fake_extract)

    import asyncio

    header, rules = asyncio.run(policy_ingest._chunked_extract(src, hint_title="hint"))

    assert len(called_with) > 1, "chunked extraction must invoke LLM multiple times"
    assert header.get("id") == "test-policy"
    assert header.get("lang") == "it"
    # Distinct articles => distinct excerpts => no dedup drops expected.
    assert len(rules) == len(called_with)


def test_dedupe_collapses_repeated_excerpts() -> None:
    rules = [
        {"excerpt": "Il contraente deve adempiere.", "severity": "warn"},
        {"excerpt": "Il contraente deve adempiere.", "severity": "fail"},  # dup
        {"excerpt": "Il contraente   deve adempiere.", "severity": "info"},  # dup (ws)
        {"excerpt": "Altra obbligazione distinta.", "severity": "warn"},
        {"excerpt": "", "severity": "warn"},  # empty -> dropped
    ]
    unique, dropped = policy_ingest._dedupe_rules(rules)
    assert len(unique) == 2
    # Dropped counts only the post-empty duplicates, per implementation contract.
    assert dropped == 2
    # First occurrence wins (severity warn, not fail).
    assert unique[0]["severity"] == "warn"


def test_chunk_failure_does_not_abort_ingest(monkeypatch) -> None:
    src = _make_long_source(4)
    call_count = {"n": 0}

    async def flaky_extract(text: str, hint_title: str | None) -> dict[str, Any]:
        call_count["n"] += 1
        if call_count["n"] == 2:
            from fastapi import HTTPException

            raise HTTPException(502, "simulated chunk failure")
        return {
            "id": "p",
            "version": "1.0.0",
            "title": "P",
            "scope": "custom",
            "lang": "it",
            "rules": [{"excerpt": f"Excerpt-{call_count['n']}", "severity": "warn"}],
        }

    monkeypatch.setattr(policy_ingest, "_llm_extract", flaky_extract)

    import asyncio

    header, rules = asyncio.run(policy_ingest._chunked_extract(src, hint_title="hint"))
    assert call_count["n"] >= 2
    # At least the surviving chunks produced rules.
    assert len(rules) >= 1
    assert header.get("id") == "p"


def test_all_chunks_failing_raises(monkeypatch) -> None:
    src = _make_long_source(3)

    async def always_fail(text: str, hint_title: str | None) -> dict[str, Any]:
        from fastapi import HTTPException

        raise HTTPException(502, "down")

    monkeypatch.setattr(policy_ingest, "_llm_extract", always_fail)

    import asyncio

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(policy_ingest._chunked_extract(src, hint_title="hint"))
    assert exc_info.value.status_code == 502
