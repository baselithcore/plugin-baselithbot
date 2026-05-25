# app/vectorstore/state.py
"""State management for indexed documents tracking and persistence."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

from agent_jira.config import COLLECTION, INDEX_STATE_PATH

logger = logging.getLogger(__name__)

# Registro documenti indicizzati (incremental indexing)
indexed_items: Dict[str, Dict[str, Any]] = {}
_state_loaded = False


def _load_persistent_index_state() -> bool:
    """Load indexed documents state from disk."""
    global indexed_items, _state_loaded
    if _state_loaded:
        return True
    if not INDEX_STATE_PATH.exists():
        return False
    try:
        raw = INDEX_STATE_PATH.read_text(encoding="utf-8")
        payload = json.loads(raw)
        if isinstance(payload, dict):
            new_items = {
                str(doc_id): value
                for doc_id, value in payload.items()
                if isinstance(value, dict) and "fingerprint" in value
            }
            indexed_items.clear()
            indexed_items.update(new_items)
            _state_loaded = True
            return True
    except Exception as exc:  # pragma: no cover - log but continue
        logger.warning(
            "[vectorstore] Impossibile leggere INDEX_STATE_PATH (%s): %s",
            INDEX_STATE_PATH,
            exc,
        )
    return False


def _persist_index_state() -> None:
    """Save indexed documents state to disk."""
    global _state_loaded
    try:
        INDEX_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(indexed_items, ensure_ascii=False)
        INDEX_STATE_PATH.write_text(serialized, encoding="utf-8")
        _state_loaded = True
    except Exception as exc:  # pragma: no cover - log but continue
        logger.warning(
            "[vectorstore] Impossibile salvare INDEX_STATE_PATH (%s): %s",
            INDEX_STATE_PATH,
            exc,
        )


def _extract_payload_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Estrae i metadati più rilevanti dal payload Qdrant."""
    filtered: Dict[str, Any] = {}
    for key, value in payload.items():
        if key in {"document_id", "fingerprint", "text", "chunk_body"}:
            continue
        if key.startswith("chunk_"):
            continue
        filtered[key] = value
    return filtered


_last_sync_ts = 0.0
INDEX_SYNC_COOLDOWN = 60.0  # seconds


def _refresh_indexed_items(*, force: bool = False) -> None:
    """Sincronizza lo stato locale degli UID indicizzati con Qdrant."""
    global indexed_items, _last_sync_ts

    now = time.time()
    if not force:
        if indexed_items:
            return
        if _load_persistent_index_state():
            return
    else:
        # Throttling: evita scansioni complete troppo frequenti (es. ogni chat turn)
        if indexed_items and (now - _last_sync_ts < INDEX_SYNC_COOLDOWN):
            return

    # Import here to avoid circular dependency
    from agent_jira.vectorstore.qdrant_ops import (
        INDEX_SCROLL_PAGE_SIZE,
        QDRANT,
        create_collection,
    )

    # Garantisce l'esistenza della collezione prima di interrogarla
    create_collection()

    refreshed: Dict[str, Dict[str, Any]] = {}
    offset = None

    while True:
        try:
            points, offset = QDRANT.scroll(  # type: ignore[arg-type]
                collection_name=COLLECTION,
                limit=INDEX_SCROLL_PAGE_SIZE,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            # Collection assente/non inizializzata
            if "not found" in str(exc).lower():
                create_collection()
                break
            raise

        for point in points:
            payload = point.payload or {}
            document_id = payload.get("document_id")
            fingerprint = payload.get("fingerprint")
            if not document_id or not fingerprint:
                continue

            entry = refreshed.get(document_id)
            if entry is None:
                entry = {"fingerprint": fingerprint}
                metadata = _extract_payload_metadata(payload)
                if metadata:
                    entry["metadata"] = metadata
                refreshed[document_id] = entry
            else:
                if "metadata" not in entry:
                    metadata = _extract_payload_metadata(payload)
                    if metadata:
                        entry["metadata"] = metadata

        if offset is None:
            break

    indexed_items.clear()
    indexed_items.update(refreshed)
    _last_sync_ts = now
    _persist_index_state()


def list_indexed_documents() -> list[dict[str, Any]]:
    """Restituisce elenco dei documenti indicizzati (uid + metadata essenziali)."""
    _refresh_indexed_items(force=True)
    docs: list[dict[str, Any]] = []
    for uid, meta in indexed_items.items():
        entry = {"document_id": uid, "metadata": meta.get("metadata", {})}
        docs.append(entry)
    return docs


# Load state on module import
_load_persistent_index_state()
