"""Contextual Retrieval (Anthropic 2024) — pre-embedding augmentation.

Porta da `graphrag/vectorstore/contextual.py` con differenze:
- Usa Ollama locale (graphrag usava Claude Haiku con prompt caching).
- Modello default: `qwen2.5:7b-instruct` — italiano decente, veloce su DGX Spark.
- Stessa filosofia: il prefix è usato SOLO per embedding; lo storage tiene
  anche il testo originale + il prefix separati, così puoi re-embeddare senza
  dover richiamare l'LLM piccolo.

Impatto empirico (Anthropic): -35% miss retrieval quando combinato con hybrid
+ rerank. Costa una chiamata LLM piccolo per chunk a ingest time.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from llm_wiki.config import (
    CONTEXTUAL_CONCURRENCY,
    CONTEXTUAL_ENABLED,
    CONTEXTUAL_LLM_MODEL,
    CONTEXTUAL_MAX_TOKENS,
    OLLAMA_URL,
)

logger = logging.getLogger(__name__)


@dataclass
class ContextualChunk:
    original_text: str
    context_prefix: str
    embedded_text: str  # = prefix + '\n\n' + original


_CTX_PROMPT = """Hai di fronte un documento di una wiki su polizze assicurative italiane.
Ecco il documento completo per contesto:
<documento>
{document}
</documento>

Ecco lo specifico frammento che vogliamo situare nel documento:
<frammento>
{chunk}
</frammento>

Scrivi UNA-DUE frasi in italiano che contestualizzino il frammento nel
documento (di che sezione è? che argomento tratta?). Servono a migliorare
la ricerca semantica. NON riassumere il documento; aggiungi solo l'ancoraggio
posizionale/semantico. Rispondi solo col testo del contesto, niente altro.
"""


_client: Any = None
_client_lock = threading.Lock()
_failed = False


def _get_client() -> Any:
    """Client Ollama lazy — evita import se la feature è off."""
    global _client, _failed
    if _client is not None or _failed:
        return _client
    with _client_lock:
        if _client is not None or _failed:
            return _client
        try:
            import ollama  # type: ignore[import-not-found]

            _client = ollama.Client(host=OLLAMA_URL)
        except ImportError:
            logger.warning("[contextual] pacchetto `ollama` non installato — feature disabilitata")
            _failed = True
        except Exception as exc:
            logger.warning("[contextual] init Ollama fallita: %s", exc)
            _failed = True
    return _client


def is_enabled() -> bool:
    return CONTEXTUAL_ENABLED and _get_client() is not None


def _contextualize_one(document: str, chunk: str, client: Any) -> str:
    """Una chiamata LLM piccolo. Silenzia errori (fallback: prefix vuoto)."""
    try:
        resp = client.generate(
            model=CONTEXTUAL_LLM_MODEL,
            prompt=_CTX_PROMPT.format(document=document[:8000], chunk=chunk[:2000]),
            options={"num_predict": CONTEXTUAL_MAX_TOKENS, "temperature": 0.0},
            stream=False,
        )
        if isinstance(resp, dict):
            out = resp.get("response") or ""
        else:
            out = getattr(resp, "response", "") or ""
        return str(out).strip()
    except Exception as exc:
        logger.debug("[contextual] call fallita: %s", exc)
        return ""


def contextualize_chunks(
    document: str,
    chunks: list[str],
) -> list[ContextualChunk]:
    """Produce un prefix contestuale per ciascun chunk — parallelizzato.

    Ogni chiamata LLM è indipendente → ThreadPoolExecutor con concurrency
    `CONTEXTUAL_CONCURRENCY` (Ollama regge richieste concorrenti senza degrado
    se la VRAM basta al modello).

    Se feature disabilitata / client non disponibile, ritorna chunks intatti
    come ContextualChunk con `context_prefix=""`. Lo storage persiste sia
    `original_text` che `context_prefix` separati per poter re-embeddare.
    """
    if not chunks:
        return []
    if not CONTEXTUAL_ENABLED:
        return [ContextualChunk(c, "", c) for c in chunks]

    client = _get_client()
    if client is None:
        return [ContextualChunk(c, "", c) for c in chunks]

    def _work(chunk: str) -> ContextualChunk:
        prefix = _contextualize_one(document, chunk, client)
        if prefix:
            return ContextualChunk(chunk, prefix, f"{prefix}\n\n{chunk}")
        return ContextualChunk(chunk, "", chunk)

    # parallelismo bounded: evita di saturare Ollama con 100+ richieste
    workers = min(CONTEXTUAL_CONCURRENCY, len(chunks))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_work, chunks))
