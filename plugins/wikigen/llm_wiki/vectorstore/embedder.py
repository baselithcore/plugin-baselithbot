"""Embedder unificato con tre strategie, scelte via config:

- **BGE-M3** (BAAI/bge-m3) via FlagEmbedding → dense + sparse + ColBERT in un
  singolo forward pass. Consigliato per italiano multilingue + retrieval ibrido.
- **Ollama** (es. `OLLAMA_EMBED_MODEL=bge-m3` o `nomic-embed-text`) → solo dense.
  Comodo se vuoi evitare dipendenze torch locali.
- **sentence-transformers** multilingue MiniLM come fallback leggero dense-only.

Pattern identico a `graphrag/vectorstore/embedder.py`: singleton thread-safe,
fallback trasparente se la dipendenza preferita manca.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from llm_wiki.config import (
    EMBEDDER_BATCH_SIZE,
    EMBEDDER_DEVICE,
    EMBEDDER_FORCE_LEGACY,
    EMBEDDER_HTTP_TIMEOUT,
    EMBEDDER_MODEL,
    EMBEDDER_URL,
    EMBEDDER_USE_FP16,
    HYBRID_USE_COLBERT,
    LEGACY_EMBEDDER_MODEL,
    OFFLINE_MODE,
    OLLAMA_EMBED_MODEL,
)

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingOutput:
    dense: list[list[float]]
    sparse: list[tuple[list[int], list[float]]] = field(default_factory=list)
    colbert: list[list[list[float]]] = field(default_factory=list)

    def has_sparse(self) -> bool:
        return bool(self.sparse)

    def has_colbert(self) -> bool:
        return bool(self.colbert)


class _BaseEmbedder:
    name: str = ""
    dense_dim: int = 0
    supports_sparse: bool = False
    supports_colbert: bool = False

    def encode(self, texts: list[str], *, is_query: bool = False) -> EmbeddingOutput:
        raise NotImplementedError


# --- BGE-M3 (FlagEmbedding) -------------------------------------------------


class BGEM3Embedder(_BaseEmbedder):
    name = "BAAI/bge-m3"
    dense_dim = 1024
    supports_sparse = True
    supports_colbert = True

    def __init__(self, model_id: str = "BAAI/bge-m3") -> None:
        from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-not-found]

        device = None if EMBEDDER_DEVICE == "auto" else EMBEDDER_DEVICE
        kwargs: dict[str, Any] = {"use_fp16": EMBEDDER_USE_FP16}
        if device:
            kwargs["devices"] = device
        self._model = BGEM3FlagModel(model_id, **kwargs)
        self.name = model_id

    def encode(self, texts: list[str], *, is_query: bool = False) -> EmbeddingOutput:
        if not texts:
            return EmbeddingOutput(dense=[])

        out = self._model.encode(
            texts,
            batch_size=EMBEDDER_BATCH_SIZE,
            max_length=8192,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=HYBRID_USE_COLBERT,
        )

        dense = [v.tolist() for v in out["dense_vecs"]]

        sparse: list[tuple[list[int], list[float]]] = []
        for lw in out.get("lexical_weights", []) or []:
            indices = [int(k) for k in lw.keys()]
            values = [float(v) for v in lw.values()]
            sparse.append((indices, values))

        colbert: list[list[list[float]]] = []
        if HYBRID_USE_COLBERT:
            for cv in out.get("colbert_vecs", []) or []:
                colbert.append(cv.tolist())

        return EmbeddingOutput(dense=dense, sparse=sparse, colbert=colbert)


# --- Remote BGE-M3 (server FastAPI su DGX) ----------------------------------


class RemoteBGEM3Embedder(_BaseEmbedder):
    """Client HTTP per server BGE-M3 remoto (es. DGX).

    Il server remoto è un wrapper di `FlagEmbedding.BGEM3FlagModel` che
    restituisce dense + sparse + ColBERT in un singolo POST `/encode`. Questo
    è l'unico modo per mantenere il retrieval ibrido completo: né Ollama né
    TEI supportano i 3 head di BGE-M3 in un'unica chiamata.

    Il codice server di riferimento è in `deploy/embedder_server/`.
    """

    name = "remote:BAAI/bge-m3"
    dense_dim = 1024
    supports_sparse = True
    supports_colbert = True

    def __init__(self, url: str) -> None:
        import httpx  # type: ignore[import-not-found]

        self._url = url.rstrip("/")
        self._client = httpx.Client(base_url=self._url, timeout=EMBEDDER_HTTP_TIMEOUT)
        self.name = f"remote:{self._url}"
        # ping opzionale: se fallisce, solleva così il caller vede subito il problema
        try:
            resp = self._client.get("/health")
            resp.raise_for_status()
            info = resp.json() if resp.content else {}
            self.dense_dim = int(info.get("dense_dim", 1024))
            logger.info("[embedder] remote BGE-M3 ok: %s (dim=%d)", self._url, self.dense_dim)
        except Exception as exc:
            logger.warning("[embedder] remote /health fallito (%s): uso default", exc)

    def encode(self, texts: list[str], *, is_query: bool = False) -> EmbeddingOutput:
        if not texts:
            return EmbeddingOutput(dense=[])
        payload = {
            "texts": texts,
            "return_colbert": HYBRID_USE_COLBERT,
            "batch_size": EMBEDDER_BATCH_SIZE,
            "is_query": is_query,
        }
        resp = self._client.post("/encode", json=payload)
        resp.raise_for_status()
        data = resp.json()
        sparse: list[tuple[list[int], list[float]]] = [
            (
                [int(i) for i in s.get("indices", [])],
                [float(v) for v in s.get("values", [])],
            )
            for s in data.get("sparse", [])
        ]
        return EmbeddingOutput(
            dense=data.get("dense", []),
            sparse=sparse,
            colbert=data.get("colbert", []) if HYBRID_USE_COLBERT else [],
        )


# --- Ollama embeddings ------------------------------------------------------


class OllamaEmbedder(_BaseEmbedder):
    """Usa le API embeddings di Ollama. Solo dense, nessun sparse."""

    supports_sparse = False
    supports_colbert = False

    def __init__(self, model_id: str) -> None:
        from llm_wiki.utils.llm import embed_ollama

        self._embed = embed_ollama
        self.name = f"ollama:{model_id}"
        self._model_id = model_id
        # dimensione probata con un ping
        try:
            probe = self._embed(["probe"], self._model_id)
            self.dense_dim = len(probe[0]) if probe and probe[0] else 1024
        except Exception:
            self.dense_dim = 1024

    def encode(self, texts: list[str], *, is_query: bool = False) -> EmbeddingOutput:
        if not texts:
            return EmbeddingOutput(dense=[])
        vectors = self._embed(texts, self._model_id)
        return EmbeddingOutput(dense=vectors)


# --- sentence-transformers (fallback dense-only) ----------------------------


class LegacySTEmbedder(_BaseEmbedder):
    supports_sparse = False
    supports_colbert = False

    def __init__(self, model_id: str) -> None:
        import os

        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

        if OFFLINE_MODE:
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            os.environ["HF_HUB_OFFLINE"] = "1"

        self._model = SentenceTransformer(model_id)
        self.name = model_id
        dim = getattr(self._model, "get_sentence_embedding_dimension", lambda: 384)()
        self.dense_dim = int(dim or 384)

    def encode(self, texts: list[str], *, is_query: bool = False) -> EmbeddingOutput:
        if not texts:
            return EmbeddingOutput(dense=[])
        vectors = self._model.encode(
            texts,
            batch_size=EMBEDDER_BATCH_SIZE,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return EmbeddingOutput(dense=[v.tolist() for v in vectors])


# --- singleton --------------------------------------------------------------


_embedder: _BaseEmbedder | None = None
_lock = threading.Lock()


def _build_embedder() -> _BaseEmbedder | None:
    if EMBEDDER_FORCE_LEGACY:
        try:
            logger.info("[embedder] forced legacy ST: %s", LEGACY_EMBEDDER_MODEL)
            return LegacySTEmbedder(LEGACY_EMBEDDER_MODEL)
        except Exception as exc:
            logger.error("[embedder] legacy load failed: %s", exc)
            return None

    # Priorità massima: server BGE-M3 remoto (es. DGX) — preserva retrieval hybrid.
    if EMBEDDER_URL:
        try:
            logger.info("[embedder] using remote BGE-M3 server: %s", EMBEDDER_URL)
            return RemoteBGEM3Embedder(EMBEDDER_URL)
        except ImportError:
            logger.error(
                "[embedder] httpx non installato: `pip install httpx`. "
                "Impossibile usare EMBEDDER_URL; provo fallback."
            )
        except Exception as exc:
            logger.error("[embedder] remote embedder init failed (%s); provo fallback.", exc)

    # Path Ollama: se esplicitato OLLAMA_EMBED_MODEL, lo usiamo prioritariamente
    if OLLAMA_EMBED_MODEL:
        try:
            logger.info("[embedder] using Ollama embeddings: %s", OLLAMA_EMBED_MODEL)
            return OllamaEmbedder(OLLAMA_EMBED_MODEL)
        except Exception as exc:
            logger.warning("[embedder] Ollama embedder failed, falling back: %s", exc)

    # Path BGE-M3
    if EMBEDDER_MODEL.lower().startswith("baai/bge-m3"):
        try:
            logger.info("[embedder] loading BGE-M3 hybrid embedder")
            return BGEM3Embedder(EMBEDDER_MODEL)
        except ImportError:
            logger.warning(
                "[embedder] FlagEmbedding non installato; fallback a %s. "
                "Installa `FlagEmbedding` per hybrid retrieval.",
                LEGACY_EMBEDDER_MODEL,
            )
        except Exception as exc:
            logger.error("[embedder] BGE-M3 load fallito (%s); fallback legacy.", exc)

    # Fallback
    target = (
        EMBEDDER_MODEL if not EMBEDDER_MODEL.lower().startswith("baai/") else LEGACY_EMBEDDER_MODEL
    )
    try:
        logger.info("[embedder] loading sentence-transformers: %s", target)
        return LegacySTEmbedder(target)
    except Exception as exc:
        logger.error("[embedder] final fallback fallito: %s", exc)
        return None


def get_embedder() -> _BaseEmbedder | None:
    global _embedder
    if _embedder is not None:
        return _embedder
    with _lock:
        if _embedder is None:
            _embedder = _build_embedder()
    return _embedder


def reset_embedder() -> None:
    global _embedder
    with _lock:
        _embedder = None
    # Cache query→embedding è indicizzata su embedder.name → flush per
    # evitare risultati stale dopo uno swap (es. legacy → BGE-M3).
    try:
        from llm_wiki.vectorstore.hybrid import reset_query_embed_cache

        reset_query_embed_cache()
    except Exception:
        pass


def embedder_supports_hybrid() -> bool:
    emb = get_embedder()
    return bool(emb and emb.supports_sparse)


def dense_dim() -> int:
    emb = get_embedder()
    return emb.dense_dim if emb else 384
