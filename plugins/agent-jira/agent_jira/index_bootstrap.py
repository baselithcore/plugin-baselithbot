from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from pathlib import Path
from typing import Any, Optional

from agent_jira.vectorstore import index_docs
from agent_jira.config import (
    INDEX_BOOTSTRAP_ENABLED,
    INDEX_BOOTSTRAP_SENTINEL,
    INDEX_STATE_PATH,
    MULTI_TENANT_ENABLED,
)

logger = logging.getLogger(__name__)


class IndexBootstrapper:
    def __init__(self, sentinel_path: Path) -> None:
        self._sentinel = sentinel_path
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._current_mode: Optional[str] = None
        self._last_error: Optional[str] = None
        self._last_completed_mode: Optional[str] = None

    def is_bootstrapped(self) -> bool:
        return self._sentinel.exists()

    def is_running(self) -> bool:
        task = self._task
        return task is not None and not task.done()

    def status(self) -> dict[str, Any]:
        return {
            "bootstrapped": self.is_bootstrapped(),
            "running": self.is_running(),
            "current_mode": self._current_mode,
            "last_completed_mode": self._last_completed_mode,
            "last_error": self._last_error,
        }

    def has_pending_changes(self) -> bool:
        """Check if indexing is required.

        Now that indexing is optimized (smart header scan), we can be more aggressive
        about checking. We largely defer to the actual indexer to skip unchanged files.
        """
        if not self.is_bootstrapped():
            return True

        if not INDEX_STATE_PATH.exists():
            return True

        # If we have state, let the fast indexer run and check timestamps
        return True

    async def schedule(
        self,
        *,
        force_full: bool = False,
        mode: Optional[str] = None,
        skip_if_no_changes: bool = True,
    ) -> bool:
        if not INDEX_BOOTSTRAP_ENABLED:
            logger.info("Index bootstrap disabilitato via config, skip schedule.")
            return False

        async with self._lock:
            if self.is_running():
                return False

            # Quick change detection optimization
            if skip_if_no_changes and not force_full and self.is_bootstrapped():
                if not self.has_pending_changes():
                    logger.info(
                        "[index] No pending changes detected, skipping bootstrap (startup optimization)."
                    )
                    return False

            resolved_mode = mode
            if resolved_mode is None:
                resolved_mode = (
                    "full"
                    if force_full or not self.is_bootstrapped()
                    else "incremental"
                )

            self._current_mode = resolved_mode
            self._task = asyncio.create_task(self._run(resolved_mode))
            self._last_error = None
            return True

    async def _run(self, mode: str) -> None:
        incremental = mode != "full"
        logger.info("[index] bootstrap task started (%s)", mode)
        try:
            # Assicura che i constraint del grafo siano attivi
            from agent_jira.graphdb import graph_db

            if graph_db.is_enabled():
                graph_db.create_constraints()

            from agent_jira.cost_control import CostController

            with CostController.unbounded(reason="index-bootstrap"):
                if MULTI_TENANT_ENABLED:
                    await self._run_per_tenant(incremental)
                else:
                    await index_docs(incremental=incremental)
            if mode == "full":
                self._mark_bootstrapped()
            self._last_completed_mode = mode
            logger.info("[index] bootstrap task completed (%s)", mode)
        except Exception as exc:  # pragma: no cover - errors logged
            self._last_error = str(exc)
            logger.exception("[index] bootstrap task failed (%s): %s", mode, exc)
        finally:
            self._current_mode = None
            async with self._lock:
                self._task = None

    async def _run_per_tenant(self, incremental: bool) -> None:
        """Indicizza la KB iterando per-tenant con contextvar impostato.

        Ogni tenant viene indicizzato in isolamento: il filesystem source
        risolve dinamicamente la root tenant-scoped, i payload Qdrant/FalkorDB
        contengono il tenant_id, e le cache sono namespacate.
        """
        from agent_jira.db.tenants import list_tenants
        from agent_jira.tenant_context import TenantInfo, set_current_tenant

        try:
            tenants = list_tenants(active_only=True)
        except Exception as exc:
            logger.exception(
                "[index] impossibile elencare i tenant per il bootstrap: %s", exc
            )
            return

        if not tenants:
            logger.info(
                "[index] nessun tenant attivo trovato: bootstrap multi-tenant skipped"
            )
            return

        for tenant in tenants:
            tenant_id = str(tenant.get("id", "")).strip()
            if not tenant_id:
                continue
            slug = tenant.get("slug")
            plan = tenant.get("plan")
            info = TenantInfo(tenant_id=tenant_id, slug=slug, plan=plan)
            token = set_current_tenant(info)
            try:
                logger.info("[index] bootstrap tenant=%s slug=%s", tenant_id, slug)
                await index_docs(incremental=incremental)
            except Exception as exc:
                logger.exception(
                    "[index] errore durante bootstrap per tenant %s: %s",
                    tenant_id,
                    exc,
                )
            finally:
                from agent_jira.tenant_context import _tenant_context

                _tenant_context.reset(token)

    def _mark_bootstrapped(self) -> None:
        self._sentinel.parent.mkdir(parents=True, exist_ok=True)
        self._sentinel.write_text("ok")

    def register_manual_completion(self, mode: str) -> None:
        self._last_completed_mode = mode
        if mode == "full":
            self._mark_bootstrapped()
        self._last_error = None

    async def shutdown(self) -> None:
        async with self._lock:
            task = self._task
            self._task = None
        if task is None:
            return
        task.cancel()
        with suppress(Exception, asyncio.CancelledError):
            await task


bootstrapper = IndexBootstrapper(INDEX_BOOTSTRAP_SENTINEL)


async def ensure_startup_bootstrap() -> None:
    await bootstrapper.schedule()


__all__ = ["bootstrapper", "ensure_startup_bootstrap"]
