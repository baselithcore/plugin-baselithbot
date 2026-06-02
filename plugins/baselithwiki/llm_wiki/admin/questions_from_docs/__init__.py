"""Doc-grounded starter-question generator (post-ingest, fingerprint-gated).

Scope
-----
Scaffold-time prompt synthesis (:mod:`llm_wiki.admin.prompt_synthesizer`)
produces ``pack.yaml.ui.suggested_questions`` from name + label +
description alone — it cannot see the actual documents because the
ingest pipeline has not run yet. Those generic chips work for empty
demos but feel disconnected once a user uploads real material in the
wizard's "Documenti" step.

This package closes the loop. After every successful ingest the hook
samples the just-produced source pages, asks the configured LLM to
propose 3-5 starter questions that span complementary intent
archetypes (definitional, procedural, comparative, overview /
synthesis) — modern RAG UX practice for empty-state chips — and
overwrites ``pack.yaml.ui.suggested_questions``. A marker file
(``prompts/.questions.docs.meta.json``) records the *doc-set
fingerprint* so the generator only refires when the corpus actually
changes (new file uploaded, page removed) — re-ingest of the same
docs is a no-op.

Design invariants
-----------------
* **Best-effort**. Any failure (LLM unreachable, JSON parse error,
  empty vault) leaves the existing questions untouched. No exception
  ever bubbles to the caller (ingest runner).
* **Fingerprint-gated**. The marker stores ``fingerprint`` (sha256
  over sorted source-folder relative paths). Identical fingerprint
  on a later finalize → skip. Different fingerprint (new doc, deleted
  doc) → drop marker + re-fire. Empty corpus → never fire.
* **Race-safe**. Marker write uses ``O_CREAT | O_EXCL`` so concurrent
  worker threads finalizing in the same batch cannot race-call the
  model; the loser gets ``FileExistsError`` and bails out.
* **Pack-agnostic**. No vertical knowledge: reuses the running pack's
  ``page_types`` taxonomy + a deterministic page-sampling strategy
  that prefers the configured *source* folder when present and falls
  back to whichever folders actually contain pages.
* **Schema-compatible**. Emits :class:`SuggestedQuestion` instances
  from the existing synth model so the
  ``pack.yaml.ui.suggested_questions`` shape and the React
  ``EmptyState`` chip renderer keep working unchanged.

Modular layout (>500 LOC budget):
- :mod:`._sampler` — pick representative pages + clean excerpt
- :mod:`._llm`     — meta-prompt + LLM call + JSON validation
- This module     — orchestrator + fingerprint + marker / pack.yaml I/O
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_wiki.admin.prompt_synthesizer.models import SynthesisError
from llm_wiki.admin.prompt_synthesizer.vendor import _synthesis_vendor
from llm_wiki.admin.questions_from_docs._llm import call_llm
from llm_wiki.admin.questions_from_docs._sampler import (
    _ordered_page_folders,
    sample_pages,
)
from llm_wiki.admin.scaffold.synthesis import _patch_pack_yaml_with_synthesis
from llm_wiki.admin.vault_seed import read_pack_data

logger = logging.getLogger(__name__)

MARKER_FILENAME = ".questions.docs.meta.json"


@dataclass(slots=True)
class RegenerationResult:
    """Outcome of a generation attempt — surfaced by the CLI / admin path."""

    applied: bool
    skipped_reason: str | None
    questions_written: int
    model: str | None
    sampled_pages: int
    fingerprint: str | None = None
    warning: str | None = None


def regenerate_questions_from_docs(
    pack_dir: Path,
    wiki_dir: Path,
    *,
    force: bool = False,
    min_questions: int | None = None,
    max_questions: int | None = None,
    max_pages: int | None = None,
    max_chars_per_page: int | None = None,
) -> RegenerationResult:
    """Generate doc-grounded suggested questions and patch ``pack.yaml``.

    Returns a :class:`RegenerationResult`. Never raises — failure paths
    set ``applied=False`` with a populated ``skipped_reason`` or
    ``warning`` so the caller can log/report without try/except.

    Fingerprint logic
    -----------------
    The marker file ``<pack_dir>/prompts/.questions.docs.meta.json``
    records the sha256 of the sorted source-folder relative paths.
    On a subsequent call the current fingerprint is compared:

    * fingerprint matches → skip (same corpus, no need to re-LLM).
    * fingerprint differs → drop the old marker and regenerate
      (new doc uploaded, page removed, page renamed).
    * marker missing → regenerate.

    ``force=True`` bypasses the fingerprint check entirely.

    Numeric parameters that default to ``None`` are resolved from
    :mod:`llm_wiki.config`.
    """
    from llm_wiki import config as _cfg

    min_q = min_questions if min_questions is not None else _cfg.QUESTIONS_FROM_DOCS_MIN
    max_q = max_questions if max_questions is not None else _cfg.QUESTIONS_FROM_DOCS_MAX
    page_budget = (
        max_pages if max_pages is not None else _cfg.QUESTIONS_FROM_DOCS_MAX_PAGES
    )
    char_budget = (
        max_chars_per_page
        if max_chars_per_page is not None
        else _cfg.QUESTIONS_FROM_DOCS_MAX_CHARS_PER_PAGE
    )
    min_q = max(2, min(5, int(min_q)))
    max_q = max(min_q, min(5, int(max_q)))

    pack_yaml = pack_dir / "pack.yaml"
    if not pack_yaml.is_file():
        return _skipped(f"pack.yaml not found at {pack_yaml}")

    pack_data = read_pack_data(pack_dir)
    if not pack_data:
        return _skipped("pack.yaml is empty or unreadable")

    page_types = list(pack_data.get("page_types") or [])
    fingerprint = compute_doc_fingerprint(wiki_dir, page_types)
    if not fingerprint:
        return _skipped(
            f"no source pages under {wiki_dir} — nothing to ground questions on"
        )

    marker_path = pack_dir / "prompts" / MARKER_FILENAME
    existing = _read_marker(marker_path)
    if not force and existing is not None:
        prev_fp = existing.get("fingerprint")
        if prev_fp == fingerprint:
            return _skipped(
                f"marker fingerprint matches current doc set ({fingerprint[:12]}…) — no rerun"
            )
        # Corpus changed since last run: drop the stale marker so the
        # O_EXCL re-create below acts as the single race-winning lock.
        _drop_marker(marker_path)

    if force:
        _drop_marker(marker_path)

    samples = sample_pages(
        wiki_dir,
        page_types=page_types,
        max_pages=page_budget,
        max_chars=char_budget,
    )
    if not samples:
        # Fingerprint says corpus is non-empty but the sampler returned
        # nothing — defensive: malformed pages, all-incomplete suffixes,
        # etc. Skip without touching the marker.
        return _skipped(
            f"sampler returned 0 pages despite fingerprint {fingerprint[:12]}…"
        )

    marker_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic marker-as-lock. Concurrent workers race-safely: only the
    # first one proceeds; the rest get FileExistsError and bail out.
    placeholder = {
        "status": "in_progress",
        "fingerprint": fingerprint,
        "ts": _utc_now_iso(),
    }
    try:
        fd = os.open(marker_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return RegenerationResult(
            applied=False,
            skipped_reason="another worker beat us to the marker",
            questions_written=0,
            model=None,
            sampled_pages=len(samples),
            fingerprint=fingerprint,
        )
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(placeholder, fh, ensure_ascii=False)

    try:
        questions, model_id = call_llm(
            pack_data=pack_data,
            samples=samples,
            min_questions=min_q,
            max_questions=max_q,
        )
    except SynthesisError as exc:
        _drop_marker(marker_path)
        logger.warning("[questions-from-docs] LLM failed: %s", exc)
        return RegenerationResult(
            applied=False,
            skipped_reason=None,
            questions_written=0,
            model=None,
            sampled_pages=len(samples),
            fingerprint=fingerprint,
            warning=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 — best-effort hook
        _drop_marker(marker_path)
        logger.exception("[questions-from-docs] unexpected failure")
        return RegenerationResult(
            applied=False,
            skipped_reason=None,
            questions_written=0,
            model=None,
            sampled_pages=len(samples),
            fingerprint=fingerprint,
            warning=f"unexpected: {exc}",
        )

    try:
        _patch_pack_yaml_with_synthesis(
            pack_yaml=pack_yaml,
            disclaimer=str((pack_data.get("ui") or {}).get("disclaimer") or ""),
            subtypes=pack_data.get("subtypes") or {},
            suggested_questions=[q.model_dump() for q in questions],
        )
    except OSError as exc:
        _drop_marker(marker_path)
        logger.error("[questions-from-docs] pack.yaml patch failed: %s", exc)
        return RegenerationResult(
            applied=False,
            skipped_reason=None,
            questions_written=0,
            model=model_id,
            sampled_pages=len(samples),
            fingerprint=fingerprint,
            warning=f"persist failed: {exc}",
        )

    meta = {
        "status": "done",
        "fingerprint": fingerprint,
        "model": model_id,
        "vendor": _synthesis_vendor(),
        "questions_count": len(questions),
        "sampled_pages": [s.relative_path for s in samples],
        "ts": _utc_now_iso(),
    }
    try:
        marker_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:  # marker write best-effort — already patched
        logger.warning("[questions-from-docs] marker finalize failed: %s", exc)

    logger.info(
        "[questions-from-docs] wrote %d questions to %s via %s (fp=%s)",
        len(questions),
        pack_yaml,
        model_id,
        fingerprint[:12],
    )
    return RegenerationResult(
        applied=True,
        skipped_reason=None,
        questions_written=len(questions),
        model=model_id,
        sampled_pages=len(samples),
        fingerprint=fingerprint,
    )


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


def compute_doc_fingerprint(wiki_dir: Path, page_types: list[dict[str, Any]]) -> str:
    """Sha256 over sorted source-folder relative paths.

    Source folder set is whatever ``_ordered_page_folders`` returns as
    *source-like* (substring match on ``source`` / ``fonti`` /
    ``document`` in id or folder name) — falls back to the full
    page-type folder set when no source-like folder is configured.

    Empty corpus → empty string (caller treats this as
    "nothing to ground on"). Re-ingest of the same files yields the
    same fingerprint; uploading a new doc changes the set of source
    page slugs, which changes the fingerprint.
    """
    if not wiki_dir.is_dir():
        return ""
    ordered = _ordered_page_folders(page_types)
    if not ordered:
        return ""
    # Source-like folders come first in the ordering. Use only those
    # if present; otherwise the whole set (lets non-source-only packs
    # still benefit from change detection).
    source_folders = [folder for folder, _ in ordered if folder]
    if any(
        f for f in source_folders if "source" in f or "fonti" in f or "document" in f
    ):
        source_folders = [
            f
            for f in source_folders
            if "source" in f or "fonti" in f or "document" in f
        ]

    paths: list[str] = []
    for folder in source_folders:
        folder_path = wiki_dir / folder
        if not folder_path.is_dir():
            continue
        for md_path in folder_path.glob("*.md"):
            name = md_path.name
            lower = name.lower()
            if name in {"index.md", "log.md"}:
                continue
            if lower.endswith(".new.md") or lower.endswith(".needs-review.md"):
                continue
            paths.append(md_path.relative_to(wiki_dir).as_posix())
    if not paths:
        return ""
    paths.sort()
    h = hashlib.sha256()
    for p in paths:
        h.update(p.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_marker(marker_path: Path) -> dict[str, Any] | None:
    try:
        raw = marker_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _skipped(reason: str) -> RegenerationResult:
    return RegenerationResult(
        applied=False,
        skipped_reason=reason,
        questions_written=0,
        model=None,
        sampled_pages=0,
    )


def _drop_marker(marker_path: Path) -> None:
    try:
        marker_path.unlink()
    except OSError:
        pass


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "MARKER_FILENAME",
    "RegenerationResult",
    "compute_doc_fingerprint",
    "regenerate_questions_from_docs",
]
