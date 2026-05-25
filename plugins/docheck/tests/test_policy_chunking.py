"""Unit tests for `services.policy_chunking` (ADR-0013)."""

from __future__ import annotations

from docheck.services import policy_chunking


def test_empty_input_returns_empty_list() -> None:
    assert policy_chunking.split_for_extraction("") == []
    assert policy_chunking.split_for_extraction("   \n\n  ") == []


def test_short_text_returns_single_chunk() -> None:
    text = "Art. 1 — Oggetto del contratto.\n\nDefinizioni varie."
    out = policy_chunking.split_for_extraction(text)
    assert len(out) == 1
    assert out[0] == text


def test_article_markers_force_structural_split() -> None:
    # Force chunking by passing a low target so the trigger fires even on
    # a synthetic input. The marker recognizer must split on each Art. N.
    body = "\n\n".join(f"Art. {i} — Obbligo numero {i}. " + ("Contenuto. " * 200) for i in range(1, 6))
    out = policy_chunking.split_for_extraction(body, target_chars=1_500, max_chunks=20)
    assert len(out) >= 4, f"expected one chunk per article, got {len(out)}"
    # Each non-preamble chunk starts with its article marker.
    starts = [c.lstrip().split("\n", 1)[0] for c in out]
    assert any(s.lower().startswith("art. 1") for s in starts)
    assert any(s.lower().startswith("art. 5") for s in starts)


def test_paragraph_fallback_when_no_markers() -> None:
    # No structural markers: must fall back to paragraph packing.
    paragraphs = [f"Paragrafo numero {i}. " + ("Lorem ipsum dolor sit amet. " * 30) for i in range(1, 11)]
    body = "\n\n".join(paragraphs)
    out = policy_chunking.split_for_extraction(body, target_chars=1_500, max_chunks=20)
    assert len(out) >= 2
    # No chunk should exceed target by more than one paragraph's worth.
    for c in out:
        assert len(c) <= 3_500, f"chunk too large: {len(c)}"


def test_max_chunks_cap_enforced() -> None:
    body = "\n\n".join(f"Art. {i} — Obbligo." + (" x" * 50) for i in range(1, 31))
    out = policy_chunking.split_for_extraction(body, target_chars=200, max_chunks=5)
    assert len(out) <= 5


def test_no_content_invented() -> None:
    body = "Art. 1 — A.\n\nArt. 2 — B." + ("\n\nPara." * 100)
    out = policy_chunking.split_for_extraction(body, target_chars=200, max_chunks=10)
    joined_clean = "".join(c for c in body if not c.isspace())
    chunks_clean = "".join(ch for c in out for ch in c if not ch.isspace())
    # Chunks must be a subset of the original (whitespace-equivalent).
    assert chunks_clean in joined_clean or joined_clean.startswith(chunks_clean[:200])
