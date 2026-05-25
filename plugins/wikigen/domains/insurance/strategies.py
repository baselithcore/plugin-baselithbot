"""Insurance vertical strategies.

Registers three :class:`PageTypeStrategy` instances tailored to the
insurance MVP and a ``frontmatter_defaults`` hook used by the orchestrator
to seed the propaedeutics block.

Strategies in priority order (the registry picks the first ``matches``):

- :class:`InsuranceSourceStrategy`     — ``page_type == "source"``.
- :class:`InsuranceGaranziaStrategy`   — ``subtype in {"garanzia-assicurativa", "pack-opzionale"}``.
- :class:`InsuranceEntityStrategy`     — ``page_type == "entity"``.

Anything else falls back to the engine's default strategy, which renders
``concept_page.j2`` / ``topic_page.j2`` if present in the pack.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from llm_wiki.domain.strategies import GenerationContext, PageTypeStrategy
from llm_wiki.ingest_raw.examples import pick_examples
from llm_wiki.ingest_raw.extractor import ExtractedDocument, ExtractedTable
from llm_wiki.ingest_raw.llm_client import generate_text
from llm_wiki.ingest_raw.schemas import IngestPlan

# --- helpers ----------------------------------------------------------------


def _today_iso(ctx: GenerationContext) -> str:
    return (ctx.today or date.today()).isoformat()


def _full_outline(markdown: str, *, limit_chars: int) -> str:
    out: list[str] = []
    for m in re.finditer(r"^(#{1,4})\s+(.+)$", markdown, re.MULTILINE):
        out.append(m.group(0))
        if sum(len(x) for x in out) > limit_chars:
            break
    return "\n".join(out)


def _extract_section_markdown(doc: ExtractedDocument, *, section_hints: list[str]) -> str:
    if not section_hints:
        return doc.markdown[:10000]
    md = doc.markdown
    chunks: list[str] = []
    for hint in section_hints:
        pat = re.compile(rf"^#+\s+.*{re.escape(hint)}.*$", re.IGNORECASE | re.MULTILINE)
        m = pat.search(md)
        if not m:
            continue
        start = m.start()
        next_heading = re.search(r"^#{1,2}\s+", md[start + len(m.group(0)) :], re.MULTILINE)
        end = (start + len(m.group(0)) + next_heading.start()) if next_heading else len(md)
        chunks.append(md[start:end])
    if not chunks:
        return doc.markdown[:10000]
    return "\n\n".join(chunks)[:12000]


def _tables_for_section(
    tables: list[ExtractedTable], *, section_hints: list[str]
) -> list[ExtractedTable]:
    if not section_hints:
        return tables[:5]
    lowered = [h.lower() for h in section_hints]
    out: list[ExtractedTable] = []
    for t in tables:
        hay = f"{t.caption or ''} {' '.join(t.header)}".lower()
        if any(h in hay for h in lowered):
            out.append(t)
    return out or tables[:3]


def _snippet_for_keyword(markdown: str, *, keyword: str, window: int) -> str:
    idx = markdown.lower().find(keyword.lower())
    if idx < 0:
        return markdown[:window]
    start = max(0, idx - window // 2)
    end = min(len(markdown), idx + window // 2)
    return markdown[start:end]


def _compact_plan(plan: IngestPlan) -> dict[str, Any]:
    return {
        "source_page": plan.source_page.target_path,
        "derived_pages": [
            {
                "target_path": p.target_path,
                "title": p.title,
                "subtype": p.subtype,
            }
            for p in plan.derived_pages
        ],
        "edizione": plan.edizione,
    }


def _vault_root(any_path: Any) -> Path:
    p = Path(any_path)
    for parent in p.parents:
        if parent.name == "raw":
            return parent.parent
    return p.parent


def _slug(target_path: str) -> str:
    p = target_path
    if p.endswith(".md"):
        p = p[:-3]
    if p.startswith("wiki/"):
        p = p[len("wiki/") :]
    return p


# --- strategies -------------------------------------------------------------


class InsuranceSourceStrategy:
    name = "insurance.source"

    def matches(self, *, page_type: str, subtype: str | None) -> bool:
        return page_type == "source"

    def generate(self, ctx: GenerationContext) -> str:
        plan = ctx.plan
        doc = ctx.extracted
        entry = ctx.plan_entry
        outline = _full_outline(doc.markdown, limit_chars=8000)
        examples = pick_examples(
            page_type="source",
            subtype=None,
            hint_keywords=[entry.title, *entry.title.split()],
            max_examples=1,
        )
        from llm_wiki.ingest_raw.planner import extract_verbatim_atoms
        from llm_wiki.ingest_raw.prompts import source_page_bundle

        atoms = extract_verbatim_atoms(doc.markdown)

        bundle = source_page_bundle(
            plan=plan.model_dump(mode="json"),
            classification={"edizione": plan.edizione, "source_type": plan.source_type},
            source_path=str(doc.source_path.relative_to(_vault_root(doc.source_path))),
            outline=outline,
            examples_blocks=[e.as_prompt_block() for e in examples],
            today_iso=_today_iso(ctx),
            verbatim_atoms=atoms,
        )
        return generate_text(messages=bundle.as_messages(), model=ctx.model)


class InsuranceGaranziaStrategy:
    name = "insurance.garanzia"

    def matches(self, *, page_type: str, subtype: str | None) -> bool:
        return page_type == "concept" and subtype in {"garanzia-assicurativa", "pack-opzionale"}

    def generate(self, ctx: GenerationContext) -> str:
        plan = ctx.plan
        doc = ctx.extracted
        entry = ctx.plan_entry
        section_md = _extract_section_markdown(doc, section_hints=entry.source_sections)
        tables = _tables_for_section(doc.tables, section_hints=entry.source_sections)
        tables_json = [
            {"page": t.page, "caption": t.caption, "header": t.header, "rows": t.rows}
            for t in tables
        ]
        examples = pick_examples(
            page_type="concept",
            subtype=entry.subtype,
            hint_keywords=[entry.title, *entry.wikilinks_expected],
            max_examples=2,
        )
        from llm_wiki.ingest_raw.prompts import garanzia_page_bundle

        bundle = garanzia_page_bundle(
            plan_entry=entry.model_dump(mode="json"),
            source_path=plan.source_page.target_path,
            section_markdown=section_md,
            tables_json=tables_json,
            examples_blocks=[e.as_prompt_block() for e in examples],
            today_iso=_today_iso(ctx),
            plan_context=_compact_plan(plan),
        )
        return generate_text(messages=bundle.as_messages(), model=ctx.model)


class InsuranceEntityStrategy:
    name = "insurance.entity"

    def matches(self, *, page_type: str, subtype: str | None) -> bool:
        return page_type == "entity"

    def generate(self, ctx: GenerationContext) -> str:
        plan = ctx.plan
        doc = ctx.extracted
        entry = ctx.plan_entry
        snippet = _snippet_for_keyword(doc.markdown, keyword=entry.title, window=1500)
        from llm_wiki.ingest_raw.planner import extract_verbatim_atoms
        from llm_wiki.ingest_raw.prompts import entity_page_bundle

        atoms = extract_verbatim_atoms(doc.markdown)

        bundle = entity_page_bundle(
            plan_entry=entry.model_dump(mode="json"),
            source_path=plan.source_page.target_path,
            context_snippet=snippet,
            today_iso=_today_iso(ctx),
            verbatim_atoms=atoms,
        )
        return generate_text(messages=bundle.as_messages(), model=ctx.model)


# --- factories ---------------------------------------------------------------


def page_type_strategies() -> list[PageTypeStrategy]:
    return [
        InsuranceSourceStrategy(),
        InsuranceGaranziaStrategy(),
        InsuranceEntityStrategy(),
    ]


def extractor_strategies() -> list[Any]:
    """No domain-specific extractor for insurance — generic backend is enough."""
    return []


def frontmatter_defaults(*, entry: Any, plan: Any) -> dict[str, Any]:
    """Insurance-specific defaults injected by the orchestrator."""
    if entry.page_type == "concept" and entry.subtype in {
        "garanzia-assicurativa",
        "pack-opzionale",
    }:
        return {
            "richiede-sezioni": [],
            "richiede-logica": "none",
            "acquistabile-senza-base": True,
            "vincoli-note": "",
            "prodotto": f"[[{_slug(plan.source_page.target_path)}]]",
        }
    return {}
