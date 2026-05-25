"""Pluggable strategy interfaces for the ingest pipeline.

Two extension points let a Domain Pack tailor the pipeline without
patching the engine:

- :class:`PageTypeStrategy` — decides how a planned page is rendered
  into Markdown. The generator dispatches by ``(page_type, subtype)`` and
  delegates the prompt selection + scope extraction to the matching
  strategy.

- :class:`ExtractorStrategy` — domain-specific hints for PDF extraction
  (regex, heading dictionaries, OCR triggers). The base extractor is
  generic; strategies sit on top to bias backend selection or
  post-process the extracted markdown.

Discovery
---------
A pack opts in by declaring ``strategies_module`` in ``pack.yaml`` (e.g.
``strategies_module: strategies``) and exposing two factory callables in
that module:

.. code-block:: python

    def page_type_strategies() -> list[PageTypeStrategy]: ...
    def extractor_strategies() -> list[ExtractorStrategy]: ...

The registry imports the module via ``importlib`` and indexes the
strategies. Calls without a registered strategy fall back to the
:class:`DefaultPageTypeStrategy`, which renders any page using
``<page_type>_page.j2`` from the active pack's prompts directory.
"""

from __future__ import annotations

import importlib
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from llm_wiki.domain.pack import DomainPack
from llm_wiki.domain.registry import get_pack

logger = logging.getLogger(__name__)


# --- page type strategy -----------------------------------------------------


@dataclass
class GenerationContext:
    """Inputs handed to a :class:`PageTypeStrategy` when rendering a page."""

    plan_entry: Any  # PagePlan — Any to avoid circular import on schemas
    plan: Any  # IngestPlan
    extracted: Any  # ExtractedDocument
    today: date | None = None
    model: str | None = None


@runtime_checkable
class PageTypeStrategy(Protocol):
    """Render a planned page into Markdown.

    The strategy owns the full generation step for the page types it
    declares — prompt selection, few-shot pick, section extraction.
    Returning a Markdown string passes the result back to the orchestrator
    for linting + writing.
    """

    name: str

    def matches(self, *, page_type: str, subtype: str | None) -> bool: ...

    def generate(self, ctx: GenerationContext) -> str: ...


class DefaultPageTypeStrategy:
    """Fallback strategy: dispatch a ``ingest/{source,entity}_page_*.j2`` bundle.

    Active for any ``(page_type, subtype)`` that no pack strategy claims.
    Routing:

    - ``page_type == "source"`` → :func:`source_page_bundle` (full
      outline + verbatim code/CLI/table atoms from the entire markdown).
    - any other ``page_type`` → :func:`entity_page_bundle` (keyword
      snippet around the page title + verbatim atoms).

    Pre-2025-05 behaviour rendered ``<page_type>_page.j2`` or fell
    back to the RAG ``system.j2`` prompt — a vestigial path that
    bypassed every editorial rule in the pack's ``ingest/`` templates
    and silently dropped code/snippet content from generated pages.
    The dispatch below makes the well-tested ingest bundles the
    authoritative generator for every pack that has no custom
    strategy.
    """

    name = "default"

    def __init__(self, prompt_template: str | None = None) -> None:
        # Retained for diagnostics: pack.yaml still ships
        # ``prompt_template`` per page_type, but the dispatch now
        # picks the bundle by page_type kind, not by raw template name.
        self._template = prompt_template

    def matches(self, *, page_type: str, subtype: str | None) -> bool:
        return True

    def generate(self, ctx: GenerationContext) -> str:
        from llm_wiki.ingest_raw.examples import pick_examples
        from llm_wiki.ingest_raw.llm_client import generate_text
        from llm_wiki.ingest_raw.planner import extract_outline, extract_verbatim_atoms
        from llm_wiki.ingest_raw.prompts import entity_page_bundle, source_page_bundle

        plan_entry = ctx.plan_entry
        plan = ctx.plan
        doc = ctx.extracted
        today_iso = (ctx.today or date.today()).isoformat()

        atoms = extract_verbatim_atoms(doc.markdown)

        if plan_entry.page_type == "source":
            outline = extract_outline(doc.markdown, max_chars=8000)
            examples = pick_examples(
                page_type="source",
                subtype=plan_entry.subtype,
                hint_keywords=[plan_entry.title, *plan_entry.title.split()],
                max_examples=1,
            )
            bundle = source_page_bundle(
                plan=plan.model_dump(mode="json"),
                classification={
                    "edizione": plan.edizione,
                    "source_type": plan.source_type,
                },
                source_path=_source_path_for_prompt(doc),
                outline=outline,
                examples_blocks=[e.as_prompt_block() for e in examples],
                today_iso=today_iso,
                verbatim_atoms=atoms,
            )
            return generate_text(messages=bundle.as_messages(), model=ctx.model)

        snippet = _snippet_for_keyword(doc.markdown, keyword=plan_entry.title, window=4000)
        bundle = entity_page_bundle(
            plan_entry=plan_entry.model_dump(mode="json"),
            source_path=plan.source_page.target_path,
            context_snippet=snippet,
            today_iso=today_iso,
            verbatim_atoms=atoms,
        )
        return generate_text(messages=bundle.as_messages(), model=ctx.model)


