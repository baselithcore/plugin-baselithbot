"""Post-write hooks: examples cache, graph extraction, reindex."""

from __future__ import annotations

import logging
from pathlib import Path

from llm_wiki.config import WIKI_ROOT
from llm_wiki.domain.registry import get_pack
from llm_wiki.ingest_raw.orchestrator.models import IngestResult

logger = logging.getLogger(__name__)


def _extract_page_graph(path: Path) -> None:
    """Run knowledge-graph extraction on a freshly-written page.

    Gated by ``GRAPH_EXTRACT_ENABLED`` + active FalkorDB. Reads the page
    from disk (we just wrote it) and pushes entities + relations to the
    KG store. Failure is logged and swallowed — graph layer is best-effort
    enrichment, the page is already on disk.
    """
    from llm_wiki.config import GRAPH_EXTRACT_ENABLED

    if not GRAPH_EXTRACT_ENABLED:
        return
    try:
        from llm_wiki.domain.prompts import get_registry
        from llm_wiki.graphdb.extraction import extract_from_page
        from llm_wiki.graphdb.store import get_kg_store
        from llm_wiki.wiki.parser import parse_file

        store = get_kg_store()
        if not store.enabled:
            return
        store.ensure_indexes()
        page = parse_file(path, WIKI_ROOT)
        if page is None or not page.body:
            return
        pack = get_pack()
        registry = get_registry()
        extract_from_page(
            page_id=page.document_id,
            page_title=page.title,
            page_body=page.body,
            page_type=page.page_type,
            pack=pack,
            registry=registry,
            store=store,
        )
    except Exception as exc:
        logger.warning("[graph.extract] post-write extraction failed for %s: %s", path, exc)


def _add_page_to_examples(path: Path) -> None:
    """Append a single appena-scritta pagina alla cache few-shot.

    Chiamato subito dopo ogni write (no-end-of-ingest batch), così la
    source page appena prodotta è disponibile come esempio per le
    derived pages dello stesso ingest. Senza questo passo, solo la run
    successiva la vedrebbe.
    """
    from llm_wiki.ingest_raw.examples import add_to_cache

    try:
        add_to_cache([path])
    except Exception as exc:
        logger.debug("[examples] cache add skipped: %s", exc)


def _reindex_written(result: IngestResult) -> None:
    """Reindex sincrono via singola chiamata batched: 1 pass embedder + 1 upsert
    Qdrant invece di N. Mantiene compat per CLI ``--reindex``."""
    import asyncio

    from llm_wiki.wiki.ingest import ingest_files_batched

    paths = [p.target_path for p in result.pages if p.status == "written"]
    if not paths:
        return

    try:
        asyncio.run(ingest_files_batched(paths))
    except RuntimeError:
        logger.info("reindex skipped: event loop already active")


def reindex_result(result: IngestResult) -> int:
    """Reindex sincrono via batch. Esposto al runner così la fase si scinde
    dal completion event del job (vedi runner.py:_run_reindex_phase)."""
    import asyncio

    from llm_wiki.wiki.ingest import ingest_files_batched

    paths = [p.target_path for p in result.pages if p.status == "written"]
    if not paths:
        return 0

    try:
        asyncio.run(ingest_files_batched(paths))
    except RuntimeError:
        logger.info("reindex skipped: event loop already active")
        return 0
    return len(paths)
