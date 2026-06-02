"""Pipeline di ingest dell'intero vault wiki → vector store (+ graph opzionale).

Usage:
    await ingest_all()                  # indicizza tutto il vault
    await ingest_file(Path("..."))      # indicizza una singola pagina

Il processo è idempotente: `index_page` cancella i chunk esistenti per lo stesso
`document_id` prima di reinserire.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from llm_wiki.config import RAW_DIR, WIKI_DIR, WIKI_ROOT
from llm_wiki.graphdb.core import get_graph_db
from llm_wiki.vectorstore.core import index_page, index_pages_batched
from llm_wiki.vectorstore.qdrant_ops import create_collection
from llm_wiki.wiki.parser import WikiPage, parse_file, walk_wiki

logger = logging.getLogger(__name__)


class RawDirViolation(RuntimeError):
    """Sollevata se una scrittura/ingest punta a `raw/`. CLAUDE.md §1: raw/ immutabile."""


def _assert_not_raw(path: Path) -> None:
    """Guardia a runtime: il pacchetto non deve mai toccare `raw/`."""
    try:
        resolved = path.resolve()
    except OSError:
        return
    if RAW_DIR in resolved.parents or resolved == RAW_DIR:
        raise RawDirViolation(
            f"`raw/` è immutabile (CLAUDE.md §1). Rifiutato: {resolved}"
        )


async def ingest_file(path: Path) -> dict[str, Any]:
    """Indicizza un singolo file markdown. Aggiorna anche il grafo se attivo."""
    _assert_not_raw(path)
    page = parse_file(path, WIKI_ROOT)
    if not page:
        return {"status": "error", "path": str(path), "message": "file non leggibile"}
    if not page.body:
        return {"status": "skipped", "path": str(path), "message": "contenuto vuoto"}

    n_chunks = await index_page(page.document_id, page.body, metadata=page.to_payload())
    _sync_graph(page)
    _tag_chunks_with_entities([page.document_id])

    return {
        "status": "indexed",
        "path": str(path),
        "document_id": page.document_id,
        "chunks": n_chunks,
        "wikilinks": len(page.wikilinks),
    }


async def ingest_files_batched(paths: list[Path]) -> dict[str, Any]:
    """Batch-indicizza N markdown via ``index_pages_batched``.

    Hot-path post-ingest: il flusso ``ingest_raw_file`` produce 5–15 pagine
    e poi le passa al reindex. Iterare ``ingest_file`` per ogni pagina
    spreca il batch embedder (BGE-M3 su MPS/CUDA = bottleneck con
    micro-batch da 1) e fa N upsert Qdrant invece di 1.

    Sync grafo resta per-pagina dopo il batch (operazione leggera, ~ms).
    """
    pages: list[WikiPage] = []
    pages_data: list[tuple[str, str, dict[str, Any]]] = []
    for path in paths:
        _assert_not_raw(path)
        page = parse_file(path, WIKI_ROOT)
        if not page or not page.body:
            continue
        pages.append(page)
        pages_data.append((page.document_id, page.body, page.to_payload()))

    if not pages_data:
        return {"status": "empty", "indexed": 0, "unchanged": 0, "chunks": 0}

    batch_result = await index_pages_batched(
        pages_data, use_contextual=True, force=False
    )
    for page in pages:
        _sync_graph(page)
    _tag_chunks_with_entities([p.document_id for p in pages])
    return {
        "status": "indexed",
        "indexed": batch_result["indexed"],
        "unchanged": batch_result["unchanged"],
        "chunks": batch_result["chunks"],
        "count": len(pages),
    }


async def ingest_all(
    concurrency: int = 4,
    *,
    use_contextual: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Walk dell'intero `wiki/` e indicizzazione BATCH.

    Pipeline ottimizzata:
    1. Parse paralleli di tutti i file markdown.
    2. Un'unica chiamata `index_pages_batched` che:
       - applica content-hash skip globale,
       - contextualizes tutti i chunks con pool riutilizzato,
       - fa UN SOLO forward pass dell'embedder su tutti i chunks (critico per
         sfruttare MPS/CUDA),
       - fa UN SOLO upsert Qdrant.
    3. Sync graph sequenziale (operazione leggera, ~1ms/edge).

    `concurrency` regola il parallelismo del parsing file (IO-bound, non
    hot path). Il vero parallelismo è dentro contextualize (ThreadPool) +
    embedder (batch GPU).

    `use_contextual=False` salta la fase contextual → ingest ~5-10× più veloce
    ma perdi il boost retrieval di Anthropic 2024 (~35% miss reduction).
    """
    t0 = time.perf_counter()
    create_collection()
    graph = get_graph_db()
    if graph.is_enabled():
        graph.create_indexes()

    files = walk_wiki(WIKI_DIR)
    if not files:
        logger.warning("[ingest] nessun file markdown in %s", WIKI_DIR)
        return {"status": "empty", "count": 0, "results": []}

    # --- parse paralleli (IO-bound, concurrency alta OK) -------------------
    sem = asyncio.Semaphore(max(concurrency, 8))

    async def _parse(p: Path) -> WikiPage | None:
        async with sem:
            _assert_not_raw(p)
            return await asyncio.to_thread(parse_file, p, WIKI_ROOT)

    parsed = await asyncio.gather(*(_parse(p) for p in files))
    pages_data: list[tuple[str, str, dict[str, Any]]] = []
    valid_pages: list[WikiPage] = []
    for page in parsed:
        if page is None or not page.body:
            continue
        pages_data.append((page.document_id, page.body, page.to_payload()))
        valid_pages.append(page)

    t_parsed = time.perf_counter()
    logger.info(
        "[perf] parsed %d/%d files in %.2fs", len(pages_data), len(files), t_parsed - t0
    )

    # --- batch embed + upsert (con skip content-hash interno) --------------
    batch_result = await index_pages_batched(
        pages_data, use_contextual=use_contextual, force=force
    )

    # --- sync graph (leggero, sequenziale) ---------------------------------
    if graph.is_enabled():
        for page in valid_pages:
            _sync_graph(page)
    _tag_chunks_with_entities([p.document_id for p in valid_pages])

    elapsed = time.perf_counter() - t0
    indexed = batch_result["indexed"]
    unchanged = batch_result["unchanged"]
    chunks = batch_result["chunks"]

    logger.info(
        "[perf] ingest_all: %d files · %d indexed · %d unchanged · %d chunks · %.2fs",
        len(files),
        indexed,
        unchanged,
        chunks,
        elapsed,
    )

    return {
        "status": "ok",
        "count": indexed,
        "total_files": len(files),
        "total_chunks": chunks,
        "unchanged": unchanged,
        "elapsed_seconds": round(elapsed, 2),
        "graph_enabled": graph.is_enabled(),
        "contextual": use_contextual,
    }


