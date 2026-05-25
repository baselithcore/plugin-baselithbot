"""Generator: produce Markdown for each planned page.

Dispatches to a :class:`PageTypeStrategy` selected from the active Domain
Pack. Strategies own:

- prompt template selection
- few-shot pick
- scope extraction (which sections + tables of the source feed the LLM)

The default strategy renders ``<page_type>_page.j2`` with a thin context
and is sufficient for verticals that don't need anything fancy.
"""

from __future__ import annotations

import logging
from datetime import date

from llm_wiki.domain.strategies import GenerationContext, select_page_type_strategy
from llm_wiki.ingest_raw.extractor import ExtractedDocument
from llm_wiki.ingest_raw.schemas import IngestPlan, PagePlan

logger = logging.getLogger(__name__)


def generate_page(
    plan_entry: PagePlan,
    *,
    plan: IngestPlan,
    doc: ExtractedDocument,
    model: str | None = None,
    today: date | None = None,
) -> str:
    strategy = select_page_type_strategy(
        page_type=plan_entry.page_type,
        subtype=plan_entry.subtype,
    )
    logger.info(
        "generate: %s — strategy=%s",
        plan_entry.target_path,
        strategy.name,
    )
    ctx = GenerationContext(
        plan_entry=plan_entry,
        plan=plan,
        extracted=doc,
        today=today,
        model=model,
    )
    return strategy.generate(ctx)
