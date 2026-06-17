"""Search service — BM25 keyword ranking, optionally fused with semantic.

Reuses the host's pure-Python BM25 (``core.memory.hybrid_search``) so keyword
search works with zero external infrastructure. When the semantic layer is
available, results are fused via Reciprocal Rank Fusion (``HybridSearcher``)
for the best of dense + sparse retrieval.
"""

from __future__ import annotations

from core.memory.hybrid_search import BM25Index, HybridSearcher, ScoredHit

from .models import SearchHit
from .semantic import SemanticIndex


def _snippet(body: str, query: str, width: int = 160) -> str:
    """Extract a context window around the first query-term hit."""
    low_body, low_q = body.lower(), query.lower().strip()
    idx = low_body.find(low_q) if low_q else -1
    if idx < 0:
        terms = [t for t in low_q.split() if t]
        idx = next((low_body.find(t) for t in terms if low_body.find(t) >= 0), 0)
        idx = max(idx, 0)
    start = max(0, idx - width // 3)
    text = body[start : start + width].replace("\n", " ").strip()
    return (
        ("…" if start > 0 else "") + text + ("…" if start + width < len(body) else "")
    )


class SearchService:
    """Builds a BM25 index over note bodies; fuses with semantic when present."""

    def __init__(self, semantic: SemanticIndex) -> None:
        self._bm25 = BM25Index()
        self._semantic = semantic
        self._titles: dict[str, str] = {}
        self._bodies: dict[str, str] = {}

    def rebuild(self, titles: dict[str, str], bodies: dict[str, str]) -> None:
        """Index ``title + body`` per note for keyword retrieval."""
        self._titles = dict(titles)
        self._bodies = dict(bodies)
        docs = {nid: f"{titles.get(nid, '')}\n{bodies.get(nid, '')}" for nid in bodies}
        self._bm25.index(docs)

    async def search(
        self, query: str, top_k: int = 20, scope: set[str] | None = None
    ) -> list[SearchHit]:
        if not query.strip():
            return []
        # Over-fetch when scoped so the post-filter still yields ``top_k`` hits.
        fetch = top_k if scope is None else top_k * 4
        bm25_hits = self._bm25.search(query, top_k=fetch)

        if self._semantic.available:
            sem = await self._semantic.query(query, top_k=fetch)
            dense = [ScoredHit(doc_id=nid, score=score) for nid, score in sem]
            fused = HybridSearcher().fuse(bm25=bm25_hits, dense=dense, top_k=fetch)
            hits = [self._to_hit(h, "hybrid", query) for h in fused]
        else:
            hits = [self._to_hit(h, "keyword", query) for h in bm25_hits]

        if scope is not None:
            hits = [h for h in hits if h.id in scope]
        return hits[:top_k]

    def _to_hit(self, hit: ScoredHit, kind: str, query: str) -> SearchHit:
        return SearchHit(
            id=hit.doc_id,
            title=self._titles.get(hit.doc_id, hit.doc_id),
            score=round(hit.score, 4),
            snippet=_snippet(self._bodies.get(hit.doc_id, ""), query),
            kind=kind,
        )
