"""Feedback router: persiste su Postgres (per-tenant) con fallback JSONL.

Strategy
========

- Postgres OK + tenant context valido → write su tabella ``feedback``
  (RLS-isolato, query-friendly, FK ``message_id``).
- Postgres OFF → fallback JSONL (legacy ``.feedback.jsonl``).

Backwards compat: il client non deve sapere quale storage. Schema
request invariato — se il `message_id` viene passato tentiamo la FK,
altrimenti resta NULL.

Auth
====

``require_user`` se Postgres on (feedback è per-utente). In setup mode
(no DB) cade su scrittura JSONL anonima.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from llm_wiki import config

logger = logging.getLogger(__name__)

router = APIRouter()


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str | None = Field(default=None, description="Assistant message UUID")
    rating: str = Field(..., pattern="^(up|down)$")
    reason: str | None = None
    question: str | None = None
    answer: str | None = None
    sources: list[dict[str, Any]] | None = None
    edition: str | None = None
    at: int | None = None


_FEEDBACK_LOG = Path(config.FEEDBACK_LOG_PATH)


def _persist_jsonl(req: FeedbackRequest) -> None:
    """Fallback legacy. Append-only JSONL, una entry per riga."""
    entry = {"t": int(time.time() * 1000), **req.model_dump(exclude_none=True)}
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    _FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _FEEDBACK_LOG.open("a", encoding="utf-8") as f:
        f.write(line)


def _maybe_user_dependency():
    """Inject ``require_user`` solo se Postgres on. In setup mode il
    feedback resta anonimo (JSONL) — il dep non si può applicare a
    runtime, quindi lo wrap-piamo lazily."""
    if not config.POSTGRES_ENABLED:
        return None
    from llm_wiki.auth.dependencies import require_user

    return require_user


_USER_DEP = _maybe_user_dependency()


@router.post("/api/feedback")
async def api_feedback(
    req: FeedbackRequest,
    request: Request,
) -> dict[str, Any]:
    if not config.FEEDBACK_ENABLED:
        raise HTTPException(status_code=404, detail="feedback disabled")

    # Path Postgres: persisti in DB con tenant scope.
    if config.POSTGRES_ENABLED:
        # Resolve user manualmente (Depends non si può iniettare conditionally).
        from llm_wiki.auth.dependencies import require_user
        from llm_wiki.auth.permissions import has_permission
        from llm_wiki.db.feedback import write_feedback

        user = require_user(request)
        # Granular check (PR audit MED #4): permesso ``feedback.write``
        # seedato a tutti i 4 ruoli system → zero regressioni. Protegge
        # custom role senza il perm dalla submission.
        if not has_permission(user, "feedback.write"):
            raise HTTPException(
                status_code=403,
                detail="Permesso richiesto: feedback.write.",
            )
        try:
            row = write_feedback(
                user_id=user["id"],
                rating=req.rating,
                message_id=req.message_id,
                reason=req.reason,
                question=req.question,
                answer=req.answer,
                sources=req.sources,
            )
            return {"status": "ok", "id": row.get("id")}
        except Exception:
            logger.exception("[feedback] DB write failed, falling back to JSONL")
            # Best-effort fallback per non perdere il segnale utente.
            try:
                _persist_jsonl(req)
            except OSError as ose:
                raise HTTPException(
                    status_code=500, detail="unable to persist feedback"
                ) from ose
            return {"status": "degraded", "fallback": "jsonl"}

    # Path JSONL (setup mode / Postgres off).
    try:
        _persist_jsonl(req)
    except OSError as exc:
        logger.warning("[feedback] persist failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="unable to persist feedback"
        ) from exc
    return {"status": "ok"}


@router.get("/api/feedback")
def list_my_feedback(
    rating: str | None = None,
    limit: int = 200,
    user: dict[str, Any] = Depends(_USER_DEP) if _USER_DEP else Depends(lambda: None),
) -> dict:
    """Lista feedback dell'utente corrente. Solo Postgres path."""
    if not config.POSTGRES_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="DB non disponibile — listing feedback richiede Postgres",
        )
    from llm_wiki.db.feedback import list_feedback

    items = list_feedback(user_id=user["id"], rating=rating, limit=limit)
    return {"count": len(items), "feedback": items}
