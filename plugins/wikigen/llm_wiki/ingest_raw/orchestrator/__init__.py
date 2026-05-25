"""End-to-end ingest orchestrator: PDF → wiki ``.md`` pages.

Flow:

1. **Guard**: input path must live under ``raw/``; never write back into ``raw/``.
2. **Extract** (docling/marker/fallback) → :class:`ExtractedDocument`.
3. **Classify** (LLM, JSON-schema constrained, pack-aware enums).
4. **Plan** (LLM) → :class:`IngestPlan` (source + derived pages).
5. **Generate** in priority order — each page goes through its
   :class:`PageTypeStrategy`.
6. **Lint + critic loop** for each page.
7. **Write** (unless ``dry_run``); append to ``log.md``.
8. **Reindex** vector store if requested.

Idempotency: rerunning on the same source overwrites only when
``overwrite=True``; otherwise pages are saved with a ``.new.md`` suffix.
Critic exhaustion produces ``.needs-review.md`` — the canonical path
never gets dirty content.

Modular layout (>500 LOC budget):
- :mod:`.models`   — dataclasses + ``_timed`` ctx manager + ``RawDirWriteAttempt``
- :mod:`._guards`  — raw-dir invariants + resume / skip-unchanged
- :mod:`._page`    — per-page generate → refine → write
- :mod:`._post`    — examples cache, graph extraction, reindex
- This module      — public ``ingest_raw_file`` orchestration
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from llm_wiki.config import (
    INGEST_BATCH_CLASSIFY_PLAN,
    INGEST_MAX_CONCURRENT,
    INGEST_VENDOR,
    WIKI_ROOT,
)
from llm_wiki.ingest_raw.cache import (
    clear_ingest_state,
    compute_source_hash,
    load_cached_extract,
    load_ingest_state,
    save_cached_extract,
    save_ingest_state,
    update_page_status,
)
from llm_wiki.ingest_raw.extractor import (
    assert_extraction_tool_available,
    extract_document,
)
from llm_wiki.ingest_raw.frontmatter import slug_from_target
from llm_wiki.ingest_raw.orchestrator._guards import (
    _assert_in_raw,
    _current_pack_name,
    _try_skip_unchanged,
)
from llm_wiki.ingest_raw.orchestrator._page import _generate_and_write
from llm_wiki.ingest_raw.orchestrator._post import (
    _add_page_to_examples,
    _extract_page_graph,
    _reindex_written,
    reindex_result,
)
from llm_wiki.ingest_raw.orchestrator.models import (
    IngestResult,
    PageResult,
    RawDirWriteAttempt,
    _timed,
)
from llm_wiki.ingest_raw.output_writer import append_log, update_index
from llm_wiki.ingest_raw.planner import (
    classify_and_plan_document,
    classify_document,
    plan_document,
    reset_existing_pages_cache,
)
from llm_wiki.ingest_raw.schemas import IngestPlan, PagePlan

logger = logging.getLogger(__name__)


def ingest_raw_file(
    raw_path: Path,
    *,
    model: str | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
    reindex: bool = False,
    today: date | None = None,
    only_source_page: bool = False,
) -> IngestResult:
    raw_path = raw_path.resolve()
    _assert_in_raw(raw_path)
    assert_extraction_tool_available()

    result = IngestResult(source_path=raw_path, backend="unknown")

    source_hash = compute_source_hash(raw_path)
    result.source_hash = source_hash
    if not overwrite and not dry_run and _try_skip_unchanged(raw_path, source_hash, result):
        return result

    logger.info("extract: %s", raw_path.name)
    with _timed(result, "extract"):
        doc = load_cached_extract(source_hash)
        if doc is not None:
            logger.info("extract: cache hit (%s)", source_hash)
        else:
            doc = extract_document(raw_path)
            save_cached_extract(source_hash, doc)
    result.backend = doc.backend
    logger.info("extracted: %s", doc.to_summary())

    pack_name = _current_pack_name()
    saved_state = (
        load_ingest_state(source_hash, pack_name)
        if (pack_name and not overwrite and not dry_run)
        else None
    )
    page_status: dict[str, str] = {}
    plan: IngestPlan | None = None

    if saved_state is not None:
        try:
            plan = IngestPlan.model_validate(saved_state["plan"])
            page_status = dict(saved_state.get("page_status") or {})
            done_count = sum(1 for s in page_status.values() if s in {"written", "needs-review"})
            logger.info(
                "resume: state hit (%d/%d pagine già fatte) — skip classify+plan",
                done_count,
                len(page_status) or 1,
            )
        except Exception as exc:
            logger.warning("resume: state corrotto (%s) — restart pulito", exc)
            saved_state = None
            plan = None

    if plan is None:
        if INGEST_BATCH_CLASSIFY_PLAN:
            logger.info("classify+plan (batched): calling LLM")
            with _timed(result, "classify_plan"):
                classification, plan = classify_and_plan_document(doc, model=model)
        else:
            logger.info("classify: calling LLM")
            with _timed(result, "classify"):
                classification = classify_document(doc, model=model)
            logger.info("plan: calling LLM")
            with _timed(result, "plan"):
                plan = plan_document(doc, classification, model=model)
        if pack_name and not dry_run:
            save_ingest_state(
                source_hash,
                pack_name=pack_name,
                raw_path=str(raw_path),
                plan_dict=plan.model_dump(mode="json"),
                page_status={},
            )
    result.plan = plan

    expected = {slug_from_target(p.target_path) for p in [plan.source_page, *plan.derived_pages]}

    pages_to_gen: list[PagePlan] = [plan.source_page]
    if not only_source_page:
        pages_to_gen.extend(sorted(plan.derived_pages, key=lambda p: p.priority))

    # Per-vendor parallelism: Ollama serializes single-model inference
    # so derived pages run sequentially. OpenAI / OpenAI-compat managed
    # endpoints load-balance server-side — derived pages run in a
    # ThreadPoolExecutor capped by INGEST_MAX_CONCURRENT. Source page
    # is always sequential first: it becomes a few-shot example for
    # the derived ones (`_add_page_to_examples`) and that handoff
    # must happen before they start.
    parallel_derived = INGEST_VENDOR == "openai" and INGEST_MAX_CONCURRENT > 1

    def _process(entry: PagePlan) -> PageResult:
        prior = page_status.get(entry.target_path)
        if prior in {"written", "needs-review"} and not overwrite:
            logger.info("resume: skip %s (status=%s)", entry.target_path, prior)
            return PageResult(
                target_path=WIKI_ROOT / entry.target_path,
                status=prior,
                message=f"resume: già {prior} in run precedente",
            )
        try:
            with _timed(result, "generate"):
                return _generate_and_write(
                    entry=entry,
                    plan=plan,
                    doc=doc,
                    expected_wikilinks=expected,
                    dry_run=dry_run,
                    overwrite=overwrite,
                    today=today,
                    model=model,
                    source_hash=source_hash,
                )
        except Exception as exc:
            logger.exception("error generating %s", entry.target_path)
            result.errors.append(f"{entry.target_path}: {exc}")
            return PageResult(
                target_path=WIKI_ROOT / entry.target_path,
                status="error",
                message=str(exc),
            )

    def _post_write(entry: PagePlan, page_result: PageResult) -> None:
        result.pages.append(page_result)
        if pack_name and not dry_run:
            update_page_status(source_hash, entry.target_path, page_result.status)
        if not dry_run and page_result.status == "written":
            _add_page_to_examples(page_result.target_path)
            reset_existing_pages_cache()
        if not dry_run and page_result.status in {"written", "needs-review"}:
            _extract_page_graph(page_result.target_path)

    # Source page first (sequential — feeds few-shot to derived).
    source_entry = pages_to_gen[0]
    _post_write(source_entry, _process(source_entry))

    derived_entries = pages_to_gen[1:]
    if derived_entries and parallel_derived:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        logger.info(
            "generate: %d derived pages in parallel (workers=%d)",
            len(derived_entries),
            INGEST_MAX_CONCURRENT,
        )
        with ThreadPoolExecutor(max_workers=INGEST_MAX_CONCURRENT) as pool:
            future_map = {pool.submit(_process, e): e for e in derived_entries}
            for fut in as_completed(future_map):
                _post_write(future_map[fut], fut.result())
    else:
        for entry in derived_entries:
            _post_write(entry, _process(entry))

    if not dry_run:
        append_log(result, today=today)
        update_index(result)
    if reindex and not dry_run:
        _reindex_written(result)

    if pack_name and not dry_run and not result.errors:
        clear_ingest_state(source_hash)

    return result


__all__ = [
    "IngestResult",
    "PageResult",
    "RawDirWriteAttempt",
    "ingest_raw_file",
    "reindex_result",
]
