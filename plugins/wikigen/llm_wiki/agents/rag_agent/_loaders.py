"""Memories + conversation history loaders (degraded-safe)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Soglia minima similarity per includere una memoria nel context.
# 0.4 con BGE-M3 normalizzato = match decente, evita inquinamento.
_MEMORIES_MIN_SIMILARITY = 0.4


def load_memories(*, user_id: str | None, question: str, top_k: int) -> list[dict[str, Any]]:
    """Top-K memorie utente via pgvector. Skippa se Postgres OFF o
    user_id mancante (chat anonima legacy)."""
    if not user_id or top_k <= 0:
        return []
    try:
        from llm_wiki import config

        if not config.POSTGRES_ENABLED:
            return []
        from llm_wiki.db.memories import search_similar
        from llm_wiki.vectorstore.embedder import get_embedder

        emb = get_embedder()
        if emb is None:
            return []
        out = emb.encode([question], is_query=True)
        if not out.dense or not out.dense[0]:
            return []
        return search_similar(
            user_id=user_id,
            query_embedding=out.dense[0],
            top_k=top_k,
            min_similarity=_MEMORIES_MIN_SIMILARITY,
        )
    except Exception as exc:
        logger.warning("[rag] memories retrieval failed (degraded): %s", exc)
        return []


def load_history(*, conversation_id: str | None, max_turns: int) -> list[dict[str, Any]]:
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
