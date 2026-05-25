# app/vectorstore/indexing.py
"""Main indexing and search logic."""

from __future__ import annotations

import asyncio
import inspect
import logging
import random
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncIterator, Dict

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from agent_jira import graphrag_adapter
from agent_jira.agents.metadata import ProjectContextExtractor
from agent_jira.cost_control import BudgetExceededError
from agent_jira.doc_sources import DocumentSourceError, create_document_sources
from agent_jira.graphdb import graph_db
from agent_jira.tenant_context import get_current_tenant_id
from agent_jira.kb_labels import (
    build_document_label_candidates,
    build_kb_label,
    is_supported_document_label,
)
from agent_jira.metrics import (
    INDEXED_DOCUMENTS_GAUGE,
    INDEXED_DOCUMENTS_TOTAL,
    INDEXING_DURATION_SECONDS,
    INDEXING_RUNS_TOTAL,
    RETRIEVAL_LATENCY_SECONDS,
)
from agent_jira.nlp_models import get_embedder
from agent_jira.telemetry import telemetry
from agent_jira.vectorstore.chunking import _chunk_point_id, _prepare_chunk_text, splitter
from agent_jira.vectorstore.graph_sync import _upsert_graph_document
from agent_jira.vectorstore.qdrant_ops import _delete_document_points
from agent_jira.vectorstore.state import (
    _persist_index_state,
    _refresh_indexed_items,
    indexed_items,
)
from agent_jira.config import (
    COLLECTION,
    EMBEDDER_MODEL,
    INDEX_EMBED_BATCH_SIZE,
    INDEX_QDRANT_WAIT,
    QDRANT,
)

logger = logging.getLogger(__name__)
_FAST_METADATA_EXTRACTOR = ProjectContextExtractor()


@lru_cache(maxsize=1)
def _embedder():
    return get_embedder(EMBEDDER_MODEL)


class _EmbedderProxy:
    """Compatibility proxy so callers and tests can patch a stable embedder object."""

    def encode(self, *args, **kwargs):
        return _embedder().encode(*args, **kwargs)


embedder = _EmbedderProxy()


async def _iter_source_items(source) -> AsyncIterator[Any]:
    """Async iterator helper for document sources."""
    items = source.iter_items()
    if inspect.isawaitable(items):
        items = await items
    if hasattr(items, "__aiter__"):
        async for item in items:
            yield item
    else:
        for item in items:
            yield item


