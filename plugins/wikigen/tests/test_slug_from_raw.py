"""Regression tests for :func:`slug_from_raw`.

The 80-char truncation used to produce trailing dashes when the slice
landed inside a ``-N`` suffix. That dangling dash made the slug not
match the source-page filename (which the planner emits dash-free),
which in turn broke ``_is_pdf_pending`` → the UI banner kept showing
"N documenti in attesa" even after ingestion completed (incl.
``.needs-review.md`` outputs).
"""

from __future__ import annotations

import pytest

from llm_wiki.ingest_raw.planner import slug_from_raw


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("foo.pdf", "foo"),
        ("Foo Bar Baz.pdf", "foo-bar-baz"),
        ("foo_bar__baz.pdf", "foo-bar-baz"),
        # Trailing dash after truncation: 81-char input ends in `-1`, the
        # slice keeps `-` at pos 80; without re-strip this matched
        # ``...-v2-`` not ``...-v2`` (page slug).
        (
            "69f3af1f0b8ebe5cde42fcda_claude-building-ai-agents-in-the-enterpise-04302026_v2-1.pdf",
            "69f3af1f0b8ebe5cde42fcda-claude-building-ai-agents-in-the-enterpise-04302026-v2",
        ),
        # Empty after normalization → fallback.
        ("____.pdf", "source"),
    ],
)
def test_slug_from_raw_known_inputs(raw: str, expected: str) -> None:
    assert slug_from_raw(raw) == expected


def test_slug_from_raw_max_len_80() -> None:
    """All outputs must be <=80 chars, never have trailing dash."""
    name = "x" + ("-y" * 60) + ".pdf"  # easily >80 after normalization
    slug = slug_from_raw(name)
    assert len(slug) <= 80
    assert not slug.endswith("-")


def test_slug_from_raw_idempotent() -> None:
    """Running the slug through a synthetic round-trip stays stable."""
    raw = "a-very-long-document-name-that-might-or-might-not-be-truncated-at-80-chars-v1-2.pdf"
    slug1 = slug_from_raw(raw)
    slug2 = slug_from_raw(slug1 + ".pdf")
    assert slug1 == slug2
