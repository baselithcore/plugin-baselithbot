"""RAG chat endpoints — one-shot + NDJSON streaming.

Multi-tenancy (Fase 5)
======================

Quando Postgres è ON e l'utente è loggato:

- ``conversation_id`` opzionale nel body. Se assente, il router crea
  una conversation nuova al primo turno e restituisce l'id nella
  risposta (one-shot) o nel primo evento NDJSON (stream).
- L'agent legge automaticamente gli ultimi N turni dalla conversation
  per costruire history, e fa retrieval ibrido wiki+memorie utente.
- Append automatico: turno user (prima della call LLM) + turno
  assistant + sources (dopo la generazione completa). In streaming,
  l'append assistant avviene a fine stream.

Setup mode (no Postgres / no auth):
- Comportamento legacy stateless. ``history`` body è ancora accettato
  (passa client → server) ma non persistito. Compat con frontend
  pre-Fase 6 che ancora usa localStorage.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from llm_wiki import config
from llm_wiki.agents.agentic_rag import AgenticRAGAgent
from llm_wiki.agents.rag_agent import RAGAgent

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)
    limit: int = Field(default=8, ge=1, le=20)
    graph: bool = False
    # Agentic RAG: plan → multi-search → reflect → synthesize. Richiede
    # AGENTIC_RAG_ENABLED=true lato server; client request ignorata
    # altrimenti.
    agentic: bool = False
    # Persistenza opzionale (Fase 5). Se passato, l'agent carica history
    # dalla conversation e persiste i turni a fine call.
    conversation_id: str | None = None


# --- helpers ---------------------------------------------------------------


def _resolve_user_and_conv(
    request: Request, conversation_id: str | None
) -> tuple[dict | None, str | None]:
    """Risolve (user, conversation_id) per la richiesta.

    Auth-aware:
    - Postgres OFF / AUTH_REQUIRED=false: ritorna (None, None) — chat
      anonima legacy, no persistenza.
    - Postgres ON: user obbligatorio (require_user → 401). conversation_id
      auto-creato se mancante.

    Permission check (013): se l'utente è autenticato richiede
    ``chat.use``. Seed 008 lo concede a tutti i 4 ruoli system, quindi
    zero regressioni sui deploy esistenti; il check protegge da ruoli
    custom che ereditano sotto-insiemi di permessi (es. un "read-only"
    senza chat.use). Anonimi (chat legacy setup-mode) bypassano.
    """
    if not config.POSTGRES_ENABLED:
        return None, None

    from llm_wiki.auth.dependencies import get_current_user, require_user
    from llm_wiki.auth.permissions import has_permission
    from llm_wiki.db.conversations import create_conversation, get_conversation

    # AUTH_REQUIRED=false: chat anonima rimane disponibile anche con
    # Postgres ON; persistenza solo se utente realmente loggato.
    user = require_user(request) if config.AUTH_REQUIRED else get_current_user(request)
    if user is None:
        return None, None

    if not has_permission(user, "chat.use"):
        raise HTTPException(
            status_code=403,
            detail="Permesso richiesto: chat.use.",
        )

    if conversation_id:
        conv = get_conversation(conversation_id)
        if not conv or conv["user_id"] != user["id"]:
            # 404 anti-oracle (vedi conversations router rationale).
            raise HTTPException(status_code=404, detail="conversazione non trovata")
        return user, conversation_id

    # Auto-create al primo turno. Title placeholder; verrà rinominato
    # da update logic frontend o da auto-derive futuro.
    new_conv = create_conversation(user_id=user["id"], title="Nuova conversazione")
    return user, new_conv["id"]


def _persist_user_turn(conversation_id: str | None, message: str) -> str | None:
    if not conversation_id:
        return None
    try:
        from llm_wiki.db.conversations import append_message

        msg = append_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
        )
        return msg.get("id")
    except Exception as exc:
        logger.warning("[chat] persist user turn failed: %s", exc)
        return None


def _persist_assistant_turn(
    conversation_id: str | None,
    answer: str,
    sources: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> str | None:
    if not conversation_id:
        return None
    try:
        from llm_wiki.db.conversations import append_message

        msg = append_message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            sources=sources or None,
            metadata=metadata or {},
        )
        return msg.get("id")
    except Exception as exc:
        logger.warning("[chat] persist assistant turn failed: %s", exc)
        return None


def _build_agent(
    *,
    graph: bool,
    agentic: bool,
    user_id: str | None,
    conversation_id: str | None,
) -> RAGAgent:
    """Sceglie l'agent: AgenticRAGAgent se richiesto E abilitato lato
    server (env), altrimenti RAGAgent monolitico. Client request senza
    server flag = downgrade silenzioso (no error)."""
    from llm_wiki.config import AGENTIC_RAG_ENABLED

    if agentic and AGENTIC_RAG_ENABLED:
        return AgenticRAGAgent(
            use_graph=graph,
            user_id=user_id,
            conversation_id=conversation_id,
        )
    return RAGAgent(
        use_graph=graph,
        user_id=user_id,
        conversation_id=conversation_id,
    )


# --- endpoints -------------------------------------------------------------


@router.post("/api/chat")
def chat(req: ChatRequest, request: Request) -> dict[str, Any]:
    user, conversation_id = _resolve_user_and_conv(request, req.conversation_id)
    user_id = user["id"] if user else None

    _persist_user_turn(conversation_id, req.message)

    agent = _build_agent(
        graph=req.graph,
        agentic=req.agentic,
        user_id=user_id,
        conversation_id=conversation_id,
    )
    result = agent.answer(req.message, limit=req.limit)

    assistant_msg_id = _persist_assistant_turn(
        conversation_id,
        result.answer,
        result.sources,
        metadata={
            "hits": len(result.hits),
            "memories": len(result.memories),
            "history_used": result.history_used,
        },
    )

    return {
        "answer": result.answer,
        "sources": result.sources,
        "hits": len(result.hits),
        "memories": len(result.memories),
        "conversation_id": conversation_id,
        "message_id": assistant_msg_id,
    }


@router.post("/api/chat/stream")
def chat_stream(req: ChatRequest, request: Request) -> StreamingResponse:
    user, conversation_id = _resolve_user_and_conv(request, req.conversation_id)
    user_id = user["id"] if user else None

    _persist_user_turn(conversation_id, req.message)

    agent = _build_agent(
        graph=req.graph,
        agentic=req.agentic,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    def generator() -> Any:
        # Primo evento: comunica conversation_id al client (per attach
        # successivi al thread persistito).
        if conversation_id:
            yield json.dumps({"type": "conversation", "id": conversation_id}) + "\n"

        full_answer_parts: list[str] = []
        last_sources: list[dict[str, Any]] = []
        try:
            for event in agent.stream(req.message, limit=req.limit):
                if event.get("type") == "token":
                    full_answer_parts.append(str(event.get("content") or ""))
                elif event.get("type") == "sources":
                    last_sources = event.get("items") or []
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as exc:
            logger.exception("[api] stream error")
            yield json.dumps({"type": "error", "message": str(exc)}) + "\n"
        finally:
            # Append assistant turn a fine stream. Anche su errore parziale
            # persistiamo quello che il modello ha generato — l'utente
            # vede comunque la risposta nello scrollback.
            answer = "".join(full_answer_parts)
            if answer.strip():
                msg_id = _persist_assistant_turn(conversation_id, answer, last_sources)
                if msg_id:
                    # Trailer event con message_id per feedback FK.
                    yield json.dumps({"type": "message_id", "id": msg_id}) + "\n"
            # Terminator: il frontend (useChat.ts) ascolta `done` per
            # spegnere il pulsante Stop e marcare `streaming=false`.
            # Senza questo evento il bottone resta in "stop" anche dopo
            # che la risposta è completa.
            yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(
        generator(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
