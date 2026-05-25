import secrets
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from agent_jira.db import get_feedback_analytics
from agent_jira.security import verify_admin_password
from agent_jira.config import ADMIN_USER  # 👈 variabili da .env centralizzate

router = APIRouter(tags=["admin"])
security = HTTPBasic()

BASE_DIR = Path(__file__).resolve().parent.parent / "static"


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Verifica credenziali admin via Basic Auth.
    Username e password vengono letti dal file .env tramite config.py.
    """
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USER)
    correct_password = verify_admin_password(credentials.password)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@router.get("/admin")
def admin_page(user: str = Depends(verify_credentials)):
    """
    Restituisce la pagina Admin (protetta da Basic Auth).
    """
    return FileResponse(BASE_DIR / "admin.html")


@router.get("/admin/data")
def admin_data(
    user: str = Depends(verify_credentials),
    days: Optional[int] = Query(
        default=30,
        ge=1,
        le=365,
        description="Finestra temporale (in giorni) da considerare per gli analytics. Usa valori >0.",
    ),
    recent_limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Numero di feedback recenti da restituire.",
    ),
    top_limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Numero massimo di voci per query/documenti popolari.",
    ),
):
    """
    Restituisce i dati di analytics/feedback in formato JSON (protetto da Basic Auth).
    - Totali aggregati (positivi, negativi, percentuali)
    - Serie temporale giornaliera
    - Feedback recenti con metadati e fonti
    - Query e documenti più citati nel periodo selezionato
    """
    analytics = get_feedback_analytics(
        days=days,
        recent_limit=recent_limit,
        top_limit=top_limit,
    )
    return JSONResponse(analytics)
