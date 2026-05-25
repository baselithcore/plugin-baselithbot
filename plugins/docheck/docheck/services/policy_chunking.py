"""Deterministic section splitter for long policy source texts.

ADR-0013: chunked policy extraction.

Pure functions: same input -> same output. No side effects, no I/O.

Strategy:
    1. Try structural split on article / section markers
       (``Art. N``, ``Articolo N``, ``Article N``, ``§ N``, ``Section N``,
       ``Sezione N``). Splits BEFORE each marker so the marker line stays
       attached to its content.
    2. If structural split yields fewer than 2 useful chunks, fall back to
       paragraph packing: greedy-fill blocks separated by blank lines up to
       ``target_chars``.
    3. Enforce ``max_chunks`` by merging adjacent chunks (shortest-pair
       merge) until count <= cap.
    4. Drop empty / whitespace-only chunks.

The chunks are NOT used to enforce Glass Box grounding — `_enforce_excerpts`
in ``policy_ingest`` continues to validate every extracted excerpt against
the original full source text. Chunks are purely a prompt-budgeting tool.
"""

from __future__ import annotations

import re

# Markers that introduce a new article / section. The split happens BEFORE
# the marker, so the marker line becomes the first line of the new chunk.
# Anchored to start-of-line (with optional leading whitespace) to avoid
# splitting on cross-references like "vedi Art. 1234" embedded mid-sentence.
_MARKER_RE = re.compile(
    r"(?im)^\s*(?:art(?:icol[oa])?\.?|article|§|section|sezione)\s+\d+[\w.\-]*\b",
)

_PARAGRAPH_SEP_RE = re.compile(r"\n\s*\n")

# Tunables (module-level constants, not function args, so callers can patch
# in tests without thread-local config). Public for test introspection.
DEFAULT_TARGET_CHARS = 20_000
DEFAULT_MAX_CHUNKS = 20
DEFAULT_MIN_CHARS = 500


def split_for_extraction(
    text: str,
    *,
    target_chars: int = DEFAULT_TARGET_CHARS,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    min_chars: int = DEFAULT_MIN_CHARS,
) -> list[str]:
    """Split source text into chunks suitable for per-chunk LLM extraction.

    Returns at least one chunk for any non-empty input. For very short
    inputs (``<= target_chars`` and no structural markers) returns a single
    chunk identical to the input (modulo strip).

    Invariants:
        - Concatenation of returned chunks is a subset of the original
          text (whitespace-equivalent). No content invented.
        - ``len(result) <= max_chunks``.
        - Every chunk is non-empty after strip.
    """
    body = (text or "").strip()
    if not body:
        return []

    if len(body) <= target_chars:
        return [body]

    chunks = _split_by_markers(body)
    if len(chunks) < 2:
        chunks = _split_by_paragraphs(body, target_chars=target_chars)

    chunks = _pack_small(chunks, target_chars=target_chars, min_chars=min_chars)
    chunks = _enforce_max_chunks(chunks, max_chunks=max_chunks)
    return [c for c in (s.strip() for s in chunks) if c]


def _split_by_markers(body: str) -> list[str]:
    """Split BEFORE each article/section marker match."""
    matches = list(_MARKER_RE.finditer(body))
    if not matches:
        return [body]
    cuts: list[int] = []
    for m in matches:
        # Cut at start-of-line preceding the marker.
        start = m.start()
        # Walk back to the line start.
        nl = body.rfind("\n", 0, start)
        cut = 0 if nl < 0 else nl + 1
        if not cuts or cut > cuts[-1]:
            cuts.append(cut)
    # First slice covers preamble before first marker (may be empty).
    pieces: list[str] = []
    prev = 0
    for c in cuts:
        if c > prev:
            pieces.append(body[prev:c])
        prev = c
    pieces.append(body[prev:])
    return [p for p in pieces if p.strip()]


def _split_by_paragraphs(body: str, *, target_chars: int) -> list[str]:
    """Pack paragraphs (split on blank lines) into chunks of up to target_chars."""
    paragraphs = _PARAGRAPH_SEP_RE.split(body)
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        plen = len(p) + 2  # +2 for the rejoined separator
        if buf and buf_len + plen > target_chars:
            chunks.append("\n\n".join(buf))
            buf = [p]
            buf_len = plen
        else:
            buf.append(p)
            buf_len += plen
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def _pack_small(chunks: list[str], *, target_chars: int, min_chars: int) -> list[str]:
    """Merge tiny chunks into their neighbor to avoid noisy micro-extractions."""
    if not chunks:
        return chunks
    out: list[str] = []
    for c in chunks:
        if out and len(c) < min_chars and len(out[-1]) + len(c) <= target_chars:
            out[-1] = out[-1] + "\n\n" + c
        else:
            out.append(c)
    return out


def _enforce_max_chunks(chunks: list[str], *, max_chunks: int) -> list[str]:
    """If above cap, merge the shortest adjacent pair repeatedly."""
    if max_chunks <= 0 or len(chunks) <= max_chunks:
        return chunks
    work = list(chunks)
    while len(work) > max_chunks:
        # Find adjacent pair with smallest combined length.
        best_i = 0
        best_sum = len(work[0]) + len(work[1])
        for i in range(1, len(work) - 1):
            s = len(work[i]) + len(work[i + 1])
            if s < best_sum:
                best_sum = s
                best_i = i
        merged = work[best_i] + "\n\n" + work[best_i + 1]
        work = [*work[:best_i], merged, *work[best_i + 2 :]]
    return work
