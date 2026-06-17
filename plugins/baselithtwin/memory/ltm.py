"""Long-term memory retrieval over the twin's salient facts.

Provides relevance scoring of stored :class:`SalientFact` records against an
inbound message so the draft engine can ground a reply in what the twin already
knows about a contact. Retrieval works **zero-infra** via a lightweight
keyword/recency score; when ``semantic_enabled`` is set it best-effort enriches
ranking with dense embeddings from the core embedder, degrading silently to
keyword scoring if embeddings are unavailable.

This bridges to ``core/memory`` conceptually (the framework's hierarchical
STM→MTM→LTM) without hard-coupling: the durable index of record is the plugin
store; the core memory bridge is an optional, fault-tolerant enrichment.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from ..models import SalientFact

_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_STOPWORDS = frozenset(
    {"the", "and", "for", "you", "che", "non", "per", "con", "una", "are", "is"}
)


def _tokens(text: str) -> list[str]:
    """Lowercase content tokens with stopwords removed."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def _keyword_score(query_tokens: Counter[str], fact: SalientFact) -> float:
    """TF-overlap score weighted by the fact's own salience."""
    fact_tokens = Counter(_tokens(fact.text))
    if not fact_tokens or not query_tokens:
        return 0.0
    overlap = sum(min(query_tokens[t], fact_tokens[t]) for t in query_tokens)
    norm = math.sqrt(sum(query_tokens.values()) * sum(fact_tokens.values()))
    return (overlap / norm) * (0.5 + 0.5 * fact.salience) if norm else 0.0


class LTMIndex:
    """Ranks salient facts for relevance to an inbound message."""

    def __init__(self, semantic_enabled: bool = False) -> None:
        self._semantic = semantic_enabled

    async def relevant(
        self, query: str, facts: list[SalientFact], top_k: int = 5
    ) -> list[SalientFact]:
        """Return up to ``top_k`` facts most relevant to ``query``.

        Always falls back to keyword scoring; dense embeddings are used only as a
        best-effort blend when enabled and importable.
        """
        if not facts or top_k <= 0:
            return []
        query_tokens = Counter(_tokens(query))
        scored = [(self._keyword(query_tokens, f), f) for f in facts]
        if self._semantic:
            scored = await self._blend_semantic(query, scored)
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [fact for score, fact in scored[:top_k] if score > 0.0]

    @staticmethod
    def _keyword(query_tokens: Counter[str], fact: SalientFact) -> float:
        return _keyword_score(query_tokens, fact)

    async def _blend_semantic(
        self, query: str, scored: list[tuple[float, SalientFact]]
    ) -> list[tuple[float, SalientFact]]:
        """Best-effort dense re-rank; returns the input unchanged on any failure."""
        try:
            from core.nlp.models import get_embedder

            embedder = get_embedder()
            q_vec = (await _embed(embedder, [query]))[0]
            f_vecs = await _embed(embedder, [f.text for _, f in scored])
        except Exception:  # noqa: BLE001 — degrade to keyword scoring
            return scored
        blended: list[tuple[float, SalientFact]] = []
        for (kw, fact), f_vec in zip(scored, f_vecs):
            blended.append((0.5 * kw + 0.5 * _cosine(q_vec, f_vec), fact))
        return blended


async def _embed(embedder: object, texts: list[str]) -> list[list[float]]:
    """Call whichever async/sync embed method the core embedder exposes."""
    for name in ("aembed_documents", "embed_documents", "aembed", "embed"):
        fn = getattr(embedder, name, None)
        if fn is None:
            continue
        result = fn(texts)
        return await result if hasattr(result, "__await__") else result
    raise AttributeError("no embed method on embedder")


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity, guarding against zero vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


__all__ = ["LTMIndex"]
