from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import ValidationError

from agent_jira.db import get_feedbacks, insert_feedback
from agent_jira.metrics import FEEDBACK_RECEIVED_TOTAL
from agent_jira.models import FeedbackDocumentReference, FeedbackRequest
from agent_jira.security import require_admin, require_user
from agent_jira.telemetry import telemetry

router = APIRouter(prefix="", tags=["feedback"])


def _normalize_sources_payload(raw_sources: Any) -> Optional[List[Dict[str, Any]]]:
    if not raw_sources:
        return None

    normalized: List[Dict[str, Any]] = []

    if isinstance(raw_sources, list):
        items = raw_sources
    else:
        items = [raw_sources]

    for source in items:
        if isinstance(source, FeedbackDocumentReference):
            normalized.append(source.dict(exclude_none=True))
            continue

        if isinstance(source, dict):
            cleaned = {
                str(key): value for key, value in source.items() if value is not None
            }
            if cleaned:
                normalized.append(cleaned)

    return normalized or None


@router.post("/feedback")
def feedback(
    payload: Dict[str, Any] = Body(...),
    _role: str = Depends(require_user),
) -> Dict[str, object]:
    """
    Registra un feedback (positive|negative) per una risposta generata.
    - I dati vengono salvati nel database PostgreSQL (configurabile tramite le variabili d'ambiente dedicate).
    """
    try:
        req = FeedbackRequest(**payload)
        sources_payload = _normalize_sources_payload(req.sources)
        conversation_id = req.conversation_id
        query = req.query
        answer = req.answer
        feedback_value = req.feedback
        comment = req.comment.strip() if isinstance(req.comment, str) else None
    except ValidationError as exc:
        # fallback per payload legacy/non conforme
        query = str(payload.get("query") or "").strip()
        answer = str(payload.get("answer") or "").strip()
        feedback_value = str(payload.get("feedback") or "").strip().lower()
        if feedback_value not in {"positive", "negative"}:
            raise HTTPException(
                status_code=422,
                detail={"message": "Invalid feedback payload", "errors": exc.errors()},
            )
        conversation_id = payload.get("conversation_id")
        sources_payload = _normalize_sources_payload(payload.get("sources"))
        raw_comment = payload.get("comment")
        comment = raw_comment.strip() if isinstance(raw_comment, str) else None

    insert_feedback(
        query,
        answer,
        feedback_value,
        conversation_id=conversation_id,
        sources=sources_payload,
        comment=comment,
    )
    telemetry.increment(f"feedback.{feedback_value}")
    FEEDBACK_RECEIVED_TOTAL.labels(sentiment=feedback_value).inc()
    sanitized_payload = {
        "query": query,
        "answer": answer,
        "feedback": feedback_value,
        "conversation_id": conversation_id,
        "sources": sources_payload,
    }
    if comment:
        sanitized_payload["comment"] = comment
    return {"status": "ok", "received": sanitized_payload}


@router.get("/feedbacks")
def list_feedbacks(
    feedback: Optional[Literal["positive", "negative"]] = Query(
        default=None,
        description="Filtra i risultati per tipo di feedback: 'positive' o 'negative'",
    ),
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=200,
        description="Limita il numero di record restituiti (max 200)",
    ),
    _role: str = Depends(require_admin),
) -> List[Dict[str, object]]:
    """
    Restituisce tutti i feedback salvati.
    - Se `feedback` è specificato, filtra per tipo ('positive' o 'negative').
    """
    return get_feedbacks(feedback, limit=limit)
