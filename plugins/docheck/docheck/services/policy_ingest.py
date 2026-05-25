"""Ingest a policy from an external source (URL or document file).

Pipeline:
    1. Acquire raw text:
       - URL: fetch (HTML or YAML), strip markup if HTML.
       - File: parse via existing parsers (PDF / DOCX / XLSX / MD / TXT).
    2. If the payload is already a YAML policy spec, import it directly.
    3. Otherwise call the LLM to extract a structured policy
       (id/title/scope/lang + rules) and persist via `policy_svc.create_policy`.

The LLM extraction is grounded: every rule must include a verbatim `excerpt`
from the source text — enforced by post-validation. Failures degrade to a
single placeholder rule + the operator can refine in the UI.
"""

from __future__ import annotations

import contextlib
import re
import uuid
from typing import Any

import httpx
import yaml
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import log
from . import llm, policy_chunking, policy_coverage
from . import policies as policy_svc
from .parsers import parse as parse_document

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile("[\\s\u00a0\u2010-\u2015\\-_.,;:!?\"'`()\\[\\]{}<>/\\\\]+")
_MAX_TEXT_CHARS = 60_000  # cap per-chunk LLM context (single-shot fallback)
_MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024  # 10MB hard cap

# ADR-0013: when source exceeds this size, switch to chunked extraction
# instead of silently truncating a single prompt. Picked below
# `policy_chunking.DEFAULT_TARGET_CHARS * 2` so we trigger chunking well
# before the single-shot cap to preserve extraction quality.
_CHUNK_TRIGGER_CHARS = 40_000

_SYSTEM_PROMPT = """You are a senior compliance analyst extracting actionable rules
from regulatory, contractual, or policy text. Your output is consumed by an
automated verifier that enforces verbatim grounding — any fabricated content is
rejected.

ABSOLUTE RULES:
1. Every rule's `excerpt` MUST be a contiguous, VERBATIM substring of the source
   text (no paraphrasing, no summarization, no merging of distant sentences,
   no translation). Copy exact characters including punctuation.
2. Pick the most operational, testable obligations or prohibitions present in
   the source. Skip preambles, definitions, recitals, signatures, page furniture.
3. Each excerpt should be self-contained (one sentence or short clause,
   typically 8-60 words). No sentence fragments, no ellipsis.
4. If the source contains fewer than 3 actionable obligations, return only what
   is present. NEVER invent rules to reach a quota.
5. Choose `rule_type` honestly:
   - presence: document/clause/section MUST be present
   - absence: clause/term MUST NOT appear
   - format: structural/format requirement (date, signature, ID format)
   - numeric_limit: explicit numeric threshold (deadline, percentage, amount)
   - semantic: substantive obligation requiring meaning-level checks
6. Choose `severity` from the source's own language:
   - fail: mandatory ("must", "shall", "deve", penalties, voidness)
   - warn: recommended ("should", "dovrebbe", best practice)
   - info: informational, non-binding context
7. `matcher`: a conservative regex ONLY when the rule has a clear lexical
   signal (specific phrase, ID pattern, date format). Otherwise null.

OUTPUT — STRICT JSON, no prose, no markdown fences:
{
  "id": "<lowercase slug from document title, [a-z0-9_.-], <=48 chars>",
  "version": "1.0.0",
  "title": "<human-readable title from document>",
  "scope": "custom",
  "lang": "<ISO 639-1 of source language: it, en, fr, de, es>",
  "rules": [
    {
      "rule_type": "presence|absence|format|numeric_limit|semantic",
      "severity": "fail|warn|info",
      "excerpt": "<verbatim substring from source>",
      "matcher": "<regex or null>",
      "rationale": "<one short sentence in source language>"
    }
  ]
}

Determinism: same input -> same output. Conservative. Quality over quantity:
3 well-grounded rules beat 10 fabricated ones."""