async def index_docs(incremental: bool = True) -> int:
    """Indicizza i documenti provenienti dalle sorgenti configurate."""

    start_time = time.perf_counter()
    # Only force refresh if we really suspect inconsistency, otherwise trust loaded state
    # for startup speed. If state is empty, we force reload.
    if not indexed_items:
        _refresh_indexed_items(force=False)

    try:
        sources_with_name = create_document_sources()
    except DocumentSourceError as exc:  # pragma: no cover - errore configurazione
        raise RuntimeError(
            f"Configurazione sorgenti documentali non valida: {exc}"
        ) from exc

    if not sources_with_name:
        logger.warning(
            "[vectorstore] Nessuna sorgente documentale attiva (config: filesystem)"
        )
        return 0

    new_documents = 0
    skipped_documents = 0
    graph_writes = 0
    graph_log_samples = 0
    current_document_ids: set[str] = set()
    previous_index = {key: value.copy() for key, value in indexed_items.items()}
    per_origin: Dict[str, int] = {name: 0 for name, _ in sources_with_name}

    # Track documents that need full processing
    items_to_process = []

    try:
        # Phase 1: Scan headers to detect changes efficiently
        for source_name, source in sources_with_name:
            if hasattr(source, "iter_headers") and hasattr(source, "read_item"):
                # Optimization: Smart check using mtime/size
                logger.info(f"[vectorstore] Scanning headers for source: {source_name}")

                # Handle both sync and async iterators for headers
                headers_gen = source.iter_headers()
                if inspect.isawaitable(headers_gen):
                    headers_gen = await headers_gen

                async def _consume_headers():
                    if hasattr(headers_gen, "__aiter__"):
                        async for h in headers_gen:
                            yield h
                    else:
                        for h in headers_gen:
                            yield h

                async for header in _consume_headers():
                    path, mtime, size = header
                    # Build temp ID just for lookup (FilesystemSource specific assumption for now)
                    # Ideally source would give us the ID without reading content, but build_kb_label needs path
                    # For filesystem, we know path is enough.
                    uid = build_kb_label(path)
                    current_document_ids.add(uid)

                    prev_entry = indexed_items.get(uid)

                    # Check if changed
                    is_changed = True
                    if incremental and prev_entry:
                        prev_mtime = prev_entry.get("mtime")
                        prev_size = prev_entry.get("size")

                        # Tolerance for float mtime differences
                        mtime_match = (
                            prev_mtime is not None
                            and abs(float(prev_mtime) - mtime) < 0.001
                        )
                        size_match = prev_size == size

                        if mtime_match and size_match:
                            is_changed = False

                    if is_changed:
                        items_to_process.append((source, path, mtime, size))
                    else:
                        skipped_documents += 1
            else:
                # Fallback for sources without header optimization (e.g. web, old impl)
                logger.info(
                    f"[vectorstore] Source {source_name} does not support headers, full scan."
                )
                async for item in _iter_source_items(source):
                    current_document_ids.add(item.uid)
                    items_to_process.append((None, item, None, None))

        if skipped_documents > 0:
            logger.info(
                f"[vectorstore] Skipped {skipped_documents} unchanged documents based on metadata."
            )

        # Phase 2: Process only new/changed items
        for source, item_or_path, mtime, size in items_to_process:
            if isinstance(item_or_path, Path):
                # It's a path from Phase 1, read it now
                item = source.read_item(item_or_path)
                if not item:
                    continue
            else:
                # It's already an item from Fallback Phase
                item = item_or_path

            # Normalize Graph Node ID
            graph_doc_id = item.uid
            try:
                fname = (item.metadata or {}).get("filename") or (
                    item.metadata or {}
                ).get("file_name")
                if fname:
                    graph_doc_id = build_kb_label(Path(fname))
            except Exception:
                pass

            # Fingerprint check (Double check for fallback or content-based dedupe)
            previous = indexed_items.get(item.uid)
            if (
                incremental
                and previous
                and previous.get("fingerprint") == item.fingerprint
            ):
                # Metadata might still update even if content fingerprint didn't change (unlikely if fingerprint includes meta)
                previous["metadata"] = dict(item.metadata or {})
                if mtime is not None:
                    previous["mtime"] = mtime
                if size is not None:
                    previous["size"] = size

                # ... existing graph sync logic for unchanged files could be here if we want to ensure graph consistency ...
                # For optimized startup, we assume if vectorstore matches, graph matches.
                # Only sync graph if explicitly missing?
                # Optimization: SKIP graph sync for unchanged files to save time

                indexed_items[item.uid] = {
                    "fingerprint": item.fingerprint,
                    "metadata": dict(item.metadata or {}),
                    "mtime": mtime,
                    "size": size,
                }
                new_documents += 1  # Technically revisited, but not re-indexed.
                continue

            # --- Full Indexing ---
            enriched_metadata = dict(item.metadata or {})

            # Look for sibling .analysis.json to extract project keys
            associated_projects = []
            if isinstance(item_or_path, Path):
                analysis_path = item_or_path.with_suffix(
                    item_or_path.suffix + ".analysis.json"
                )
                associated_projects = (
                    _FAST_METADATA_EXTRACTOR.extract_from_analysis_file(analysis_path)
                )

            fast_context = _FAST_METADATA_EXTRACTOR.extract_from_text(
                item.content, associated_projects=associated_projects
            )
            enriched_metadata.update(fast_context.to_search_metadata())

            # Split text into chunks
            raw_chunks = [
                chunk for chunk in splitter.split_text(item.content) if chunk.strip()
            ]

            if not raw_chunks:
                # Empty file, just track it
                indexed_items[item.uid] = {
                    "fingerprint": item.fingerprint,
                    "metadata": enriched_metadata,
                    "mtime": mtime,
                    "size": size,
                }
                continue

            enriched_chunks = [
                _prepare_chunk_text(chunk, enriched_metadata) for chunk in raw_chunks
            ]
            chunk_count = len(enriched_chunks)

            # Offload embedding generation to thread
            vectors = await asyncio.to_thread(
                embedder.encode,
                enriched_chunks,
                batch_size=INDEX_EMBED_BATCH_SIZE,
                convert_to_numpy=True,
            )
            if hasattr(vectors, "tolist"):
                vectors_iterable = vectors.tolist()
            else:
                vectors_iterable = vectors
            points: list[PointStruct] = []
            tenant_id = get_current_tenant_id()
            for idx, (chunk_text, vector) in enumerate(
                zip(enriched_chunks, vectors_iterable)
            ):
                payload: Dict[str, Any] = {
                    "text": chunk_text,
                    "document_id": graph_doc_id,
                    "fingerprint": item.fingerprint,
                }
                payload.update(enriched_metadata)
                payload["chunk_index"] = idx
                payload["chunk_count"] = chunk_count
                raw_chunk = raw_chunks[idx].strip()
                if raw_chunk:
                    payload["chunk_body"] = raw_chunk
                if tenant_id:
                    payload["tenant_id"] = tenant_id

                points.append(
                    PointStruct(
                        id=_chunk_point_id(item.uid, idx),
                        vector=vector,
                        payload=payload,
                    )
                )

            try:
                # Offload Qdrant upsert to thread
                await asyncio.to_thread(
                    QDRANT.upsert,
                    collection_name=COLLECTION,
                    points=points,
                    wait=INDEX_QDRANT_WAIT,
                )

                # Ensure standard KB category for promoted nodes
                graph_metadata = dict(enriched_metadata)
                graph_metadata["category"] = "knowledge-base"
                graph_metadata["title"] = graph_doc_id
                graph_metadata["name"] = graph_doc_id
                graph_metadata["label"] = graph_doc_id
                graph_metadata["display_name"] = graph_doc_id
                graph_metadata["kb_label"] = graph_doc_id
                graph_metadata["doc_label"] = graph_doc_id
                graph_metadata["jira_label"] = graph_doc_id
                graph_metadata["full_text"] = item.content

                if _upsert_graph_document(
                    graph_doc_id,
                    item.fingerprint,
                    source=item.metadata.get("source", "unknown"),
                    metadata=graph_metadata,
                    chunk_count=chunk_count,
                    context=fast_context,
                ):
                    graph_writes += 1
                    if graph_log_samples < 3:
                        logger.info(
                            "[graphdb] upsert doc=%s",
                            item.uid,
                        )
                        graph_log_samples += 1

                indexed_items[item.uid] = {
                    "fingerprint": item.fingerprint,
                    "metadata": enriched_metadata,
                    "mtime": mtime,
                    "size": size,
                }
                source_origin = item.metadata.get("source", "unknown")
                per_origin[source_origin] = per_origin.get(source_origin, 0) + 1
                new_documents += 1

            except BudgetExceededError as e:
                logger.error(f"🛑 BUDGET EXCEEDED during indexing {item.uid}.")
                _delete_document_points(item.uid)
                if graph_db.is_enabled():
                    graph_db.delete_node(graph_doc_id)
                raise e

    finally:
        for source_name, source in sources_with_name:
            close = getattr(source, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    stale_documents = set(previous_index.keys()) - current_document_ids
    if stale_documents:
        logger.info(f"[vectorstore] Removing {len(stale_documents)} stale documents.")

    for document_id in stale_documents:
        _delete_document_points(document_id)

        # Calculate graph ID for GraphDB cleanup
        graph_doc_id_to_delete = document_id
        try:
            prev_meta = previous_index.get(document_id, {}).get("metadata", {})
            fname = prev_meta.get("filename") or prev_meta.get("file_name")
            graph_ids_to_delete = {graph_doc_id_to_delete}
            if fname:
                graph_doc_id_to_delete = build_kb_label(Path(fname))
                graph_ids_to_delete.update(build_document_label_candidates(Path(fname)))
            else:
                graph_ids_to_delete = {graph_doc_id_to_delete}
        except Exception:
            graph_ids_to_delete = {graph_doc_id_to_delete}

        if graph_db.is_enabled():
            for graph_id in graph_ids_to_delete:
                graph_db.delete_node(graph_id)

        indexed_items.pop(document_id, None)

    if graph_db.is_enabled() and stale_documents:
        deleted_count = graph_db.delete_orphan_nodes()
        if deleted_count > 0:
            logger.info(
                "[graphdb] Garbage Collector: cleaned up %d orphan nodes", deleted_count
            )

    origin_summary = (
        ", ".join(f"{name}={count}" for name, count in per_origin.items())
        if per_origin
        else "nessuna sorgente"
    )
    graph_summary = (
        f"graphdb={graph_writes}" if graph_writes else "graphdb=0 (skip/disabled)"
    )
    logger.info(
        "[vectorstore] %s nuovi/modificati, %s skiapati. (%s; %s)",
        new_documents,
        skipped_documents,
        origin_summary,
        graph_summary,
    )

    mode_label = "incremental" if incremental else "full"
    INDEXING_RUNS_TOTAL.labels(mode=mode_label).inc()
    duration = time.perf_counter() - start_time
    INDEXING_DURATION_SECONDS.labels(mode=mode_label).observe(duration)
    if new_documents > 0:
        telemetry.increment("indexing.new_documents", value=new_documents)
        INDEXED_DOCUMENTS_TOTAL.inc(new_documents)
    INDEXED_DOCUMENTS_GAUGE.set(len(indexed_items))
    _persist_index_state()

    return new_documents


def _build_kb_label_filter(kb_label: str) -> Filter | None:
    candidate = str(kb_label or "").strip().lower()
    if not candidate:
        return None

    labels = [candidate]
    if not is_supported_document_label(candidate):
        labels = build_document_label_candidates(candidate)

    conditions = [
        FieldCondition(key=field, match=MatchValue(value=label))
        for label in labels
        for field in ("document_id", "kb_label", "doc_label", "jira_label", "label")
    ]
    if not conditions:
        return None

    return Filter(should=conditions)


def _build_tenant_filter() -> Filter | None:
    """Costruisce un filtro Qdrant per il tenant corrente."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return None
    return Filter(
        must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
    )


def _merge_filters(*filters: Filter | None) -> Filter | None:
    """Combina più filtri Qdrant in un unico filtro con clausola must."""
    must_conditions = []
    should_conditions = []
    for f in filters:
        if f is None:
            continue
        if f.must:
            must_conditions.extend(f.must)
        if f.should:
            # Wrap should in a nested filter within must
            must_conditions.append(Filter(should=f.should))
    if not must_conditions and not should_conditions:
        return None
    return Filter(must=must_conditions if must_conditions else None)


def search(query_vector, limit: int = 15, kb_label: str | None = None):
    """Esegue ricerca in Qdrant con il vettore query e aggiorna il grafo con archi SIMILAR."""
    start = time.perf_counter()
    kb_filter = _build_kb_label_filter(kb_label) if kb_label else None
    tenant_filter = _build_tenant_filter()
    combined_filter = _merge_filters(kb_filter, tenant_filter)
    results = []
    for attempt in range(3):
        try:
            response = QDRANT.query_points(
                collection_name=COLLECTION,
                query=query_vector,
                limit=limit,
                query_filter=combined_filter,
            )
            results = response.points
            break
        except Exception as exc:
            if attempt < 2:
                # backoff jitter per contenzione server Qdrant
                time.sleep(0.05 * (2**attempt) + random.random() * 0.02)
                continue
            logger.warning(
                "[vectorstore] ricerca Qdrant fallita dopo retry, ritorno lista vuota: %s",
                exc,
            )
            RETRIEVAL_LATENCY_SECONDS.observe(time.perf_counter() - start)
            return []
    RETRIEVAL_LATENCY_SECONDS.observe(time.perf_counter() - start)

    # Hook opzionale GraphRAG (se flag on e SDK presente). Oggi no-op se disabilitato.
    results = graphrag_adapter.expand_with_graph(results, query_vector, limit)

    if graph_db.is_enabled():
        try:
            # Collega solo i top-N documenti tra loro per evitare esplosione del grafo
            doc_ids = []
            for hit in results:
                payload = getattr(hit, "payload", None) or {}
                doc_id = payload.get("document_id")
                if isinstance(doc_id, str) and doc_id.strip():
                    doc_ids.append((doc_id, getattr(hit, "score", None)))
            # SIMILAR relationships removed - replaced with intelligent relationship detection
        except Exception as exc:  # pragma: no cover - log ma continua
            logger.warning("[graphdb] error during graph update: %s", exc)

    return results
