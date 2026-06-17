"""Persistent embedding cache — memoise note vectors across restarts.

Embeddings are deterministic for a given (model, text), so re-embedding the
whole vault on every restart *and* on every note write (each write rebuilds the
index) is pure waste. We memoise vectors in ``<vault>/.brain/embeddings.json``
keyed by a SHA-256 of the note text: a rebuild only embeds notes whose content
actually changed; everything else is a dict hit.

A ``model`` tag (the configured embedding model name) is stored alongside the
vectors. If the model changes, cached vectors would have the wrong geometry, so
a tag mismatch drops the cache wholesale.

Best-effort: any IO/parse error degrades to an empty in-memory cache, so the
semantic layer still works (it just recomputes) and never breaks.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from core.observability.logging import get_logger

logger = get_logger(__name__)


def content_key(text: str) -> str:
    """Stable cache key for a note's embeddable text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingCache:
    """A content-hash → vector store persisted as one JSON file."""

    def __init__(self, vault_root: Path | None) -> None:
        self._path = (vault_root / ".brain" / "embeddings.json") if vault_root else None
        self._store: dict[str, list[float]] = {}
        self._model: str | None = None
        self._load()

    def _load(self) -> None:
        if self._path is None or not self._path.is_file():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("embedding cache load failed: %s", exc)
            return
        if not isinstance(raw, dict):
            return
        self._model = raw.get("model")
        vectors = raw.get("vectors")
        if isinstance(vectors, dict):
            self._store = {
                k: [float(x) for x in v]
                for k, v in vectors.items()
                if isinstance(v, list)
            }

    def ensure_model(self, model: str | None) -> None:
        """Drop everything if the embedding model changed (stale geometry)."""
        if model is not None and self._model is not None and model != self._model:
            logger.info(
                "embedding model changed (%s → %s) — clearing cache",
                self._model,
                model,
            )
            self._store.clear()
        self._model = model

    def get(self, key: str) -> list[float] | None:
        return self._store.get(key)

    def put(self, key: str, vector: list[float]) -> None:
        self._store[key] = vector

    def prune(self, keep: set[str]) -> None:
        """Forget vectors no longer backing any live note."""
        self._store = {k: v for k, v in self._store.items() if k in keep}

    def save(self) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_name(self._path.name + ".tmp")
            tmp.write_text(
                json.dumps({"model": self._model, "vectors": self._store}),
                encoding="utf-8",
            )
            tmp.replace(self._path)
        except OSError as exc:
            logger.warning("embedding cache save failed: %s", exc)