def _strip_html(html: str) -> str:
    text = _HTML_TAG_RE.sub(" ", html)
    return _WS_RE.sub(" ", text).strip()


def _clip(text: str) -> str:
    if len(text) <= _MAX_TEXT_CHARS:
        return text
    head = text[: _MAX_TEXT_CHARS - 200]
    return head + "\n[...TRUNCATED...]"


async def _fetch_url(url: str) -> tuple[str, str]:
    """Return (text, content_type). Blocks non-http schemes; enforces size cap."""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only http/https URLs are allowed")
    try:
        async with (
            httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers={"User-Agent": "doCheck-PolicyIngest/0.1"},
            ) as client,
            client.stream("GET", url) as resp,
        ):
            resp.raise_for_status()
            ctype = (resp.headers.get("content-type") or "").lower()
            buf = bytearray()
            async for chunk in resp.aiter_bytes():
                buf.extend(chunk)
                if len(buf) > _MAX_DOWNLOAD_BYTES:
                    raise HTTPException(413, "Remote payload too large (>10MB)")
            raw = bytes(buf)
    except httpx.HTTPError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Fetch failed: {exc}") from exc

    if "yaml" in ctype or url.lower().endswith((".yml", ".yaml")):
        return raw.decode("utf-8", errors="replace"), "yaml"
    if "html" in ctype:
        return _strip_html(raw.decode("utf-8", errors="replace")), "html"
    if "json" in ctype:
        return raw.decode("utf-8", errors="replace"), "json"
    # Plain text default
    return raw.decode("utf-8", errors="replace"), "text"


def _looks_like_policy_yaml(text: str) -> bool:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return False
    return isinstance(data, dict) and "rules" in data and "id" in data


def _norm_loose(s: str) -> str:
    """Aggressive normalization for PDF-vs-LLM excerpt matching.
    Strips punctuation/dashes/whitespace + lowercases. Defeats line-break
    artifacts, hyphenation, smart quotes."""
    return _PUNCT_RE.sub("", s).lower()


def _enforce_excerpts(rules: list[dict[str, Any]], source_text: str) -> list[dict[str, Any]]:
    """Keep rules whose excerpt is recoverable from source text.
    Two-tier match: strict whitespace-collapsed, then loose punctuation-stripped.
    Loose match accepts PDF artifacts (hyphenation, line breaks mid-phrase)
    while still rejecting hallucinations."""
    norm_strict = _WS_RE.sub(" ", source_text).lower()
    norm_loose = _norm_loose(source_text)
    kept: list[dict[str, Any]] = []
    for r in rules:
        excerpt = (r.get("excerpt") or "").strip()
        if not excerpt:
            continue
        ex_strict = _WS_RE.sub(" ", excerpt).lower()
        if ex_strict in norm_strict:
            kept.append(r)
            continue
        ex_loose = _norm_loose(excerpt)
        if len(ex_loose) >= 12 and ex_loose in norm_loose:
            kept.append(r)
            continue
        log.warning("policy_ingest.excerpt_not_in_source", excerpt=excerpt[:120])
    return kept


def _slugify(s: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9_.-]+", "-", s.lower()).strip("-.")
    slug = re.sub(r"-{2,}", "-", slug)[:48]
    return slug or fallback


async def _llm_extract(source_text: str, hint_title: str | None) -> dict[str, Any]:
    """Deterministic extraction (temperature=0). Resilient JSON repair on parse
    failure. Caller is responsible for verbatim-excerpt grounding enforcement."""
    user = (
        f"Source title hint: {hint_title or 'unknown'}\n\n"
        f"Source text (verbatim):\n---\n{_clip(source_text)}\n---\n\n"
        "Extract rules following the absolute rules in the system prompt. "
        "Copy excerpts exactly. Return JSON only."
    )
    try:
        out = await llm.chat_json_resilient(
            system=_SYSTEM_PROMPT,
            user=user,
            temperature=0.0,
            max_tokens=4096,
        )
    except Exception as exc:
        log.error("policy_ingest.llm_failed", error=str(exc))
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"LLM extraction failed: {exc}. Verify the LLM runtime is reachable.",
        ) from exc
    if not isinstance(out, dict) or "rules" not in out:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "LLM returned invalid policy shape")
    return out


