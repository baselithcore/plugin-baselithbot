"""Semantic recall of historical stints — reuses core retrieval primitives.

Rather than reimplementing search, this wraps the framework's own
:class:`~core.memory.hybrid_search.BM25Index` for keyword recall and, when
``semantic_enabled`` is set, the core embedder
(:func:`~core.nlp.models.get_embedder`) for dense cosine ranking. Both degrade
gracefully: if the optional NLP extras are absent, recall falls back to BM25;
if no corpus exists, recall returns an empty list. The plugin therefore boots
self-contained while still benefiting from core machinery when present.
"""

from __future__ import annotations

import math

from core.memory.hybrid_search import BM25Index
from core.observability.logging import get_logger

logger = get_logger(__name__)

# A small seed corpus of archetypal strategy outcomes so recall is useful from
# the first lap. Real deployments append live stint summaries via ``remember``.
_SEED: dict[str, str] = {
    "h-undercut-medium": (
        "Undercut from P4 on worn mediums with a close gap ahead; boxed early "
        "for fresh softs and jumped the car in front within three laps."
    ),
    "h-overcut-hard": (
        "Extended the hard stint while rivals pitted into traffic; track "
        "position held and the overcut gained two places at the flag."
    ),
    "h-thermal-derate": (
        "Power-unit thermals spiked in clean air; switched to a conservative "
        "engine mode and lifted to protect the unit, losing little lap time."
    ),
    "h-cliff-blowout": (
        "Stayed out past the soft tyre cliff chasing track position; "
        "degradation fell off sharply and cost more time than an early stop."
    ),
}


class HistoricalRecall:
    """Keyword + optional-dense recall over past stint/decision summaries."""

    def __init__(self, semantic_enabled: bool = False, top_k: int = 5) -> None:
        self._docs: dict[str, str] = dict(_SEED)
        self._top_k = top_k
        self._semantic = semantic_enabled
        self._bm25 = BM25Index()
        self._embedder = None
        self._embeddings: dict[str, list[float]] = {}
        self._reindex()
        if semantic_enabled:
            self._try_load_embedder()

    def _try_load_embedder(self) -> None:
        """Best-effort load of the core embedder; stay on BM25 if unavailable."""
        try:
            from core.nlp.models import get_embedder

            self._embedder = get_embedder()
        except Exception as exc:  # noqa: BLE001 — optional extra
            logger.info("pitwall_embedder_unavailable", error=str(exc))
            self._embedder = None

    def _reindex(self) -> None:
        """Rebuild the BM25 index over the current corpus."""
        self._bm25.index(self._docs)

    def remember(self, doc_id: str, summary: str) -> None:
        """Add a stint/decision summary to the recall corpus."""
        self._docs[doc_id] = summary
        self._reindex()
        self._embeddings.pop(doc_id, None)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two equal-length vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    async def recall(self, query: str) -> list[str]:
        """Return up to ``top_k`` historical summaries most relevant to ``query``."""
        if not self._docs:
            return []
        if self._semantic and self._embedder is not None:
            try:
                return await self._recall_dense(query)
            except Exception as exc:  # noqa: BLE001 — fall back to keyword
                logger.debug("pitwall_dense_recall_failed", error=str(exc))
        hits = self._bm25.search(query, top_k=self._top_k)
        return [self._docs[h.doc_id] for h in hits if h.doc_id in self._docs]

    async def _recall_dense(self, query: str) -> list[str]:
        """Dense cosine recall using the core embedder."""
        assert self._embedder is not None
        missing = [d for d in self._docs if d not in self._embeddings]
        if missing:
            vectors = await self._embedder.encode([self._docs[d] for d in missing])
            for doc_id, vec in zip(missing, vectors):
                self._embeddings[doc_id] = list(vec)
        q_vec = list((await self._embedder.encode([query]))[0])
        scored = sorted(
            ((self._cosine(q_vec, self._embeddings[d]), d) for d in self._docs),
            key=lambda t: t[0],
            reverse=True,
        )
        return [self._docs[d] for _, d in scored[: self._top_k]]


__all__ = ["HistoricalRecall"]
