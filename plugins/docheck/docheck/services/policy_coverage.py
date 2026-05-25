"""Coverage report for policy ingest (ADR-0014).

Runs a second LLM pass on the source text that enumerates ALL distinct
obligations / prohibitions / requirements present, then compares the
result with the rules actually extracted in the first pass. Produces a
coverage ratio + a gap list of detected obligations that did not surface
as extracted rules.

Glass Box invariant (CLAUDE.md §5): every detected obligation must carry
a verbatim excerpt grounded against the original source text. Counters
that cannot be grounded are dropped silently with telemetry.

Soft-fail: any LLM/transport failure here is caught by the caller and
converted to ``coverage=None`` — the coverage report is informational and
must never block the ingest pipeline.
"""

from __future__ import annotations

import re
from typing import Any

from ..core.logging import log
from . import llm, policy_chunking

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile("[\\s\u00a0\u2010-\u2015\\-_.,;:!?\"'`()\\[\\]{}<>/\\\\]+")

_MAX_GAPS_REPORTED = 20
_DETECT_MAX_TOKENS = 4096

_DETECT_PROMPT = """You are a compliance taxonomy enumerator. Read the source
text and list EVERY distinct obligation, prohibition, or substantive
requirement it contains. Coverage matters more than depth: a complete list
of short pointers beats a small list of long descriptions.

ABSOLUTE RULES:
1. Each `excerpt` MUST be a contiguous, VERBATIM substring of the source
   text (no paraphrasing, no merging). 8-40 words typical.
2. `label` is a 3-10 word human-readable identifier in the source
   language (e.g. "termine massimo per la consegna").
3. `severity_hint`: 'fail' (mandatory / shall / deve), 'warn' (should /
   dovrebbe), 'info' (informational). Pick conservatively.
4. Cover the entire source. Do NOT stop after a few items. Aim for the
   real count: a Civil Code chapter may contain dozens of obligations.
5. Skip preambles, definitions, recitals, page furniture, signatures.
6. Do NOT invent obligations not present in the source.

OUTPUT — STRICT JSON only, no prose, no markdown fences:
{
  "obligations": [
    {
      "label": "<short identifier>",
      "excerpt": "<verbatim substring from source>",
      "severity_hint": "fail|warn|info"
    }
  ]
}

Determinism: same input -> same output."""


def _normalize_strict(s: str) -> str:
    return _WS_RE.sub(" ", (s or "").strip()).lower()


def _normalize_loose(s: str) -> str:
    return _PUNCT_RE.sub("", (s or "")).lower()


def _is_grounded(excerpt: str, source_text: str) -> bool:
    """Verbatim substring check, two-tier (strict whitespace + loose punct)."""
    if not excerpt or not source_text:
        return False
    a_strict = _normalize_strict(excerpt)
    src_strict = _normalize_strict(source_text)
    if a_strict and a_strict in src_strict:
        return True
    a_loose = _normalize_loose(excerpt)
    src_loose = _normalize_loose(source_text)
    return bool(a_loose) and len(a_loose) >= 12 and a_loose in src_loose


def _detected_matches_extracted(detected_excerpt: str, extracted_excerpts: list[str]) -> bool:
    """Loose substring match in either direction across the extracted set."""
    d = _normalize_loose(detected_excerpt)
    if not d or len(d) < 8:
        return False
    for e in extracted_excerpts:
        n = _normalize_loose(e)
        if not n:
            continue
        if d in n or n in d:
            return True
    return False


async def _detect_obligations_chunk(chunk_text: str) -> list[dict[str, Any]]:
    """One LLM pass per chunk. Returns raw obligation dicts (un-grounded)."""
    user = (
        f"Source text (verbatim):\n---\n{chunk_text}\n---\n\n"
        "Enumerate every distinct obligation. Copy excerpts exactly. "
        "Return JSON only."
    )
    out = await llm.chat_json_resilient(
        system=_DETECT_PROMPT,
        user=user,
        temperature=0.0,
        max_tokens=_DETECT_MAX_TOKENS,
    )
    if not isinstance(out, dict):
        return []
    items = out.get("obligations") or []
    return [x for x in items if isinstance(x, dict)]


def _dedupe_obligations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedup by normalized excerpt. First occurrence wins."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for it in items:
        ex = str(it.get("excerpt") or "").strip()
        if not ex:
            continue
        key = _normalize_strict(ex)
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)
    return unique


async def compute_coverage(
    *,
    source_text: str,
    extracted_excerpts: list[str],
    chunk_trigger_chars: int,
) -> dict[str, Any]:
    """Compute the coverage report.

    Returns a dict with shape:
        {
          "extracted_count": int,
          "detected_count": int,
          "coverage_ratio": float in [0, 1],
          "gaps": [ {"label", "excerpt", "severity_hint"} ],
        }

    Raises whatever the LLM service raises — caller is expected to soft-fail.
    """
    if len(source_text) > chunk_trigger_chars:
        chunks = policy_chunking.split_for_extraction(source_text)
    else:
        chunks = [source_text]

    detected_raw: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        try:
            detected_raw.extend(await _detect_obligations_chunk(chunk))
        except Exception as exc:
            # Per-chunk soft failure: log and continue.
            log.warning(
                "policy_ingest.coverage_chunk_failed",
                chunk_index=idx,
                chunk_count=len(chunks),
                error=str(exc),
            )

    detected_unique = _dedupe_obligations(detected_raw)
    detected_grounded = [d for d in detected_unique if _is_grounded(d.get("excerpt", ""), source_text)]

    extracted_count = len(extracted_excerpts)
    detected_count = len(detected_grounded)

    # Build gaps: detected obligations that no extracted excerpt covers.
    gaps: list[dict[str, Any]] = []
    for d in detected_grounded:
        ex = str(d.get("excerpt") or "")
        if _detected_matches_extracted(ex, extracted_excerpts):
            continue
        gaps.append(
            {
                "label": str(d.get("label") or "")[:120],
                "excerpt": ex,
                "severity_hint": str(d.get("severity_hint") or "warn"),
            }
        )
        if len(gaps) >= _MAX_GAPS_REPORTED:
            break

    if detected_count == 0:
        ratio = 1.0 if extracted_count else 0.0
    else:
        ratio = max(0.0, min(1.0, extracted_count / detected_count))

    return {
        "extracted_count": extracted_count,
        "detected_count": detected_count,
        "coverage_ratio": round(ratio, 3),
        "gaps": gaps,
    }
