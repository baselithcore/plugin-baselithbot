"""Maximal Marginal Relevance (MMR) post-rerank diversification.

Risolve il problema di top-K omogeneo: dopo dedup per ``document_id`` +
cross-encoder rerank, i top-K possono comunque essere chunk dello stesso
"vicinato semantico" (stessa pagina concettuale spezzata, paragrafi
sinonimi su sezioni diverse). MMR riequilibra rilevanza vs diversità:

    score(d) = λ · rel(d, q) − (1 − λ) · max_{d' ∈ S} sim(d, d')

dove ``S`` è il set già selezionato, ``rel`` lo score del reranker
(normalizzato min-max), e ``sim`` il coseno fra embedding densi dei
candidati. ``λ ∈ [0,1]``: 1.0 = relevance pura (MMR off), 0.0 =
diversità pura. Default 0.7 = forte preferenza al ranking originale ma
penalizza ridondanza marcata.

Note:
- Lavora **dopo** il rerank cross-encoder: il rerank score è il
  segnale di rilevanza più affidabile che abbiamo.
- Embedda i passage con l'embedder dense esistente (un singolo batch).
  Costo dominato dalla forward pass, ~50ms su GPU per 24 chunk × 1024
  dim. Trascurabile vs rerank predict.
- Fallback no-op trasparente se l'embedder non risponde o se ``len(hits)
  ≤ top_k`` (niente da diversificare).
"""

from __future__ import annotations

import logging
import math
from typing import Any

from llm_wiki.config import MMR_ENABLED, MMR_LAMBDA
from llm_wiki.vectorstore.embedder import get_embedder

logger = logging.getLogger(__name__)


def _passage_text(hit: dict[str, Any]) -> str:
    payload = hit.get("payload") or {}
    return str(payload.get("raw_text") or payload.get("text") or hit.get("text") or "")


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-12:
        return vec
    inv = 1.0 / norm
    return [x * inv for x in vec]


def _cosine_pre_normalized(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return values
    lo = min(values)
    hi = max(values)
    if hi - lo < 1e-12:
        return [1.0] * len(values)
    span = hi - lo
    return [(v - lo) / span for v in values]


def diversify(
    hits: list[dict[str, Any]],
    *,
    top_k: int,
    lambda_: float | None = None,
) -> list[dict[str, Any]]:
    """Riordina i ``hits`` con MMR e ritorna i top-K diversificati.

    Args:
        hits: lista hit già reranked (ordinati per ``score`` desc).
        top_k: quanti hit ritornare.
        lambda_: trade-off relevance↔diversità. ``None`` = config default.

    Returns:
        Sub-lista di ``hits`` di lunghezza ≤ ``top_k``. Aggiunge campo
        ``mmr_rank`` (posizione MMR, 0-based) sugli hit selezionati.
        Preserva il resto del payload verbatim.
    """
    if not MMR_ENABLED or len(hits) <= top_k or top_k <= 1:
        return hits[:top_k]

    lam = MMR_LAMBDA if lambda_ is None else lambda_
    lam = max(0.0, min(1.0, lam))

    embedder = get_embedder()
    if embedder is None:
        return hits[:top_k]

    texts = [_passage_text(h)[:2000] for h in hits]
    if not all(texts):
        return hits[:top_k]

    try:
        out = embedder.encode(texts, is_query=False)
    except Exception as exc:
        logger.warning("[mmr] embedding fallito (%s) — fallback rerank ordering", exc)
        return hits[:top_k]

    if not out.dense or len(out.dense) != len(hits):
        return hits[:top_k]

    vectors = [_normalize(v) for v in out.dense]
    relevance = _minmax([float(h.get("score") or 0.0) for h in hits])

    selected_idx: list[int] = []
    candidates = list(range(len(hits)))

    while len(selected_idx) < top_k and candidates:
        best_c = -1
        best_score = -math.inf
        for c in candidates:
            if selected_idx:
                sim_to_set = max(
                    _cosine_pre_normalized(vectors[c], vectors[s]) for s in selected_idx
                )
            else:
                sim_to_set = 0.0
            mmr_score = lam * relevance[c] - (1.0 - lam) * sim_to_set
            if mmr_score > best_score:
                best_score = mmr_score
                best_c = c
        if best_c < 0:
            break
        selected_idx.append(best_c)
        candidates.remove(best_c)

    out_hits: list[dict[str, Any]] = []
    for rank, idx in enumerate(selected_idx):
        h = dict(hits[idx])
        h["mmr_rank"] = rank
        out_hits.append(h)
    return out_hits
