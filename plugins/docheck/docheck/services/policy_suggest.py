"""Suggest additional rules for an existing policy (ADR-0015).

User provides a fresh source (URL fetched or raw text) for a policy that
is already in the catalog. The LLM extracts grounded rules from the
source, then we filter out candidates that semantically overlap with
rules already present. The result is a list of **proposals** — nothing
is persisted by this service. The UI lets the operator pick which ones
to accept; accepted suggestions go through the existing `add_rule` API.

Glass Box invariant (CLAUDE.md §5): every suggestion carries a verbatim
excerpt grounded against the user-supplied source text — same machinery
used by `policy_ingest`.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import log
from . import policies as policy_svc
from . import policy_coverage, policy_ingest

MAX_SUGGESTIONS = 30


async def _gather_existing_excerpts(db: AsyncSession, pid: str, version: str) -> list[str]:
    rows = await policy_svc.list_rules(db, pid, version)
    return [str(r.get("excerpt", "")).strip() for r in rows if r.get("excerpt")]


async def suggest_more(
    db: AsyncSession,
    *,
    pid: str,
    version: str,
    source_text: str,
) -> list[dict[str, Any]]:
    """Return up to MAX_SUGGESTIONS grounded rule proposals not overlapping
    with the policy's existing rules. Does NOT persist anything."""
    if not source_text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty source text")

    existing_excerpts = await _gather_existing_excerpts(db, pid, version)

    # Reuse the same single-shot / chunked extraction path so behavior on
    # long sources matches the initial ingest exactly (ADR-0013).
    if len(source_text) > policy_ingest._CHUNK_TRIGGER_CHARS:
        _header, raw_rules = await policy_ingest._chunked_extract(source_text, hint_title=pid)
    else:
        extracted = await policy_ingest._llm_extract(source_text, hint_title=pid)
        rules = extracted.get("rules") or []
        if not isinstance(rules, list):
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "LLM rules must be a list")
        raw_rules = [r for r in rules if isinstance(r, dict)]

    # Apply the same verbatim grounding filter as ingest.
    grounded = policy_ingest._enforce_excerpts(raw_rules, source_text)

    grounding_drop = len(raw_rules) - len(grounded)
    dedup_drop = 0
    suggestions: list[dict[str, Any]] = []
    for r in grounded:
        excerpt = str(r.get("excerpt") or "").strip()
        if not excerpt:
            continue
        # Skip candidates that overlap (in either direction) with any
        # excerpt already present on the policy.
        if policy_coverage._detected_matches_extracted(excerpt, existing_excerpts):
            dedup_drop += 1
            continue
        suggestions.append(
            {
                "rule_type": r.get("rule_type", "semantic"),
                "severity": r.get("severity", "warn"),
                "excerpt": excerpt,
                "matcher": (r.get("matcher") or None),
                "rationale": str(r.get("rationale") or "")[:280] or None,
            }
        )
        if len(suggestions) >= MAX_SUGGESTIONS:
            break

    log.info(
        "policy_suggest.requested",
        policy_id=pid,
        version=version,
        existing=len(existing_excerpts),
        raw=len(raw_rules),
        grounded=len(grounded),
        grounding_drop=grounding_drop,
        dedup_drop=dedup_drop,
        returned=len(suggestions),
    )
    return suggestions


async def suggest_from_url(
    db: AsyncSession,
    *,
    pid: str,
    version: str,
    url: str,
) -> list[dict[str, Any]]:
    """Fetch the URL via the same sandboxed fetcher used by ingest, then
    delegate to `suggest_more`."""
    text, _kind = await policy_ingest._fetch_url(url)
    return await suggest_more(db, pid=pid, version=version, source_text=text)


async def suggest_from_document(
    db: AsyncSession,
    *,
    pid: str,
    version: str,
    filename: str,
    mime_type: str,
    content: bytes,
) -> list[dict[str, Any]]:
    """Parse an uploaded document via the same parsers used by ingest, then
    delegate to `suggest_more`. Symmetrical to `policy_ingest.ingest_from_document`
    minus the persistence step."""
    import contextlib
    import tempfile
    from pathlib import Path

    from .parsers import parse as parse_document

    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        chunks = parse_document(tmp_path, mime_type)
    except ValueError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    finally:
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)

    text = "\n\n".join(c.text for c in chunks if c.text)
    return await suggest_more(db, pid=pid, version=version, source_text=text)
