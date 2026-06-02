"""Post-write hooks: examples cache, graph extraction, reindex."""

from __future__ import annotations

import logging
from pathlib import Path

from llm_wiki.config import WIKI_ROOT
from llm_wiki.domain.registry import get_pack
from llm_wiki.ingest_raw.orchestrator.models import IngestResult

logger = logging.getLogger(__name__)


def _load_page_for_graph(path: Path):
    """Parse a freshly-written page + resolve pack/registry.

    Returns ``(page, pack, registry)`` or ``None`` for empty/unparseable
    pages. Thread-safe: only reads disk + process-singleton pack/registry,
    so it can run inside the LLM-extraction thread pool.
    """
    from llm_wiki.domain.prompts import get_registry
    from llm_wiki.wiki.parser import parse_file

    page = parse_file(path, WIKI_ROOT)
    if page is None or not page.body:
        return None
    return page, get_pack(), get_registry()


def _extract_page_graph(path: Path) -> None:
    """Serial entry point: extract + persist one page's graph.

    Gated by ``GRAPH_EXTRACT_ENABLED`` + active FalkorDB. Reads the page
    from disk (we just wrote it) and pushes entities + relations to the
    KG store. Failure is logged and swallowed — graph layer is best-effort
    enrichment, the page is already on disk. Used by the single-worker /
    Ollama ingest path (see :func:`_run_graph_extraction`).
    """
    from llm_wiki.config import GRAPH_EXTRACT_ENABLED

    if not GRAPH_EXTRACT_ENABLED:
        return
    try:
        from llm_wiki.graphdb.extraction import extract_from_page
        from llm_wiki.graphdb.store import get_kg_store

        store = get_kg_store()
        if not store.enabled:
            return
        store.ensure_indexes()
        loaded = _load_page_for_graph(path)
        if loaded is None:
            return
        page, pack, registry = loaded
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
        logger.warning(
            "[graph.extract] post-write extraction failed for %s: %s", path, exc
        )


def _run_graph_extraction(paths: list[Path], *, parallel: bool, workers: int) -> None:
    """Knowledge-graph extraction for the pages written by one ingest run.

    Serial path (Ollama / single worker): per-page extract+persist, identical
    to calling :func:`_extract_page_graph` in a loop.

    Parallel path (``INGEST_VENDOR=openai`` + ``workers > 1``): the expensive
    LLM extraction calls fan out over a thread pool, then the validated
    payloads are persisted **serially** on this thread — store MERGE mutations
    never race. ``ensure_indexes`` runs once up front (no concurrent DDL).

    Best-effort throughout: per-page failures are logged + swallowed; the
    pages are already on disk.
    """
    from llm_wiki.config import GRAPH_EXTRACT_ENABLED

    if not GRAPH_EXTRACT_ENABLED or not paths:
        return

    if not parallel or workers <= 1 or len(paths) < 2:
        for p in paths:
            _extract_page_graph(p)
        return

    try:
        from llm_wiki.graphdb.store import get_kg_store

        store = get_kg_store()
        if not store.enabled:
            return
        store.ensure_indexes()  # once, on main thread — avoid concurrent DDL
    except Exception as exc:
        logger.warning(
            "[graph.extract] store unavailable, skipping graph phase: %s", exc
        )
        return

    from concurrent.futures import ThreadPoolExecutor

    from llm_wiki.graphdb.extraction import (
        extract_payload_from_page,
        persist_extraction,
    )

    def _payload(path: Path):
        try:
            loaded = _load_page_for_graph(path)
            if loaded is None:
                return None
            page, pack, registry = loaded
            payload = extract_payload_from_page(
                page_title=page.title,
                page_body=page.body,
                pack=pack,
                registry=registry,
            )
            return (page.document_id, page.page_type, payload)
        except Exception as exc:
            logger.warning(
                "[graph.extract] payload extraction failed for %s: %s", path, exc
            )
            return None

    logger.info(
        "[graph.extract] %d pages, LLM extraction in parallel (workers=%d)",
        len(paths),
        workers,
    )
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_payload, paths))

    for res in results:
        if res is None:
            continue
        page_id, page_type, payload = res
        try:
            persist_extraction(
                payload, page_id=page_id, page_type=page_type, store=store
            )
            logger.info(
                "[graph.extract] page=%s entities=%d relations=%d",
                page_id,
                len(payload.entities),
                len(payload.relations),
            )
        except Exception as exc:
            logger.warning("[graph.extract] persist failed for %s: %s", page_id, exc)


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