def _source_path_for_prompt(doc: Any) -> str:
    """Render ``doc.source_path`` as a vault-relative string when possible.

    Insurance's strategy uses ``relative_to(<vault>/raw)`` to keep the
    prompt clean; mirror the behaviour here so the default strategy
    produces the same value the source-page template expects.
    """
    p = Path(doc.source_path)
    for parent in p.parents:
        if parent.name == "raw":
            try:
                return str(p.relative_to(parent.parent))
            except ValueError:
                break
    return str(p)


def _snippet_for_keyword(markdown: str, *, keyword: str, window: int) -> str:
    """Slice a ``window``-char window centred on the first ``keyword`` hit.

    Falls back to the head of the document if the keyword is not
    found — common when the planner derives a page title that
    rephrases the source.
    """
    if not markdown:
        return ""
    idx = markdown.lower().find(keyword.lower()) if keyword else -1
    if idx < 0:
        return markdown[:window]
    start = max(0, idx - window // 2)
    end = min(len(markdown), start + window)
    return markdown[start:end]


# --- extractor strategy -----------------------------------------------------


@runtime_checkable
class ExtractorStrategy(Protocol):
    """Domain-aware tweaks layered on top of the generic PDF extractor.

    Hooks let the pack pre-bias the backend or post-process the extracted
    markdown (e.g. an insurance pack may merge "Set Informativo" page
    sequences; a legal pack may detect "Sentenza" front-matter from
    layout).
    """

    name: str

    def claim(self, source_path: Path, hints: dict[str, Any]) -> bool: ...

    def post_process(self, doc: Any) -> Any: ...


# --- registry ---------------------------------------------------------------


@dataclass
class StrategyBundle:
    page_types: list[PageTypeStrategy]
    extractors: list[ExtractorStrategy]


_lock = threading.Lock()
_cached: StrategyBundle | None = None
_cached_pack_root: Path | None = None


def _import_pack_strategies(pack: DomainPack) -> StrategyBundle:
    page_types: list[PageTypeStrategy] = []
    extractors: list[ExtractorStrategy] = []

    module_name = getattr(pack, "_strategies_module", None) or _resolve_strategies_module(pack)
    if module_name is None:
        return StrategyBundle(page_types, extractors)

    try:
        mod = importlib.import_module(module_name)
    except ModuleNotFoundError:
        logger.info("[strategies] pack %s declares no strategies module", pack.name)
        return StrategyBundle(page_types, extractors)
    except Exception as exc:
        logger.warning("[strategies] failed to import %s: %s", module_name, exc)
        return StrategyBundle(page_types, extractors)

    page_types.extend(_call_factory(mod, "page_type_strategies"))
    extractors.extend(_call_factory(mod, "extractor_strategies"))
    logger.info(
        "[strategies] loaded from %s — page_types=%d extractors=%d",
        module_name,
        len(page_types),
        len(extractors),
    )
    return StrategyBundle(page_types, extractors)


def _resolve_strategies_module(pack: DomainPack) -> str | None:
    if pack.root is None:
        return None
    candidate = pack.root / "strategies.py"
    if not candidate.is_file():
        return None
    return f"domains.{pack.name}.strategies"


def _call_factory(mod: Any, name: str) -> list:
    factory: Callable[[], list] | None = getattr(mod, name, None)
    if factory is None:
        return []
    try:
        result = factory()
    except Exception as exc:
        logger.warning("[strategies] factory %s.%s raised: %s", mod.__name__, name, exc)
        return []
    return list(result) if result else []


def get_strategies() -> StrategyBundle:
    """Process-wide cached strategies for the active pack."""
    global _cached, _cached_pack_root
    pack = get_pack()
    with _lock:
        if _cached is None or _cached_pack_root != pack.root:
            _cached = _import_pack_strategies(pack)
            _cached_pack_root = pack.root
        return _cached


def reset_strategies_cache() -> None:
    """Test-only: drop the cached strategies."""
    global _cached, _cached_pack_root
    with _lock:
        _cached = None
        _cached_pack_root = None


def select_page_type_strategy(*, page_type: str, subtype: str | None) -> PageTypeStrategy:
    """Pick the first matching strategy or fall back to the default."""
    bundle = get_strategies()
    for strat in bundle.page_types:
        try:
            if strat.matches(page_type=page_type, subtype=subtype):
                return strat
        except Exception as exc:
            logger.warning("[strategies] %s.matches raised: %s", strat.name, exc)
            continue
    pack = get_pack()
    pt = pack.page_type(page_type)
    template = pt.prompt_template if pt else None
    return DefaultPageTypeStrategy(prompt_template=template)
