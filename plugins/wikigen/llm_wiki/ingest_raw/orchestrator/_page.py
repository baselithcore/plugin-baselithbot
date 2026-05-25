"""Per-page generate → refine → write helper used by the orchestrator."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from llm_wiki.config import WIKI_ROOT
from llm_wiki.ingest_raw.critic import refine_until_clean
from llm_wiki.ingest_raw.extractor import ExtractedDocument
from llm_wiki.ingest_raw.frontmatter import (
    ensure_frontmatter,
    ensure_required_sections,
    strip_markdown_wrapper,
)
from llm_wiki.ingest_raw.generator import generate_page
from llm_wiki.ingest_raw.orchestrator._guards import _assert_not_raw
from llm_wiki.ingest_raw.orchestrator.models import PageResult
from llm_wiki.ingest_raw.schemas import IngestPlan, PagePlan


def _generate_and_write(
    *,
    entry: PagePlan,
    plan: IngestPlan,
    doc: ExtractedDocument,
    expected_wikilinks: set[str],
    dry_run: bool,
    overwrite: bool,
    today: date | None,
    model: str | None,
    source_hash: str | None = None,
) -> PageResult:
    target = _resolve_target(entry.target_path)
    _assert_not_raw(target)

    md = generate_page(entry, plan=plan, doc=doc, model=model, today=today)
    md = strip_markdown_wrapper(md)
    md = ensure_frontmatter(md, entry=entry, plan=plan, today=today, source_hash=source_hash)
    md = ensure_required_sections(md, entry=entry, plan=plan)

    outcome = refine_until_clean(
        markdown=md,
        target_path=target,
        expected_wikilinks=expected_wikilinks,
        model=model,
        page_type=entry.page_type,
    )

    if dry_run:
        return PageResult(
            target_path=target,
            status="dry-run",
            lint_report=outcome.final_report,
            iterations=outcome.iterations,
            bytes_written=0,
            message="dry-run: page not written",
        )

    status, actual_path, bytes_written, message = _write_page(
        target=target,
        content=outcome.markdown,
        overwrite=overwrite,
        needs_review=outcome.exhausted,
    )

    return PageResult(
        target_path=actual_path,
        status=status,
        lint_report=outcome.final_report,
        iterations=outcome.iterations,
        bytes_written=bytes_written,
        message=message,
    )


def _write_page(
    *, target: Path, content: str, overwrite: bool, needs_review: bool
) -> tuple[str, Path, int, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    if needs_review:
        actual = target.with_suffix(".needs-review.md")
        actual.write_text(content, encoding="utf-8")
        return (
            "needs-review",
            actual,
            len(content.encode("utf-8")),
            "critic exhausted: saved with `.needs-review.md` suffix",
        )
    if target.exists() and not overwrite:
        actual = target.with_suffix(".new.md")
        actual.write_text(content, encoding="utf-8")
        return (
            "conflict",
            actual,
            len(content.encode("utf-8")),
            f"file exists, saved as {actual.name}",
        )
    target.write_text(content, encoding="utf-8")
    return ("written", target, len(content.encode("utf-8")), "ok")


def _resolve_target(target_path: str) -> Path:
    p = Path(target_path)
    if not p.is_absolute():
        p = WIKI_ROOT / target_path
    return p.resolve()
