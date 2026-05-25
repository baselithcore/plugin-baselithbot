"""Cross-encoder reranker per hit del vector store.

Porta da `graphrag/insurance/reranker.py` con differenze:
- Device configurabile via `RERANKER_DEVICE` (cuda su DGX Spark, mps su Mac).
- Accetta sia `hit["payload"]["text"]` che `hit["payload"]["raw_text"]`.
- Idempotente: fallback trasparente se sentence-transformers o modello mancano.

Perché: il retrieval ibrido (dense+sparse±ColBERT) seleziona candidati veloci
ma "ciechi" alla relazione query↔passage. Un cross-encoder rianima ciascuna
coppia → rimuove duplicati quasi-identici e boosta relevance semantica.
Impatto empirico: +15-25% precisione su query tecniche italiane.

Pipeline:
  hybrid_search(top_k * input_mult)  →  rerank  →  top_k
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from llm_wiki.config import (
    RERANKER_BATCH_SIZE,
    RERANKER_DEVICE,
    RERANKER_ENABLED,
    RERANKER_INPUT_MULT,
    RERANKER_MODEL,
)

logger = logging.getLogger(__name__)

_model: Any = None
_lock = threading.Lock()
_failed = False


def _load_model() -> Any:
    global _model, _failed
    if _model is not None or _failed:
        return _model
    with _lock:
        if _model is not None or _failed:
            return _model
        try:
            from sentence_transformers import CrossEncoder  # type: ignore[import-not-found]

            kwargs: dict[str, Any] = {"max_length": 1024}
            if RERANKER_DEVICE != "auto":
                kwargs["device"] = RERANKER_DEVICE
            logger.info(
                "[reranker] caricamento cross-encoder: %s (device=%s)",
                RERANKER_MODEL,
                RERANKER_DEVICE,
            )
            _model = CrossEncoder(RERANKER_MODEL, **kwargs)
        except ImportError:
            logger.warning(
                "[reranker] sentence-transformers non installato — reranker disabilitato"
            )
            _failed = True
        except Exception as exc:
            logger.warning(
                "[reranker] load fallito (%s) — fallback a ordering originale", exc
            )
            _failed = True
    return _model


def is_available() -> bool:
    """True se il modello è caricato e pronto."""
    return RERANKER_ENABLED and _load_model() is not None


def _passage_text(hit: dict[str, Any]) -> str:
    """Estrae il testo rilevante dal hit, preferendo raw_text se disponibile."""
    payload = hit.get("payload") or {}
    # raw_text è il chunk senza il prefisso meta; più pulito per reranking.
    return str(payload.get("raw_text") or payload.get("text") or hit.get("text") or "")


def _dedupe(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per `document_id` tieni solo il chunk col miglior vector score.

    Riduce il lavoro del cross-encoder evitando di reranking-are chunks
    dello stesso doc (spesso ridondanti dopo ColBERT fusion).
    """
    best: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for h in hits:
        doc_id = str(h.get("payload", {}).get("document_id") or h.get("id") or id(h))
        if doc_id not in best or float(h.get("score") or 0) > float(
            best[doc_id].get("score") or 0
        ):
            if doc_id not in best:
                order.append(doc_id)
            best[doc_id] = h
    return [best[d] for d in order]


def rerank(
    query: str,
    hits: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    """Re-score coppie (query, passage) via cross-encoder, ritorna top_k.

    Ottimizzazioni:
    - dedup per `document_id` prima del predict (riduce le coppie)
    - batch size configurabile via `RERANKER_BATCH_SIZE` (32 default, 64 su CUDA)
    - batch singolo per l'intera lista (CrossEncoder.predict già batch-aware)

    Aggiunge `rerank_score`, preserva lo `score` originale come `vector_score`,
    e riscrive `score` con il rerank score per uniformità downstream.
    """
    if not RERANKER_ENABLED or not hits:
        return hits[:top_k]

    model = _load_model()
    if model is None:
        return hits[:top_k]

    # Dedup pre-rerank: 1 chunk migliore per doc_id
    unique = _dedupe(hits)

    pairs: list[tuple[str, str]] = [(query, _passage_text(h)[:1800]) for h in unique]

    try:
        scores = model.predict(
            pairs, batch_size=RERANKER_BATCH_SIZE, show_progress_bar=False
        )
    except Exception as exc:
        logger.warning(
            "[reranker] predict fallito (%s) — fallback ordering originale", exc
        )
        return unique[:top_k]

    enriched: list[dict[str, Any]] = []
    for hit, score in zip(unique, scores, strict=True):
        out = dict(hit)
        out["rerank_score"] = float(score)
        out["vector_score"] = float(hit.get("score") or 0.0)
        out["score"] = float(score)
        enriched.append(out)

    enriched.sort(key=lambda h: h.get("rerank_score", 0.0), reverse=True)
    return enriched[:top_k]


def prefetch_limit(top_k: int) -> int:
    """Quanto prefetchare dal retrieval prima del rerank."""
    return top_k * RERANKER_INPUT_MULT if RERANKER_ENABLED else top_k
