"""AI endpoints — chat with your notes + inline transforms.

Chat streams NDJSON (one JSON object per line: token events, then a sources
event) so the SPA can render tokens live and citations at the end. Transforms
return a single typed JSON result.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..ai_service import AIService
from ..chat_models import ChatRequest, ConversationCreate
from ..index_state import get_index
from ..memory import derive_title
from ..research_service import ResearchService

router = APIRouter(prefix="/api/ai", tags=["ai"])


class TransformRequest(BaseModel):
    action: str = Field(description="summarize|expand|improve|autotag|suggest_links")
    text: str
    title: str = ""


class ResearchRequest(BaseModel):
    question: str


@router.get("/status")
async def ai_status() -> dict[str, object]:
    return AIService(get_index()).status()


@router.post("/chat")
async def ai_chat(req: ChatRequest) -> StreamingResponse:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="empty question")

    idx = get_index()
    conv = idx.conversations.get(req.conversation_id) if req.conversation_id else None
    if conv is None:
        # First turn: open a thread titled from the opening question.
        conv = idx.conversations.create(
            ConversationCreate(title=derive_title(question), workspace=req.workspace)
        )

    return StreamingResponse(
        AIService(idx).chat_stream(conv, question),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            # The host mounts this under /baselithbrain, so its SmartGzipMiddleware
            # exclusion (/chat/stream) never matches us and would gzip-buffer the
            # stream — killing the typewriter effect. Declaring an explicit
            # Content-Encoding makes Starlette's GZip responder skip compression,
            # so tokens flush to the client as they arrive.
            "Content-Encoding": "identity",
        },
    )


@router.post("/research")
async def ai_research(req: ResearchRequest) -> dict[str, object]:
    """Run bounded multi-hop ReAct research over the vault; return a cited report."""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="empty question")
    try:
        return await ResearchService(get_index()).research(question)
    except Exception as exc:  # noqa: BLE001 — surface a clean 503 to the UI
        raise HTTPException(
            status_code=503, detail=f"Research unavailable: {exc}"
        ) from exc


@router.post("/transform")
async def ai_transform(req: TransformRequest) -> dict[str, object]:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="empty text")
    try:
        return await AIService(get_index()).transform(req.action, req.text, req.title)
    except Exception as exc:  # noqa: BLE001 — surface a clean 503 to the UI
        raise HTTPException(status_code=503, detail=f"AI unavailable: {exc}") from exc
