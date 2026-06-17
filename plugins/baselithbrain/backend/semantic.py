"""Optional semantic layer (embeddings) — degrades gracefully when absent.

Semantic search and derived graph edges are opt-in (``BASELITHBRAIN_SEMANTIC_
ENABLED=true``) and require an embedder. We reuse the host's cached embedder
(``core.nlp.get_embedder``) when available; if the dependency or model is
missing the whole layer disables itself and the plugin keeps working in pure
keyword/explicit-link mode. Local-first is never compromised.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from core.observability.logging import get_logger

from .embedding_cache import EmbeddingCache, content_key

logger = get_logger(__name__)


def _embedding_model_name() -> str | None:
    """Best-effort name of the configured embedding model (for cache tagging)."""
    try:
        from core.config import get_vectorstore_config  # noqa: PLC0415

        return str(get_vectorstore_config().embedding_model)
    except Exception:  # noqa: BLE001 — tag is optional
        return None


class SemanticIndex:
    """Note embeddings with cosine similarity, persisted across restarts.

    Best-effort: disables itself if no embedder is available; vectors are
    memoised by content hash (:class:`EmbeddingCache`) so a rebuild only embeds
    notes whose text changed.
    """

    def __init__(self, vault_root: Path | None = None) -> None:
        self._vectors: dict[str, list[float]] = {}
        self._embedder: Any | None = None
        self._available = False
        self._cache = EmbeddingCache(vault_root)

    async def _ensure_embedder(self) -> bool:
        if self._embedder is not None:
            return True
        try:
            from core.nlp import get_embedder  # noqa: PLC0415

            self._embedder = get_embedder()
            self._available = True
        except Exception as exc:  # noqa: BLE001 — optional feature
            logger.info("BaselithBrain semantic layer disabled: %s", exc)
            self._available = False
        return self._available

    async def _embed(self, text: str) -> list[float] | None:
        if not await self._ensure_embedder():
            return None
        try:
            vec = await self._embedder.encode(text)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("embed failed: %s", exc)
            return None
        return [float(x) for x in (vec.tolist() if hasattr(vec, "tolist") else vec)]

    async def rebuild(self, texts: dict[str, str]) -> None:
        """Embed every note, reusing cached vectors for unchanged text.

        No-op if the embedder is unavailable. Only notes whose content hash is
        absent from the persistent cache are re-embedded; the cache is then
        pruned to the live set and flushed to disk.
        """
        self._vectors.clear()
        if not await self._ensure_embedder():
            return
        self._cache.ensure_model(_embedding_model_name())
        keys: set[str] = set()
        for note_id, text in texts.items():
            key = content_key(text)
            keys.add(key)
            vec = self._cache.get(key)
            if vec is None:
                vec = await self._embed(text)
                if vec is not None:
                    self._cache.put(key, vec)
            if vec is not None:
                self._vectors[note_id] = vec
        self._cache.prune(keys)
        self._cache.save()

    @property
    def available(self) -> bool:
        return self._available and bool(self._vectors)

    async def query(self, text: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Return ``(note_id, score)`` ranked by cosine similarity."""
        vec = await self._embed(text)
        if vec is None:
            return []
        scored = [(nid, _cosine(vec, v)) for nid, v in self._vectors.items()]
        scored.sort(key=lambda p: p[1], reverse=True)
        return scored[:top_k]

    def neighbors(
        self, note_id: str, top_k: int, threshold: float
    ) -> list[tuple[str, float]]:
        """Most similar notes to ``note_id`` above ``threshold`` (excl. self)."""
        base = self._vectors.get(note_id)
        if base is None:
            return []
        scored = [
            (nid, _cosine(base, v))
            for nid, v in self._vectors.items()
            if nid != note_id
        ]
        scored = [p for p in scored if p[1] >= threshold]
        scored.sort(key=lambda p: p[1], reverse=True)
        return scored[:top_k]


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
