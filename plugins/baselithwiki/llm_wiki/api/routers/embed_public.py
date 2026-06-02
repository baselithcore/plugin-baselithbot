"""Public embed chat endpoints — token-authenticated, no JWT.

Surface
-------

``GET  /api/embed/config``           — branding + welcome + suggestions per il widget
``POST /api/embed/chat``             — one-shot RAG, stateless
``POST /api/embed/chat/stream``      — NDJSON streaming, stateless

Auth model
----------

Token plaintext nel body (``embed_token``). Lookup via
:func:`llm_wiki.db.embeds.verify_token` — match ``token_hash`` +
``Origin`` ∈ ``origin_allowlist``. Senza Origin valido → 401.

Tenant context viene impostato manualmente dopo la verifica via
:func:`auth.tenant_context.set_current_tenant` — necessario perché
``TenantMiddleware`` ignora ``/api/embed/*`` (no JWT da decodificare).

Persistenza
-----------

Stateless: nessuna conversation persistita lato server (frontend tiene
``conversation_id`` localStorage e passa ``history`` in ogni request).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from llm_wiki import config
from llm_wiki.agents.rag_agent import RAGAgent
from llm_wiki.auth.rate_limit import RateLimitExceeded, rate_limiter
from llm_wiki.auth.tenant_context import TenantInfo, reset_tenant, set_current_tenant
from llm_wiki.db import embeds as embeds_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/embed", tags=["embed"])


# --- models ---------------------------------------------------------------


class _EmbedChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str
    content: str


class _EmbedBaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    embed_token: str = Field(min_length=10, max_length=200)


class EmbedConfigRequest(_EmbedBaseRequest):
    pass


class EmbedChatRequest(_EmbedBaseRequest):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[_EmbedChatMessage] = Field(default_factory=list, max_length=40)
    limit: int = Field(default=6, ge=1, le=12)


# --- helpers --------------------------------------------------------------


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "-"


def _request_origin(request: Request) -> str | None:
    """Origin del browser. ``Origin`` è obbligatorio per le cross-origin
    POST cors-protetti; ``Referer`` come fallback non lo accettiamo perché
    falsificabile e non disambigua sub-path/sub-resource."""
    origin = request.headers.get("origin")
    return origin.strip() if origin else None


def _resolve_embed(request: Request, token: str) -> dict[str, Any]:
    """Verifica token + origin + rate-limit. Solleva HTTPException su fail."""
    if not config.POSTGRES_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embed disponibile solo con storage attivo (Postgres).",
        )
    origin = _request_origin(request)
    embed = embeds_db.verify_token(token, origin=origin)
    if embed is None:
        # 401 generico — non distinguiamo "token invalido" da "origin
        # non in allowlist" per non leak info utili a un attaccante.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token embed non valido o origin non autorizzato.",
        )

    limit = int(embed.get("rate_limit_per_minute") or 0)
    if limit > 0:
        identifier = f"embed:{embed['id']}:ip:{_client_ip(request)}"
        try:
            rate_limiter.check(identifier, limit, config.RATE_LIMIT_WINDOW_SECONDS)
        except RateLimitExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit superato, riprova tra pochi secondi.",
            ) from exc

    return embed


def _build_agent_for_embed() -> RAGAgent:
    """Embed = chat anonima stateless. Niente user_id / conversation_id;
    history arriva dal client in ogni request (gestita lato widget)."""
    return RAGAgent(
        use_graph=False,
        user_id=None,
        conversation_id=None,
    )


# --- endpoints ------------------------------------------------------------


@router.post("/config")
def embed_config(req: EmbedConfigRequest, request: Request) -> dict[str, Any]:
    """Config che il widget legge al boot. POST (non GET) perché il token
    viaggia in body — meno chance di finire in log/referrer/storage."""
    embed = _resolve_embed(request, req.embed_token)
    # last_used best-effort.
    embeds_db.touch_last_used(embed["id"])

    # Branding del pack attivo lato server come fallback se theme è
    # parziale. Il widget mini-app farà merge: theme[key] ?? pack.ui[key].
    pack_branding: dict[str, Any] = {}
    try:
        from llm_wiki.domain.registry import load_pack

        pack = load_pack()
        pack_branding = {
            "label": pack.label,
            "language": pack.language,
            "ui": pack.ui.model_dump(),
        }
    except Exception as exc:
        logger.debug("[embed] pack branding fallback: %s", exc)

    return {
        "embed_id": embed["id"],
        "name": embed["name"],
        "theme": embed["theme"],
        "welcome_message": embed["welcome_message"],
        "suggested_questions": embed["suggested_questions"],
        "pack": pack_branding,
        "rate_limit_per_minute": embed["rate_limit_per_minute"],
    }


@router.post("/chat")
def embed_chat(req: EmbedChatRequest, request: Request) -> dict[str, Any]:
    embed = _resolve_embed(request, req.embed_token)
    tenant_token = set_current_tenant(TenantInfo(tenant_id=embed["tenant_id"]))
    try:
        agent = _build_agent_for_embed()
        result = agent.answer(req.message, limit=req.limit)
        return {
            "answer": result.answer,
            "sources": result.sources,
            "hits": len(result.hits),
            "memories": 0,
        }
    finally:
        reset_tenant(tenant_token)


@router.post("/chat/stream")
def embed_chat_stream(req: EmbedChatRequest, request: Request) -> StreamingResponse:
    embed = _resolve_embed(request, req.embed_token)

    def generator() -> Any:
        tenant_token = set_current_tenant(TenantInfo(tenant_id=embed["tenant_id"]))
        try:
            agent = _build_agent_for_embed()
            try:
                for event in agent.stream(req.message, limit=req.limit):
                    yield json.dumps(event, ensure_ascii=False) + "\n"
            except Exception as exc:
                logger.exception("[embed] stream error")
                yield json.dumps({"type": "error", "message": str(exc)}) + "\n"
            finally:
                yield json.dumps({"type": "done"}) + "\n"
        finally:
            reset_tenant(tenant_token)

    return StreamingResponse(
        generator(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = ["router"]
