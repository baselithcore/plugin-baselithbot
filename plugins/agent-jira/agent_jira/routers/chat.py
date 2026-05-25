from __future__ import annotations

import inspect

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from agent_jira.chat import chat_service
from agent_jira.models import ChatRequest


async def _require_chat_user(request: Request) -> str:
    from agent_jira.security import require_user

    dependency = request.app.dependency_overrides.get(require_user, require_user)
    try:
        result = dependency(request)
    except TypeError:
        result = dependency()
    if inspect.isawaitable(result):
        return await result
    return result


router = APIRouter(dependencies=[Depends(_require_chat_user)])


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Endpoint principale per interrogare il chatbot.
    Delegato al ChatService che gestisce retrieval, reranking, caching e generazione della risposta.
    """
    return await chat_service.handle_chat_async(req)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Restituisce la risposta del chatbot in streaming (chunk di testo)."""

    stream = await chat_service.handle_chat_stream_async(req)

    async def _stream_bytes():
        async for chunk in stream:
            if isinstance(chunk, bytes):
                yield chunk
            else:
                yield str(chunk).encode("utf-8")

    return StreamingResponse(
        _stream_bytes(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
