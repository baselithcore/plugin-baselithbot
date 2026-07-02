"""CLI bridge routes — surface ``baselith`` CLI capabilities in the dashboard.

The whole System Console is **admin-only**, reads included: diagnostics and
infra status disclose deployment topology (datastore hosts/ports, provider and
model configuration), and the plugin's System Console tab is centrally
admin-only (``system: true``) — the backend gate must match what the tab policy
promises. Destructive infra ops (cache flush, db reset) and dev-tool execution
(test/lint/docs) are additionally routed through the shared audit sink + event
bus, so they appear live in the dashboard's event feed exactly like lifecycle
actions.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.auth.types import AuthUser

from ..cli_models import (
    ActionOutcome,
    CacheStats,
    ConfigReport,
    DbStatus,
    DoctorReport,
    InfoReport,
    JobView,
    QueueStatus,
    VerifyReport,
)
from ..service.audit import get_audit_sink
from ..service.bridge import emit_action
from ..service.cli import (
    cache_clear,
    cache_stats,
    config_report,
    db_reset,
    db_status,
    doctor,
    get_job_manager,
    info,
    queue_status,
    verify,
)
from ..i18n import translate
from ._guards import admin_principal, locale_of


async def _record(actor: str, plugin: str, op: str, ok: bool) -> None:
    """Audit + stream a governed CLI action (best-effort)."""
    try:
        await get_audit_sink().record(
            actor=actor, plugin=plugin, op=op, ok=ok, reason=None
        )
    except Exception:  # noqa: BLE001 — audit must never break the action
        pass
    await emit_action(plugin=plugin, op=op, ok=ok, state="unknown")


def build_cli_router() -> APIRouter:
    """Build the CLI-bridge sub-router (admin-only, reads included)."""
    router = APIRouter(
        tags=["baselithcontrol:cli"], dependencies=[Depends(admin_principal)]
    )

    # ── Diagnostics (read-only) ────────────────────────────────
    @router.get("/cli/doctor", response_model=DoctorReport)
    async def cli_doctor() -> DoctorReport:
        """System diagnostics (``baselith doctor``)."""
        return await doctor()

    @router.get("/cli/verify", response_model=VerifyReport)
    async def cli_verify() -> VerifyReport:
        """Installation/environment checks (``baselith verify``)."""
        return await verify()

    @router.get("/cli/info", response_model=InfoReport)
    async def cli_info() -> InfoReport:
        """Framework + workspace snapshot (``baselith info``)."""
        return await info()

    @router.get("/cli/config", response_model=ConfigReport)
    async def cli_config() -> ConfigReport:
        """Redacted config view + validation (``baselith config``)."""
        return await config_report()

    # ── Infrastructure (read-only) ─────────────────────────────
    @router.get("/cli/infra/db", response_model=DbStatus)
    async def cli_db_status() -> DbStatus:
        """Persistent datastore connectivity (``baselith db status``)."""
        return await db_status()

    @router.get("/cli/infra/cache", response_model=CacheStats)
    async def cli_cache_stats() -> CacheStats:
        """Redis cache stats (``baselith cache stats``)."""
        return await cache_stats()

    @router.get("/cli/infra/queue", response_model=QueueStatus)
    async def cli_queue_status() -> QueueStatus:
        """RQ task-queue status (``baselith queue status``)."""
        return await queue_status()

    # ── Infrastructure (destructive, admin) ────────────────────
    @router.post("/cli/infra/cache/clear", response_model=ActionOutcome)
    async def cli_cache_clear(
        user: AuthUser = Depends(admin_principal),
    ) -> ActionOutcome:
        """Flush the Redis cache DB (``baselith cache clear``) — admin, audited."""
        outcome = await cache_clear()
        await _record(user.user_id, "cache", "clear", outcome.ok)
        return outcome

    @router.post("/cli/infra/db/reset", response_model=ActionOutcome)
    async def cli_db_reset(user: AuthUser = Depends(admin_principal)) -> ActionOutcome:
        """Wipe vector stores + cache (``baselith db reset``) — admin, audited."""
        outcome = await db_reset()
        await _record(user.user_id, "database", "reset", outcome.ok)
        return outcome

    # ── Dev tools (subprocess jobs, admin) ─────────────────────
    @router.post("/cli/devtools/{kind}", response_model=JobView)
    async def cli_devtool_run(
        kind: Literal["test", "lint", "docs"],
        request: Request,
        user: AuthUser = Depends(admin_principal),
    ) -> JobView:
        """Start a dev-tool job (``test``/``lint``/``docs``) — admin, audited."""
        manager = get_job_manager(request.app)
        try:
            job = await manager.start(kind)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        # ``ok`` records that the *launch* succeeded — the job outcome is
        # asynchronous and lands in the job view, not this audit record.
        await _record(user.user_id, "devtools", f"{kind}.start", True)
        return job

    @router.get("/cli/devtools/jobs", response_model=list[JobView])
    async def cli_devtool_jobs(
        request: Request,
        _user: AuthUser = Depends(admin_principal),
    ) -> list[JobView]:
        """List dev-tool jobs (admin)."""
        return get_job_manager(request.app).list()

    @router.get("/cli/devtools/jobs/{job_id}", response_model=JobView)
    async def cli_devtool_job(
        job_id: str,
        request: Request,
        _user: AuthUser = Depends(admin_principal),
    ) -> JobView:
        """Fetch one dev-tool job's status + output tail (admin)."""
        job = get_job_manager(request.app).get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=translate("error.job_not_found", locale_of(request)),
            )
        return job

    return router


__all__ = ["build_cli_router"]
