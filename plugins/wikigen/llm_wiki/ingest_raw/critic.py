"""Critic loop: re-invoke the LLM to fix pages that fail linting.

Pattern: ``generate → lint → if errors (severity=error) → refine → lint → ...``
up to ``MAX_ITER``. If errors remain, the page is saved with the
``.needs-review.md`` suffix and the orchestrator carries on — never write
dirty content under the canonical path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from llm_wiki.config import INGEST_CRITIC_MAX_ITER
from llm_wiki.ingest_raw.frontmatter import strip_markdown_wrapper
from llm_wiki.ingest_raw.linter import LintReport, lint_wiki_text
from llm_wiki.ingest_raw.llm_client import generate_text
from llm_wiki.ingest_raw.prompts import refine_bundle

logger = logging.getLogger(__name__)


# Tunable via `INGEST_CRITIC_MAX_ITER` (config.py). Default 1: fail-fast,
# marca `.needs-review.md` invece di insistere. Iter aggiuntive bruciano
# ~30-90s/page su Ollama e raramente sistemano ERROR strutturali
# (frontmatter mancante, propedeuticità non inferibili dal PDF, ecc.).
MAX_ITER_DEFAULT = INGEST_CRITIC_MAX_ITER

# Source pages hanno struttura più semplice (riassunto fonte raw, niente
# corpo normativo) e gli stub deterministici di `ensure_required_sections`
# coprono la quasi totalità degli ERROR strutturali. Cap a 1 risparmia
# fino a 1 round-trip LLM/source page (~30-90s su Ollama).
_MAX_ITER_BY_PAGE_TYPE = {"source": 1}


def _max_iter_for(page_type: str | None) -> int:
    if page_type and page_type in _MAX_ITER_BY_PAGE_TYPE:
        return _MAX_ITER_BY_PAGE_TYPE[page_type]
    return MAX_ITER_DEFAULT


class CriticExhausted(RuntimeError):
    """Critic exhausted its retries without removing all errors."""


@dataclass
class RefineOutcome:
    markdown: str
    final_report: LintReport
    iterations: int
    exhausted: bool


def refine_until_clean(
    *,
    markdown: str,
    target_path: Path,
    expected_wikilinks: set[str] | None = None,
    max_iter: int | None = None,
    model: str | None = None,
    page_type: str | None = None,
) -> RefineOutcome:
    if max_iter is None:
        max_iter = _max_iter_for(page_type)
    current = markdown

    for i in range(1, max_iter + 1):
        report = lint_wiki_text(current, path=target_path, expected_wikilinks=expected_wikilinks)
        if not report.has_errors:
            logger.info("critic: page clean after %d iter (warn=%d)", i, len(report.issues))
            return RefineOutcome(
                markdown=current, final_report=report, iterations=i, exhausted=False
            )
        feedback = report.to_prompt_feedback()
        errors = [iss for iss in report.issues if iss.severity.value == "error"]
        logger.info(
            "critic iter %d (%s): %d errors. Refining…",
            i,
            target_path.name,
            len(errors),
        )
        for iss in errors:
            code = getattr(iss, "code", "?")
            msg = getattr(iss, "message", str(iss))
            logger.info("  · [%s] %s", code, msg[:200])
        bundle = refine_bundle(current_markdown=current, lint_feedback=feedback)
        current = generate_text(messages=bundle.as_messages(), model=model, temperature=0.15)
        current = strip_markdown_wrapper(current)

    report = lint_wiki_text(current, path=target_path, expected_wikilinks=expected_wikilinks)
    return RefineOutcome(
        markdown=current,
        final_report=report,
        iterations=max_iter,
        exhausted=report.has_errors,
    )
