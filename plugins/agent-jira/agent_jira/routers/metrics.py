from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

from agent_jira.security import require_admin

router = APIRouter(tags=["metrics"], dependencies=[Depends(require_admin)])


@router.get("/metrics")
def prometheus_metrics() -> Response:
    """Esporta le metriche Prometheus registrate nel processo."""

    payload = generate_latest(REGISTRY)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
