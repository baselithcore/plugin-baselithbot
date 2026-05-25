"""Indicizzazione delle pagine wiki: chunk → embed → upsert in Qdrant.

Estratto da :mod:`llm_wiki.vectorstore.core` per separare il path di
ingestion da quello di retrieval. La pipeline single-page e quella
batched condividono content-hash skip (idempotente sul re-ingest).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

from qdrant_client.models import PointStruct  # type: ignore[import-not-found]

from llm_wiki.config import (
    COLLECTION_NAME,
    HIERARCHICAL_CHILD_OVERLAP,
    HIERARCHICAL_CHILD_SIZE,
    HIERARCHICAL_CHUNKING_ENABLED,
    HIERARCHICAL_PARENT_SIZE,
)
from llm_wiki.vectorstore.chunking import (
    chunk_markdown,
    chunk_point_id,
    extract_article_refs,
    prepare_chunk_text,
    section_paths_for_chunks,
    slug_anchor,
)
from llm_wiki.vectorstore.contextual import contextualize_chunks
from llm_wiki.vectorstore.embedder import get_embedder
from llm_wiki.vectorstore.hierarchical import (
    HierarchicalChunk,
    build_parent_id,
    chunk_markdown_hierarchical,
)
from llm_wiki.vectorstore.qdrant_ops import (
    build_point_vector,
    create_collection,
    delete_document_points,
    get_qdrant,
    upsert_in_batches,
)

logger = logging.getLogger(__name__)


def _content_hash(content: str) -> str:
    """Hash stabile del contenuto normalizzato per change detection."""
    normalized = content.strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()[:16]


def _existing_content_hash(client: Any, document_id: str) -> str | None:
    """Legge `content_hash` del primo chunk del doc, se presente in Qdrant."""
    try:
        from qdrant_client.models import (  # type: ignore[import-not-found]
            FieldCondition as _FC,
        )
        from qdrant_client.models import (
            Filter as _F,
        )
        from qdrant_client.models import (
            MatchValue as _MV,
        )

        res, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=_F(must=[_FC(key="document_id", match=_MV(value=document_id))]),
            limit=1,
            with_payload=["content_hash"],
        )
        if res:
            return (res[0].payload or {}).get("content_hash")
    except Exception:
        return None
    return None


async def index_page(
    document_id: str,
    content: str,
    metadata: dict[str, Any] | None = None,
    *,
    force: bool = False,
) -> int:
    """Chunk + embed + upsert. Ritorna il numero di chunk indicizzati.

    Ottimizzazioni:
    - **Content-hash skip**: se il contenuto (normalizzato) è identico a quello
      già indicizzato, salta l'intera pipeline. Speedup massimo per re-ingest
      incrementale (`llm-wiki ingest` su vault invariato = ~50ms/file).
    - **Timing log** a livello INFO per profilare.
    """
    t0 = time.perf_counter()
    client = get_qdrant()
    if not client:
        logger.error("[vectorstore] Qdrant non disponibile")
        return 0

    create_collection()

    new_hash = _content_hash(content)
    if not force:
        existing = await asyncio.to_thread(_existing_content_hash, client, document_id)
        if existing == new_hash:
            logger.info("[vectorstore] %s invariato (hash=%s) — skip", document_id, new_hash)
            return 0

    delete_document_points(document_id)

    embedder = get_embedder()
    if not embedder:
        logger.error("[vectorstore] embedder non disponibile")
        return 0

    meta = dict(metadata or {})
    meta["content_hash"] = new_hash

    hierarchical: list[HierarchicalChunk] | None = None
    if HIERARCHICAL_CHUNKING_ENABLED:
        hierarchical = chunk_markdown_hierarchical(
            content,
            parent_size=HIERARCHICAL_PARENT_SIZE,
            child_size=HIERARCHICAL_CHILD_SIZE,
            child_overlap=HIERARCHICAL_CHILD_OVERLAP,
        )

    if hierarchical:
        chunks = [h.child_text for h in hierarchical]
        section_paths = [list(h.section_path) for h in hierarchical]
    else:
        chunks = chunk_markdown(content)
        if not chunks:
            return 0
        section_paths = section_paths_for_chunks(content, chunks)

    t_ctx = time.perf_counter()
    contextual = await asyncio.to_thread(contextualize_chunks, content, chunks)
    t_ctx_done = time.perf_counter()

    enriched = [prepare_chunk_text(ctx.embedded_text, meta) for ctx in contextual]
    emb_out = await asyncio.to_thread(embedder.encode, enriched)
    t_emb_done = time.perf_counter()

    points: list[PointStruct] = []
    for idx, (raw_chunk, enriched_chunk, ctx) in enumerate(
        zip(chunks, enriched, contextual, strict=True)
    ):
        sec_path = section_paths[idx] if idx < len(section_paths) else []
        sec_heading = sec_path[-1] if sec_path else ""
        # Quando il chunker hierarchical è attivo, il child può ricadere
        # sotto un heading H3+ INTERNO al parent_window: preferiamo quel
        # heading per la citazione anchor-first puntuale.
        if hierarchical:
            hc = hierarchical[idx]
            fine_h = hc.section_heading_fine or sec_heading
            fine_a = hc.section_anchor_fine or slug_anchor(sec_heading)
        else:
            fine_h = sec_heading
            fine_a = slug_anchor(sec_heading)
        payload: dict[str, Any] = {
            "text": enriched_chunk,
            "raw_text": raw_chunk,
            "context_prefix": ctx.context_prefix,
            "document_id": document_id,
            "chunk_index": idx,
            "chunk_count": len(chunks),
            # Articoli citati nel chunk (rinvii interni/esterni). Abilita
            # il follow-the-link retrieval in `_expand_with_rinvii`.
            "articoli_citati": extract_article_refs(raw_chunk),
            # Provenance puntuale → wikilink Obsidian `[[slug#anchor]]`.
            # `section_heading` = heading fine (più profondo) sotto cui ricade
            # il chunk; `section_path` = breadcrumb completo (H1/H2 → fine).
            "section_path": sec_path,
            "section_heading": fine_h,
            "section_anchor": fine_a,
        }
        if hierarchical:
            hc = hierarchical[idx]
            payload["parent_id"] = build_parent_id(document_id, hc.parent_id)
            payload["parent_text"] = hc.parent_text
            payload["is_hierarchical"] = True
            # Heading del parent_window (utile per dedup parent-section vs
            # hierarchical retrieval): è il top-level breadcrumb del chunk.
            payload["parent_section_heading"] = sec_heading
        payload.update(meta)

        dense = emb_out.dense[idx]
        sparse = emb_out.sparse[idx] if emb_out.has_sparse() else None
        colbert = emb_out.colbert[idx] if emb_out.has_colbert() else None

        points.append(
            PointStruct(
                id=chunk_point_id(document_id, idx),
                vector=build_point_vector(dense, sparse=sparse, colbert=colbert),
                payload=payload,
            )
        )

    inserted = await asyncio.to_thread(upsert_in_batches, points, collection=COLLECTION_NAME)
    if inserted == 0 and points:
        logger.error("[vectorstore] upsert %s fallito (0/%d inseriti)", document_id, len(points))
        return 0

    t_end = time.perf_counter()
    logger.info(
        "[perf] index %s: %d chunks · ctx=%.2fs emb=%.2fs upsert=%.2fs total=%.2fs",
        document_id,
        inserted,
        t_ctx_done - t_ctx,
        t_emb_done - t_ctx_done,
        t_end - t_emb_done,
        t_end - t0,
    )
    return inserted


async def index_pages_batched(
    pages: list[tuple[str, str, dict[str, Any]]],
    *,
    use_contextual: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Ingestion batch ottimizzata per N pagine.

    Vantaggi rispetto a N chiamate `index_page` sequenziali:
    - **1 sola chiamata embedder** su TUTTI i chunk del batch (MPS/CUDA usa
      bene il GPU solo con batch grandi; single-page batch sono bottleneck).
    - **1 sola chiamata upsert Qdrant** invece di N piccole.
    - **Contextual globale parallelo**: tutti i chunks di tutte le pagine
      passano in un unico ThreadPoolExecutor → Ollama (su DGX remoto) viene
      pompato alla concurrency configurata senza idle tra una pagina e l'altra.

    `pages` = lista di (document_id, content, metadata).
    """
    t0 = time.perf_counter()
    client = get_qdrant()
    if not client:
        logger.error("[vectorstore] Qdrant non disponibile")
        return {"indexed": 0, "unchanged": 0, "chunks": 0}

    create_collection()

    embedder = get_embedder()
    if not embedder:
        logger.error("[vectorstore] embedder non disponibile")
        return {"indexed": 0, "unchanged": 0, "chunks": 0}

    # --- skip immutati ------------------------------------------------------
    to_process: list[tuple[str, str, dict[str, Any], str]] = []
    unchanged = 0
    for doc_id, content, meta in pages:
        h = _content_hash(content)
        if not force:
            existing = _existing_content_hash(client, doc_id)
            if existing == h:
                unchanged += 1
                continue
        to_process.append((doc_id, content, dict(meta), h))

    if not to_process:
        logger.info("[perf] ingest batch: tutti %d invariati — skip", unchanged)
        return {"indexed": 0, "unchanged": unchanged, "chunks": 0}

    # --- chunking tutti i documenti ----------------------------------------
    # Flat: [(doc_id, chunk_idx, raw_chunk, meta_with_hash, full_content), ...]
    flat: list[tuple[str, int, str, dict[str, Any], str]] = []
    doc_chunk_counts: dict[str, int] = {}
    # Mappa (doc_id, chunk_idx) → breadcrumb di heading, per popolare il
    # payload con provenance puntuale (vedi `index_page` per il rationale).
    section_map: dict[tuple[str, int], list[str]] = {}
    # Hierarchical: mappa (doc_id, chunk_idx) → (parent_id_globale, parent_text,
    # heading_fine, anchor_fine). Vuota nel path standard.
    hier_map: dict[tuple[str, int], tuple[str, str, str, str]] = {}
    for doc_id, content, meta, h in to_process:
        meta["content_hash"] = h
        hierarchical_doc: list[HierarchicalChunk] | None = None
        if HIERARCHICAL_CHUNKING_ENABLED:
            hierarchical_doc = chunk_markdown_hierarchical(
                content,
                parent_size=HIERARCHICAL_PARENT_SIZE,
                child_size=HIERARCHICAL_CHILD_SIZE,
                child_overlap=HIERARCHICAL_CHILD_OVERLAP,
            )
        if hierarchical_doc:
            chunks = [hc.child_text for hc in hierarchical_doc]
            sec_paths = [list(hc.section_path) for hc in hierarchical_doc]
            for idx, hc in enumerate(hierarchical_doc):
                hier_map[(doc_id, idx)] = (
                    build_parent_id(doc_id, hc.parent_id),
                    hc.parent_text,
                    hc.section_heading_fine,
                    hc.section_anchor_fine,
                )
        else:
            chunks = chunk_markdown(content)
            sec_paths = section_paths_for_chunks(content, chunks)
        doc_chunk_counts[doc_id] = len(chunks)
        for idx, c in enumerate(chunks):
            flat.append((doc_id, idx, c, meta, content))
            section_map[(doc_id, idx)] = sec_paths[idx] if idx < len(sec_paths) else []

    if not flat:
        return {"indexed": len(to_process), "unchanged": unchanged, "chunks": 0}

    # --- contextual GLOBALE (raggruppato per documento) --------------------
    # Raggruppo per doc_id per poter chiamare contextualize_chunks col context
    # del documento intero. La parallelizzazione interna (ThreadPool) satura
    # Ollama su DGX sulle chiamate di UN documento; qui chiamiamo doc-by-doc
    # ma il pool è riusato e la rete lavora continuamente.
    t_ctx = time.perf_counter()
    ctx_map: dict[tuple[str, int], str] = {}  # (doc_id, idx) -> prefix
    if use_contextual:
        for doc_id, _, _, _ in to_process:
            chunks_doc = [raw for did, _, raw, _, _ in flat if did == doc_id]
            full_content = next(c for did, _, _, _, c in flat if did == doc_id)
            ctx_results = await asyncio.to_thread(contextualize_chunks, full_content, chunks_doc)
            for i, res in enumerate(ctx_results):
                ctx_map[(doc_id, i)] = res.context_prefix
    t_ctx_done = time.perf_counter()

    # --- embed UNICO batch su TUTTI i chunk --------------------------------
    enriched_texts: list[str] = []
    for doc_id, idx, raw, meta, _ in flat:
        prefix = ctx_map.get((doc_id, idx), "")
        embed_body = f"{prefix}\n\n{raw}" if prefix else raw
        enriched_texts.append(prepare_chunk_text(embed_body, meta))

    emb_out = await asyncio.to_thread(embedder.encode, enriched_texts)
    t_emb_done = time.perf_counter()

    # --- build all points + single upsert ----------------------------------
    # Prima cancella tutti i doc coinvolti in un colpo
    for doc_id, _, _, _ in to_process:
        delete_document_points(doc_id)

    points: list[PointStruct] = []
    for i, (doc_id, idx, raw, meta, _) in enumerate(flat):
        sec_path = section_map.get((doc_id, idx), [])
        sec_heading = sec_path[-1] if sec_path else ""
        hier = hier_map.get((doc_id, idx))
        if hier:
            # heading_fine / anchor_fine: preferiti per la citazione puntuale.
            fine_h = hier[2] or sec_heading
            fine_a = hier[3] or slug_anchor(sec_heading)
        else:
            fine_h = sec_heading
            fine_a = slug_anchor(sec_heading)
        payload: dict[str, Any] = {
            "text": enriched_texts[i],
            "raw_text": raw,
            "context_prefix": ctx_map.get((doc_id, idx), ""),
            "document_id": doc_id,
            "chunk_index": idx,
            "chunk_count": doc_chunk_counts[doc_id],
            "articoli_citati": extract_article_refs(raw),
            "section_path": sec_path,
            "section_heading": fine_h,
            "section_anchor": fine_a,
        }
        if hier:
            payload["parent_id"] = hier[0]
            payload["parent_text"] = hier[1]
            payload["is_hierarchical"] = True
            payload["parent_section_heading"] = sec_heading
        payload.update(meta)

        dense = emb_out.dense[i]
        sparse = emb_out.sparse[i] if emb_out.has_sparse() else None
        colbert = emb_out.colbert[i] if emb_out.has_colbert() else None

        points.append(
            PointStruct(
                id=chunk_point_id(doc_id, idx),
                vector=build_point_vector(dense, sparse=sparse, colbert=colbert),
                payload=payload,
            )
        )

    inserted = await asyncio.to_thread(upsert_in_batches, points, collection=COLLECTION_NAME)
    if inserted < len(points):
        logger.warning(
            "[vectorstore] upsert batch parziale: %d/%d points inseriti", inserted, len(points)
        )
    # Diag temp: per-doc breakdown — quale doc è stato incluso, con quanti chunk.
    # Permette di spottare doc silenziosamente saltati (chunk_count=0) o
    # filtrati downstream del chunker.
    for doc_id_diag, content_diag, _, _ in to_process:
        n_chunks_diag = doc_chunk_counts.get(doc_id_diag, 0)
        n_points_diag = sum(
            1 for p in points if (p.payload or {}).get("document_id") == doc_id_diag
        )
        logger.info(
            "[diag] doc=%s body_len=%d chunks=%d points_built=%d",
            doc_id_diag,
            len(content_diag),
            n_chunks_diag,
            n_points_diag,
        )

    t_end = time.perf_counter()
    logger.info(
        "[perf] batch ingest: %d pages · %d chunks · ctx=%.2fs emb=%.2fs upsert=%.2fs total=%.2fs",
        len(to_process),
        inserted,
        t_ctx_done - t_ctx,
        t_emb_done - t_ctx_done,
        t_end - t_emb_done,
        t_end - t0,
    )

    return {
        "indexed": len(to_process) if inserted > 0 else 0,
        "unchanged": unchanged,
        "chunks": inserted,
    }
