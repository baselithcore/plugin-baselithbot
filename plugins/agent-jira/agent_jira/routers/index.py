from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from agent_jira.cost_control import CostController
from agent_jira.index_bootstrap import bootstrapper
from agent_jira.security import require_admin_or_job
from agent_jira.vectorstore import index_docs
from agent_jira.config import INDEX_BOOTSTRAP_ENABLED

router = APIRouter(tags=["indexing"], dependencies=[Depends(require_admin_or_job)])


@router.get("/index/status")
def index_status() -> Dict[str, object]:
    status = bootstrapper.status()
    status["bootstrap_enabled"] = INDEX_BOOTSTRAP_ENABLED
    status["state"] = "running" if status.get("running") else "idle"
    return status


@router.post("/index/bootstrap")
async def trigger_bootstrap(force_full: bool = False) -> Dict[str, object]:
    if not INDEX_BOOTSTRAP_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Bootstrapping disabilitato via configurazione.",
        )
    scheduled = await bootstrapper.schedule(force_full=force_full)
    if not scheduled:
        raise HTTPException(
            status_code=409, detail="Un processo di indicizzazione è già in corso."
        )
    return {"status": "scheduled", **bootstrapper.status()}


@router.post("/reindex")
async def reindex(force: bool = False) -> Dict[str, object]:
    """
    Esegue un'indicizzazione dei documenti locali.

    - ``force=false`` (default): indicizzazione incrementale, salta file non modificati.
    - ``force=true``: re-indicizzazione completa, rielabora tutti i file
      (utile dopo aggiornamenti al reader o al chunking).
    """
    if bootstrapper.is_running():
        raise HTTPException(
            status_code=409,
            detail="Indicizzazione non disponibile: job già in esecuzione.",
        )
    with CostController.unbounded(reason="reindex-endpoint"):
        new_files = await index_docs(incremental=not force)
    mode = "full" if force else "incremental"
    bootstrapper.register_manual_completion(mode)
    return {"status": "ok", "new_files_indexed": new_files, "mode": mode}
