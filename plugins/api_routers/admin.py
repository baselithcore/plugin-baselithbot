"""
Admin Router.

Provides secure endpoints for administrative tasks, including analytics
dashboards and system monitoring. Protected by HTTP Basic Authentication.
"""

from dataclasses import asdict
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pathlib import Path
import secrets

from core.services.feedback_service import get_feedback_service
from core.middleware import (
    verify_admin_password,
    check_admin_lockout,
    record_admin_failure,
    clear_admin_failures,
)
from core.config import get_security_config
from core.task_queue.dead_letter import (
    DeadLetterError,
    DeadLetterRecord,
    get_dead_letter_queue,
)

router = APIRouter(tags=["admin"])
security = HTTPBasic()

BASE_DIR = Path(__file__).resolve().parent.parent / "static"


def _get_admin_user() -> str:
    """Read the admin username lazily from the active security config."""
    return get_security_config().admin_user


async def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Verifica credenziali admin via Basic Auth.
    Username and password are read from the .env file via config.py.
    Enforces account lockout after repeated failures.
    """
    await check_admin_lockout(credentials.username)

    correct_username = secrets.compare_digest(credentials.username, _get_admin_user())
    correct_password = verify_admin_password(credentials.password)

    if not (correct_username and correct_password):
        await record_admin_failure(credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide",
            headers={"WWW-Authenticate": "Basic"},
        )

    await clear_admin_failures(credentials.username)
    return credentials.username


@router.get("/admin")
def admin_page(_user: str = Depends(verify_credentials)):
    """
    Restituisce la pagina Admin (protetta da Basic Auth).
    """
    return FileResponse(BASE_DIR / "admin.html")


@router.get("/admin/data")
async def admin_data(
    _user: str = Depends(verify_credentials),
    days: Optional[int] = Query(
        default=30,
        ge=1,
        le=365,
        description="Time window (in days) to consider for analytics. Use values >0.",
    ),
    recent_limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of recent feedbacks to return.",
    ),
    top_limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of entries for popular queries/documents.",
    ),
):
    """
    Returns analytics/feedback data in JSON format (protected by Basic Auth).
    - Aggregated totals (positive, negative, percentages)
    - Daily time series
    - Recent feedback with metadata and sources
    - Most cited queries and documents in the selected period
    """
    feedback_service = get_feedback_service()
    analytics = await feedback_service.get_analytics(
        days=days,
        recent_limit=recent_limit,
        top_limit=top_limit,
    )
    return JSONResponse(analytics)


# --------------------------------------------------------------------------- #
# Dead-letter queue (DLQ) administration                                      #
#                                                                             #
# Inspect, replay, and purge terminally-failed background jobs. All routes    #
# are behind the same Basic-Auth guard as the rest of the admin surface.      #
# --------------------------------------------------------------------------- #


def _dlq_summary(record: DeadLetterRecord) -> dict:
    """Compact view for the list endpoint — omits the heavy traceback/payload."""
    data = asdict(record)
    data.pop("traceback", None)
    data.pop("payload_b64", None)
    return data


@router.get("/admin/dlq")
def dlq_list(
    _user: str = Depends(verify_credentials),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List dead-lettered jobs (summary view) with the total count."""
    dlq = get_dead_letter_queue()
    items = [_dlq_summary(r) for r in dlq.list(limit=limit, offset=offset)]
    return {"total": dlq.count(), "items": items, "limit": limit, "offset": offset}


@router.get("/admin/dlq/{job_id}")
def dlq_detail(job_id: str, _user: str = Depends(verify_credentials)):
    """Return the full dead-letter record (including traceback); 404 if absent."""
    record = get_dead_letter_queue().get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Dead-letter record not found.")
    return asdict(record)


@router.post("/admin/dlq/{job_id}/replay")
def dlq_replay(job_id: str, _user: str = Depends(verify_credentials)):
    """Re-enqueue a dead-lettered job; 409 if it cannot be replayed."""
    try:
        new_id = get_dead_letter_queue().replay(job_id)
    except DeadLetterError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"job_id": new_id}


@router.delete("/admin/dlq")
def dlq_purge_all(_user: str = Depends(verify_credentials)):
    """Purge every dead-letter record; returns how many were removed."""
    removed = get_dead_letter_queue().purge_all()
    return {"removed": removed}


@router.delete("/admin/dlq/{job_id}")
def dlq_purge(job_id: str, _user: str = Depends(verify_credentials)):
    """Purge a single dead-letter record; 404 if it does not exist."""
    if not get_dead_letter_queue().purge(job_id):
        raise HTTPException(status_code=404, detail="Dead-letter record not found.")
    return {"status": "purged", "job_id": job_id}