def _dedupe_rules(rules: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Dedup by normalized excerpt. First occurrence wins. Returns (unique, dropped)."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    dropped = 0
    for r in rules:
        excerpt = str(r.get("excerpt") or "").strip()
        if not excerpt:
            continue
        key = _WS_RE.sub(" ", excerpt).lower()
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        unique.append(r)
    return unique, dropped


async def _chunked_extract(source_text: str, hint_title: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run per-chunk extraction over a long source, merging rules.

    Returns:
        (header, rules) where header carries the document-level fields
        (id/title/lang/version) taken from the first successful chunk, and
        ``rules`` is the merged+deduped list of raw rule dicts (still
        un-grounded — caller must run `_enforce_excerpts`).
    """
    chunks = policy_chunking.split_for_extraction(source_text)
    if not chunks:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty source text")

    header: dict[str, Any] = {}
    merged_rules: list[dict[str, Any]] = []
    per_chunk_counts: list[int] = []
    failures = 0

    for idx, chunk in enumerate(chunks):
        try:
            extracted = await _llm_extract(chunk, hint_title=hint_title)
        except HTTPException as exc:
            # One chunk's failure should not abort the whole ingest; record
            # and continue. If every chunk fails, the final grounded-count
            # check in `ingest` will surface a clear 4xx/5xx.
            failures += 1
            log.warning(
                "policy_ingest.chunk_extract_failed",
                chunk_index=idx,
                chunk_count=len(chunks),
                detail=exc.detail,
            )
            per_chunk_counts.append(0)
            continue

        if not header:
            header = {k: extracted.get(k) for k in ("id", "version", "title", "scope", "lang") if extracted.get(k)}
        chunk_rules = [r for r in (extracted.get("rules") or []) if isinstance(r, dict)]
        merged_rules.extend(chunk_rules)
        per_chunk_counts.append(len(chunk_rules))

    unique, dedup_drop = _dedupe_rules(merged_rules)
    log.info(
        "policy_ingest.chunked_extraction",
        chunk_count=len(chunks),
        chunk_failures=failures,
        rules_per_chunk=per_chunk_counts,
        rules_merged=len(merged_rules),
        rules_unique=len(unique),
        dedup_drop=dedup_drop,
    )
    if failures == len(chunks):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "LLM extraction failed on every chunk. Verify the LLM runtime.",
        )
    return header, unique


async def ingest(
    db: AsyncSession,
    *,
    source_text: str,
    hint_title: str,
    source_uri: str,
    created_by: str,
    override_id: str | None = None,
    override_version: str | None = None,
) -> dict[str, Any]:
    """Run extraction → persist policy. Returns PolicyOut dict."""
    if not source_text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty source text")

    # Fast path: already a policy YAML
    if _looks_like_policy_yaml(source_text):
        out = await policy_svc.import_yaml(
            db,
            content=source_text,
            created_by=created_by,
            override_active=False,
        )
        return out

    # ADR-0013: chunked extraction for long sources avoids silent truncation.
    if len(source_text) > _CHUNK_TRIGGER_CHARS:
        header, rules_raw = await _chunked_extract(source_text, hint_title=hint_title)
    else:
        extracted = await _llm_extract(source_text, hint_title=hint_title)
        raw_rules = extracted.get("rules") or []
        if not isinstance(raw_rules, list):
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "LLM rules must be a list")
        header = {k: extracted.get(k) for k in ("id", "version", "title", "scope", "lang") if extracted.get(k)}
        rules_raw = [r for r in raw_rules if isinstance(r, dict)]

    # Glass Box invariant: every excerpt must be a verbatim substring of the
    # FULL original source (not just the chunk it came from). This is what
    # the auditor / UI will surface; chunks are a prompt-budgeting detail.
    rules = _enforce_excerpts(rules_raw, source_text)
    submitted = sum(1 for r in rules_raw if r.get("excerpt"))
    grounded = len(rules)
    log.info(
        "policy_ingest.grounding_stats",
        submitted_rules=submitted,
        grounded_rules=grounded,
        drop_rate=round(1 - (grounded / submitted), 3) if submitted else 0,
        chunked=len(source_text) > _CHUNK_TRIGGER_CHARS,
    )
    if not rules:
        # Refuse: zero verbatim-grounded rules. Don't fabricate a placeholder
        # — that masks LLM hallucination and pollutes the policy catalog.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Could not extract any verbatim-grounded rules from the source. "
            f"LLM produced {submitted} rule(s) but none matched the source text. "
            "Try a clearer source document or create rules manually.",
        )

    pid = override_id or _slugify(
        str(header.get("id") or hint_title),
        fallback=f"pol-{uuid.uuid4().hex[:8]}",
    )
    version = override_version or str(header.get("version") or "1.0.0").strip() or "1.0.0"
    title = (str(header.get("title") or hint_title)).strip() or pid
    lang = str(header.get("lang") or "it").strip()[:8] or "it"

    out = await policy_svc.create_policy(
        db,
        pid=pid,
        version=version,
        title=title,
        scope="custom",
        lang=lang,
        active=False,
        rules=[
            {
                "rule_type": r.get("rule_type", "semantic"),
                "severity": r.get("severity", "warn"),
                "excerpt": str(r.get("excerpt", "")).strip(),
                "matcher": (r.get("matcher") or None),
            }
            for r in rules
        ],
        created_by=created_by,
    )
    # Persist source URI for traceability
    from ..db.models import Policy

    p = await db.get(Policy, (pid, version))
    if p:
        p.source_uri = source_uri

    # ADR-0014: coverage report (soft-fail — informational, never gate ingest).
    extracted_excerpts = [str(r.get("excerpt", "")).strip() for r in rules]
    try:
        coverage = await policy_coverage.compute_coverage(
            source_text=source_text,
            extracted_excerpts=extracted_excerpts,
            chunk_trigger_chars=_CHUNK_TRIGGER_CHARS,
        )
        log.info(
            "policy_ingest.coverage_report",
            extracted=coverage["extracted_count"],
            detected=coverage["detected_count"],
            ratio=coverage["coverage_ratio"],
            gaps=len(coverage["gaps"]),
        )
        out = {**out, "coverage": coverage}
    except Exception as exc:
        log.warning("policy_ingest.coverage_failed", error=str(exc))
        out = {**out, "coverage": None}
    return out


async def ingest_from_url(
    db: AsyncSession,
    *,
    url: str,
    created_by: str,
) -> dict[str, Any]:
    text, _kind = await _fetch_url(url)
    return await ingest(
        db,
        source_text=text,
        hint_title=url,
        source_uri=url,
        created_by=created_by,
    )


async def ingest_from_document(
    db: AsyncSession,
    *,
    filename: str,
    mime_type: str,
    content: bytes,
    created_by: str,
) -> dict[str, Any]:
    """Parse the uploaded file via the document parsers, then run LLM extraction."""
    import tempfile
    from pathlib import Path

    # Plain YAML/text shortcut
    if filename.lower().endswith((".yaml", ".yml")) or "yaml" in mime_type:
        return await policy_svc.import_yaml(
            db,
            content=content,
            created_by=created_by,
            override_active=False,
        )

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
    return await ingest(
        db,
        source_text=text,
        hint_title=Path(filename).stem,
        source_uri=f"file://{filename}",
        created_by=created_by,
    )
