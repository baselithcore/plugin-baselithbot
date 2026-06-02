"""Runtime control endpoints for the admin router.

Currently only ``POST /api/admin/restart`` lives here. Kept separate so
the upload/scaffold routers don't drag in ``signal``/``threading``.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from llm_wiki.admin.scaffold import (
    ProviderSettings,
    ScaffoldError,
    _upsert_env_kv,
    mutate_env_file,
    repo_root,
)
from llm_wiki.api.admin_perms import require_admin_perm

logger = logging.getLogger(__name__)

router = APIRouter()


def _running_under_reloader() -> bool:
    """Heuristic: gira sotto ``uvicorn --reload``?

    Senza una env-var canonica esposta da uvicorn, controlliamo:
    1. ``--reload`` in argv del parent process (best effort, no psutil dep)
    2. presenza modulo ``watchfiles`` importato (uvicorn lo usa per file watch)
    3. ``RUN_MAIN`` di tipico Django/uvicorn worker-detect

    Falsi negativi (skip detect) → SIGTERM ucciderà reloader. Conservativo:
    consideriamo reload-mode anche con un solo segnale positivo.
    """
    if os.getenv("RUN_MAIN") == "true":
        return True
    if os.getenv("UVICORN_RELOAD_PROC"):
        return True
    # Marker scritto da `wiki-wl serve --reload` prima di uvicorn.run.
    # Inheritato dal worker child quando uvicorn lo respawna.
    if os.getenv("LLMWIKI_RUN_RELOAD"):
        return True
    # `watchfiles` importato → uvicorn --reload attivo (pacchetto richiesto
    # solo in reload mode).
    import sys as _sys

    if (
        "watchfiles" in _sys.modules
        or "uvicorn.supervisors.watchfilesreload" in _sys.modules
    ):
        return True
    # Ultimo fallback: ispeziona la cmdline del parent process. Cattura
    # `uvicorn main:app --reload` lanciato senza il nostro wrapper.
    try:
        import subprocess as _sp

        ppid = os.getppid()
        out = _sp.run(
            ["ps", "-o", "args=", "-p", str(ppid)],
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
        )
        if "--reload" in out.stdout:
            return True
    except Exception:  # pragma: no cover — best-effort heuristic
        pass
    return False


class RestartResponse(BaseModel):
    """Response for ``POST /api/admin/restart``."""

    scheduled: bool
    pid: int
    delay_ms: int
    note: str
    requires_manual: bool = False
    mode: str = "unknown"


@router.post(
    "/restart",
    response_model=RestartResponse,
    dependencies=[Depends(require_admin_perm("admin.runtime"))],
)
def restart_process(delay_ms: int = 500) -> RestartResponse:
    """Schedule a graceful self-restart compatible with both supervised
    and unsupervised deployments.

    Strategy
    --------
    1. **Touch** key Python files watched by ``uvicorn --reload``. This
       is the path that actually works for the dev workflow: StatReload
       sees the mtime change, kills the worker and respawns it cleanly
       — preserving the supervisor process. SIGTERM alone would just
       exit the worker AND the reloader (no respawn).
    2. **Fallback SIGTERM** scheduled `delay_ms + 2000ms` later. If the
       process is run under a non-uvicorn supervisor (systemd, docker
       restart policy, supervisord) the touch is a no-op and the kill
       triggers the supervisor's restart contract.
    3. Bare ``python main.py`` without reload exits and stays exited —
       the operator must relaunch by hand. We surface that case in the
       ``note`` field so the frontend can warn the user.

    ``delay_ms`` is clamped to [100, 5000] so the HTTP response flushes
    before any restart action fires.
    """
    delay_ms = max(100, min(delay_ms, 5000))
    pid = os.getpid()
    touched: list[str] = []

    rr = repo_root()
    candidates = [
        rr / "main.py",
        rr / "llm_wiki" / "__init__.py",
    ]

    def _touch() -> None:
        now = time.time()
        for c in candidates:
            try:
                if c.exists():
                    os.utime(c, (now, now))
                    touched.append(str(c.relative_to(rr)))
            except OSError as exc:
                logger.warning("[admin] touch %s failed: %s", c, exc)

    def _kick() -> None:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as exc:
            logger.error("[admin] restart kill failed: %s", exc)

    # touch runs first: uvicorn --reload picks up mtime change e respawna
    # solo il worker (preserva il reloader supervisor).
    threading.Timer(delay_ms / 1000.0, _touch).start()

    # SIGTERM fallback solo se NON siamo sotto uvicorn --reload. Detect:
    # `WATCHFILES_FORCE_POLLING`/`UVICORN_RELOADER_PID` non sempre settati;
    # heuristic: se il modulo `uvicorn.supervisors` ha già un reloader vivo,
    # skippiamo SIGTERM (lo killerebbe). Diamo un'opportunità al touch.
    # In supervisori esterni (systemd, docker), nessuna reload-machinery
    # → SIGTERM è l'unico modo di restartare.
    in_reload = bool(os.getenv("UVICORN_RELOAD_PROC")) or _running_under_reloader()
    has_supervisor = bool(
        os.getenv("INVOCATION_ID")  # systemd
        or os.getenv("SUPERVISOR_ENABLED")  # supervisord
        or os.getenv("KUBERNETES_SERVICE_HOST")  # k8s
        or os.getenv("DOCKER_CONTAINER")  # docker (best effort)
    )
    if in_reload:
        threading.Timer(delay_ms / 1000.0, _touch).start()
        logger.warning(
            "[admin] restart scheduled (touch only, --reload detected) in %dms (pid=%s)",
            delay_ms,
            pid,
        )
        mode = "reload"
        requires_manual = False
        note = "uvicorn --reload detected: touching watched files to trigger respawn."
    elif has_supervisor:
        threading.Timer(delay_ms / 1000.0, _touch).start()
        threading.Timer((delay_ms + 2000) / 1000.0, _kick).start()
        logger.warning(
            "[admin] restart scheduled (touch + SIGTERM, supervisor detected) in %dms (pid=%s)",
            delay_ms,
            pid,
        )
        mode = "supervised"
        requires_manual = False
        note = "Supervisor detected (systemd/supervisord/k8s/docker): SIGTERM scheduled, supervisor will respawn."
    else:
        # Bare process: SIGTERM would kill the server with no respawn.
        # Refuse and signal the caller to surface a manual-restart prompt
        # immediately instead of letting the wizard time out.
        logger.warning(
            "[admin] restart NOT scheduled (no reloader, no supervisor) — pid=%s, manual restart required",
            pid,
        )
        mode = "bare"
        requires_manual = True
        note = (
            "Server running without --reload and no supervisor detected. "
            "Automatic restart would kill the process. Run the displayed command manually."
        )
    return RestartResponse(
        scheduled=not requires_manual,
        pid=pid,
        delay_ms=delay_ms,
        note=note,
        requires_manual=requires_manual,
        mode=mode,
    )


class ActivateNowResponse(BaseModel):
    """Response for ``POST /api/admin/activate-now``."""

    ok: bool
    pack: str | None
    setup_mode: bool
    jobs_started: int
    note: str


@router.post(
    "/activate-now",
    response_model=ActivateNowResponse,
    dependencies=[Depends(require_admin_perm("admin.runtime"))],
)
async def activate_now() -> ActivateNowResponse:
    """In-process soft activation for bare-mode deployments.

    Scaffold mutates ``os.environ`` and resets the pack cache, but the
    one-shot lifespan hooks (qdrant collection bootstrap, embedder
    warmup, ``autostart_pending_ingest``) only run at process boot. In
    bare mode (``python -m llm_wiki serve`` without ``--reload`` and no
    supervisor) we cannot restart the process — SIGTERM would kill the
    server with no respawn. This endpoint replays the lifespan side
    effects in-process so the wizard can finish without forcing the
    user back to a terminal.

    Idempotent: safe to call multiple times.
    """
    import asyncio as _asyncio

    from llm_wiki import config
    from llm_wiki.api.routers.ingest import autostart_pending_ingest
    from llm_wiki.domain.registry import load_pack
    from llm_wiki.ingest_raw.jobs import get_registry as _get_job_registry
    from llm_wiki.vectorstore.embedder import get_embedder
    from llm_wiki.vectorstore.qdrant_ops import create_collection

    # Defensive: scaffold also calls refresh_paths(), but this endpoint
    # may run from any caller — re-sync module constants to the current
    # env so RAW_DIR / WIKI_DIR point at the tenant's vault.
    try:
        config.refresh_paths()
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("[admin.activate-now] config.refresh_paths failed: %s", exc)

    if not config.APP_DOMAIN:
        return ActivateNowResponse(
            ok=False,
            pack=None,
            setup_mode=True,
            jobs_started=0,
            note="APP_DOMAIN unset: scaffold did not activate any pack.",
        )

    try:
        pack = load_pack()
    except Exception as exc:
        logger.error("[admin.activate-now] load_pack failed: %s", exc)
        return ActivateNowResponse(
            ok=False,
            pack=None,
            setup_mode=True,
            jobs_started=0,
            note=f"pack load failed: {exc}",
        )

    try:
        await _asyncio.to_thread(get_embedder)
        await _asyncio.to_thread(create_collection)
    except Exception as exc:
        logger.warning("[admin.activate-now] warmup partial: %s", exc)

    try:
        _get_job_registry().set_loop(_asyncio.get_running_loop())
    except Exception as exc:
        logger.debug("[admin.activate-now] registry loop set skipped: %s", exc)

    jobs_before = 0
    try:
        jobs_before = len(_get_job_registry().list_jobs(limit=10_000))
    except Exception:
        pass

    if getattr(config, "AUTO_INGEST_ON_STARTUP", True):
        try:
            await autostart_pending_ingest()
        except Exception as exc:
            logger.warning("[admin.activate-now] autostart ingest failed: %s", exc)

    jobs_after = jobs_before
    try:
        jobs_after = len(_get_job_registry().list_jobs(limit=10_000))
    except Exception:
        pass

    return ActivateNowResponse(
        ok=True,
        pack=pack.name,
        setup_mode=False,
        jobs_started=max(0, jobs_after - jobs_before),
        note="In-process activation done (no restart).",
    )


class ProviderUpdateResponse(BaseModel):
    """Response for ``POST /api/admin/provider``."""

    ok: bool
    vendor: str | None
    rag_vendor: str | None
    ingest_vendor: str | None
    model: str | None
    ingest_model: str | None
    base_url: str | None
    env_written: bool
    note: str = ""


@router.post(
    "/provider",
    response_model=ProviderUpdateResponse,
    dependencies=[Depends(require_admin_perm("admin.tenant.manage"))],
)
def update_provider(req: ProviderSettings) -> ProviderUpdateResponse:
    """Rotate LLM provider config without re-scaffolding the pack.

    Accepts either single-vendor mode (``vendor`` set → both chat and
    ingest use it) or split mode (``rag_vendor`` + ``ingest_vendor``
    set independently → chat and ingest dispatch to different
    providers). ``vendor`` still wins for the fallback ``LLM_VENDOR``
    when split mode is requested.

    Mutates ``.env`` (upsert-in-place, preserves unrelated lines), mirrors
    the new values into the running process via ``os.environ``, refreshes
    the module-level constants in :mod:`llm_wiki.config`, and drops the
    cached LLM clients so the next inference call rebuilds against the
    new vendor/key/url combo. Idempotent.
    """
    import os as _os

    if not (req.vendor or req.rag_vendor or req.ingest_vendor):
        raise HTTPException(
            400, "at least one of vendor / rag_vendor / ingest_vendor required"
        )

    eff_rag = req.rag_vendor or req.vendor
    eff_ingest = req.ingest_vendor or req.vendor

    rr = repo_root()
    env_path = rr / ".env"
    template = rr / ".env.example"

    def _mutate(base: str) -> str:
        if req.vendor:
            base = _upsert_env_kv(base, "LLM_VENDOR", req.vendor)
        if req.rag_vendor:
            base = _upsert_env_kv(base, "RAG_VENDOR", req.rag_vendor)
        if req.ingest_vendor:
            base = _upsert_env_kv(base, "INGEST_VENDOR", req.ingest_vendor)
        if eff_rag == "ollama" and req.model:
            base = _upsert_env_kv(base, "OLLAMA_MODEL", req.model)
        elif eff_rag == "openai" and req.model:
            base = _upsert_env_kv(base, "OPENAI_MODEL", req.model)
        if eff_ingest == "ollama" and req.ingest_model:
            base = _upsert_env_kv(base, "INGEST_OLLAMA_MODEL", req.ingest_model)
        elif eff_ingest == "openai" and req.ingest_model:
            base = _upsert_env_kv(base, "INGEST_OPENAI_MODEL", req.ingest_model)
        if req.ollama_url:
            base = _upsert_env_kv(base, "OLLAMA_URL", req.ollama_url)
        if req.openai_api_base:
            base = _upsert_env_kv(base, "OPENAI_API_BASE", req.openai_api_base)
        if req.openai_api_key:
            base = _upsert_env_kv(base, "OPENAI_API_KEY", req.openai_api_key)
        if req.base_url and not req.ollama_url and not req.openai_api_base:
            if "ollama" in {eff_rag, eff_ingest}:
                base = _upsert_env_kv(base, "OLLAMA_URL", req.base_url)
            if "openai" in {eff_rag, eff_ingest}:
                base = _upsert_env_kv(base, "OPENAI_API_BASE", req.base_url)
        if req.api_key and not req.openai_api_key and "openai" in {eff_rag, eff_ingest}:
            base = _upsert_env_kv(base, "OPENAI_API_KEY", req.api_key)
        return base

    try:
        written = mutate_env_file(env_path, _mutate, template=template)
    except ScaffoldError as exc:
        raise HTTPException(400, str(exc)) from exc

    if req.vendor:
        _os.environ["LLM_VENDOR"] = req.vendor
    if req.rag_vendor:
        _os.environ["RAG_VENDOR"] = req.rag_vendor
    if req.ingest_vendor:
        _os.environ["INGEST_VENDOR"] = req.ingest_vendor
    if eff_rag == "ollama" and req.model:
        _os.environ["OLLAMA_MODEL"] = req.model
    elif eff_rag == "openai" and req.model:
        _os.environ["OPENAI_MODEL"] = req.model
    if eff_ingest == "ollama" and req.ingest_model:
        _os.environ["INGEST_OLLAMA_MODEL"] = req.ingest_model
    elif eff_ingest == "openai" and req.ingest_model:
        _os.environ["INGEST_OPENAI_MODEL"] = req.ingest_model
    if req.ollama_url:
        _os.environ["OLLAMA_URL"] = req.ollama_url
    if req.openai_api_base:
        _os.environ["OPENAI_API_BASE"] = req.openai_api_base
    if req.openai_api_key:
        _os.environ["OPENAI_API_KEY"] = req.openai_api_key
    if req.base_url and not req.ollama_url and not req.openai_api_base:
        if "ollama" in {eff_rag, eff_ingest}:
            _os.environ["OLLAMA_URL"] = req.base_url
        if "openai" in {eff_rag, eff_ingest}:
            _os.environ["OPENAI_API_BASE"] = req.base_url
    if req.api_key and not req.openai_api_key and "openai" in {eff_rag, eff_ingest}:
        _os.environ["OPENAI_API_KEY"] = req.api_key

    try:
        from llm_wiki import config as _cfg

        _cfg.refresh_paths()
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("[admin.provider] config.refresh_paths failed: %s", exc)

    try:
        from llm_wiki.utils.llm import reset_clients

        reset_clients()
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("[admin.provider] reset_clients failed: %s", exc)

    note = "" if written else ".env not writable — runtime env updated only"
    return ProviderUpdateResponse(
        ok=True,
        vendor=req.vendor,
        rag_vendor=req.rag_vendor,
        ingest_vendor=req.ingest_vendor,
        model=req.model,
        ingest_model=req.ingest_model,
        base_url=req.base_url,
        env_written=written,
        note=note,
    )
