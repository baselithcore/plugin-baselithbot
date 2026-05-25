"""Memories + conversation history loaders (degraded-safe).

``load_memories`` ora delega lo storage vettoriale a
:class:`llm_wiki.memories.store.MemoriesStore` (Qdrant via
``core.services.vectorstore``). L'interfaccia resta sincrona
back-compat con i call site di ``_synth.py``: la funzione fa da bridge
fra il sync caller e l'API async del MemoriesStore senza richiedere
refactor a cascata.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from collections.abc import Awaitable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

# Soglia minima similarity per includere una memoria nel context.
# 0.4 con BGE-M3 normalizzato = match decente, evita inquinamento.
_MEMORIES_MIN_SIMILARITY = 0.4

_T = TypeVar("_T")


def _run_sync(coro: Awaitable[_T]) -> _T:
    """Esegue una coroutine da un caller sincrono.

    Casi:
    - Caller sync senza loop attivo → ``asyncio.run`` diretto.
    - Caller sync chiamato da un thread del loop (FastAPI ``def`` route in
      threadpool) → ``asyncio.run`` diretto: il thread worker NON ha un
      event loop running.
    - Caller dentro un loop already-running (``async def`` route che ci
      chiama da contesto sync) → fallback su thread isolato per evitare
      ``RuntimeError: this event loop is already running``.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)  # type: ignore[arg-type]
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()  # type: ignore[arg-type]


def load_memories(
    *, user_id: str | None, question: str, top_k: int
) -> list[dict[str, Any]]:
    """Top-K memorie utente via Qdrant. Skippa se Postgres OFF o user_id
    mancante (chat anonima legacy). Failure mode: log warn + return []
    — il RAG continua senza memorie."""
    if not user_id or top_k <= 0:
        return []
    try:
        from llm_wiki import config

        if not config.POSTGRES_ENABLED:
            return []
        from llm_wiki.memories.store import get_memories_store
        from llm_wiki.vectorstore.embedder import get_embedder

        emb = get_embedder()
        if emb is None:
            return []

        store = get_memories_store()
        return _run_sync(
            store.search(
                user_id=user_id,
                query=question,
                top_k=top_k,
                min_similarity=_MEMORIES_MIN_SIMILARITY,
                embedder=emb,
            )
        )
    except Exception as exc:
        logger.warning("[rag] memories retrieval failed (degraded): %s", exc)
        return []


def load_history(
    *, conversation_id: str | None, max_turns: int
) -> list[dict[str, Any]]:
    """Ultimi N turni dalla conversation. Skippa se Postgres OFF o
    conversation_id mancante."""
    if not conversation_id or max_turns <= 0:
        return []
    try:
        from llm_wiki import config

        if not config.POSTGRES_ENABLED:
            return []
        from llm_wiki.db.conversations import latest_turns

        return latest_turns(conversation_id=conversation_id, max_turns=max_turns)
    except Exception as exc:
        logger.warning("[rag] history load failed (degraded): %s", exc)
        return []