def _tag_chunks_with_entities(document_ids: list[str]) -> None:
    """Hook post-ingest: arricchisce i payload Qdrant con
    ``entities_mentioned`` + ``entity_tiers``. No-op se il flag è OFF o se
    KG store non è installato. Errori swallowed (best-effort).

    Vedi :mod:`llm_wiki.graphdb.chunk_tagging` per il dettaglio
    dell'algoritmo e la sua aderenza ai principi graphify.
    """
    if not document_ids:
        return
    try:
        from llm_wiki.graphdb.chunk_tagging import tag_chunks_for_documents

        tag_chunks_for_documents(document_ids)
    except Exception as exc:
        logger.debug("[ingest] chunk-tag swallowed: %s", exc)


def _sync_graph(page: WikiPage) -> None:
    """Proietta pagina + wikilinks sul grafo se attivo."""
    graph = get_graph_db()
    if not graph.is_enabled():
        return
    graph.upsert_page(
        page.document_id,
        title=page.title,
        page_type=page.page_type,
        category=page.category,
        tags=page.tags,
        source_file=page.relative_path,
    )
    for target in page.wikilinks:
        # Il target potrebbe essere slug "bare" (es. "unipol-assicurazioni")
        # oppure percorso relativo. Normalizziamo a slug solo nome file.
        resolved = _resolve_target(target)
        # upsert nodo "ghost" se la pagina puntata non esiste ancora
        graph.upsert_page(resolved, title=target, page_type="unknown")
        graph.link_pages(page.document_id, resolved, rel="LINKS_TO")


def _resolve_target(target: str) -> str:
    """Normalizza un wikilink al formato document_id `<category>/<slug>`.

    Se il target non include categoria (caso tipico in Obsidian), teniamo solo
    lo slug finale: la vera risoluzione avviene al momento della query (dove
    il grafo restituisce i vicini per slug prefix-match).
    """
    t = target.strip().strip("/")
    if t.endswith(".md"):
        t = t[:-3]
    if t.startswith("wiki/"):
        t = t[len("wiki/") :]
    return t
