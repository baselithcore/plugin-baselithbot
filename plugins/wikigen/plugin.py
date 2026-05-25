"""WikigenPlugin — full port of llm-wiki-grafiphy into BaselithCore.

Lifespan parity with the original :file:`main.py` (preserved 1:1):

1. Load domain pack if ``APP_DOMAIN`` is set (otherwise setup mode).
2. Validate ``SECRET_KEY`` when ``AUTH_REQUIRED=true`` (fail-fast).
3. Open Postgres pool + bootstrap admin if ``users`` table empty.
4. Warm embedder + Qdrant collection synchronously (blocks /api until ready).
5. Background fire-and-forget: LLM warmup, reranker, examples cache.
6. Auto-ingest pending PDFs deposited by the wizard.

Shutdown: explicit ``close_pool()`` to silence psycopg_pool GC warnings.

Routing
-------
Wikigen routers already declare their own absolute ``/api/...`` prefixes,
so :meth:`get_router_prefix` returns ``""``: all routes mount at root with
their original paths (``/api/chat``, ``/api/wiki``, ``/api/auth``, …).

Middleware
----------
The original ``main.py`` registers app-level middleware (RequestId, CORS,
EmbedCORS, TenantMiddleware, SecurityHeaders, HttpMetrics, _AdminGate).
BaselithCore's plugin contract does not expose an app-middleware extension
point, so the wikigen-specific middlewares are NOT auto-applied by the
plugin loader. Integrators that need full parity call
:meth:`WikigenPlugin.apply_app_middleware` once at app construction
(typically inside ``core.api.factory.create_app``).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# sys.path bootstrap — MUST run before any `from llm_wiki...` import.
#
# The wikigen source tree carries 650+ absolute imports of the form
# ``from llm_wiki.xxx import yyy``. To preserve them verbatim (zero
# regression risk on import paths) the plugin directory is added to
# sys.path so the nested ``plugins/wikigen/llm_wiki/`` package resolves as
# a top-level ``llm_wiki``.
# ---------------------------------------------------------------------------
_PLUGIN_DIR = Path(__file__).resolve().parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from fastapi import APIRouter, FastAPI  # noqa: E402

from core.plugins import RouterPlugin  # noqa: E402

logger = logging.getLogger(__name__)


class WikigenPlugin(RouterPlugin):
    """BaselithCore plugin wrapping the wikigen FastAPI surface."""

    # -- routing ----------------------------------------------------------

    def get_router_prefix(self) -> str:
        # Wikigen routers carry their own ``/api/...`` prefixes; mount at root.
        return ""

    def get_router_tags(self) -> List[str]:
        return ["wikigen"]

    def create_router(self) -> APIRouter:
        # Required by RouterPlugin abstract contract. Real routers are
        # returned by ``get_routers``; this empty stub is never mounted.
        return APIRouter()

    def get_routers(self) -> List[APIRouter]:
        """Return wikigen routers, gated on Postgres / admin flags."""
        from llm_wiki import config as wikigen_config
        from llm_wiki.api.routers.chat import router as chat_router
        from llm_wiki.api.routers.embed_public import router as embed_public_router
        from llm_wiki.api.routers.feedback import router as feedback_router
        from llm_wiki.api.routers.graph import router as graph_router
        from llm_wiki.api.routers.health import router as health_router
        from llm_wiki.api.routers.ingest import router as ingest_router
        from llm_wiki.api.routers.metrics_router import router as metrics_router
        from llm_wiki.api.routers.system import router as system_router
        from llm_wiki.api.routers.wiki import router as wiki_router

        routers: List[APIRouter] = [
            system_router,
            health_router,
            metrics_router,
            wiki_router,
            chat_router,
            feedback_router,
            embed_public_router,
            ingest_router,
            graph_router,
        ]

        if wikigen_config.POSTGRES_ENABLED:
            from llm_wiki.api.routers.auth import router as auth_router
            from llm_wiki.api.routers.conversations import (
                router as conversations_router,
            )
            from llm_wiki.api.routers.embeds_admin import router as embeds_admin_router
            from llm_wiki.api.routers.feedback_admin import (
                router as feedback_admin_router,
            )
            from llm_wiki.api.routers.gdpr import router as gdpr_router
            from llm_wiki.api.routers.memories import router as memories_router
            from llm_wiki.api.routers.rbac import router as rbac_router
            from llm_wiki.api.routers.rbac_groups import router as rbac_groups_router
            from llm_wiki.api.routers.rbac_lifecycle import (
                router as rbac_lifecycle_router,
            )

            routers.extend(
                [
                    auth_router,
                    conversations_router,
                    memories_router,
                    rbac_router,
                    rbac_lifecycle_router,
                    rbac_groups_router,
                    gdpr_router,
                    embeds_admin_router,
                    feedback_admin_router,
                ]
            )
            logger.info(
                "[wikigen] auth+conversations+memories+rbac+groups+gdpr mounted "
                "(public_registration=%s)",
                wikigen_config.AUTH_PUBLIC_REGISTRATION,
            )

        if wikigen_config.ADMIN_API_ENABLED:
            from llm_wiki.api.admin import router as admin_router

            routers.append(admin_router)
            logger.info(
                "[wikigen] admin API mounted (loopback=%s, postgres=%s)",
                wikigen_config.ADMIN_API_LOOPBACK_ONLY,
                wikigen_config.POSTGRES_ENABLED,
            )

        return routers

    # -- static frontend --------------------------------------------------

    def get_static_assets_path(self):
        """Serve the built React SPA when present.

        The wikigen frontend builds to ``ui/dist/``. BaselithCore's lifespan
        mounts the returned directory at ``/plugins/wikigen/static`` and, if
        ``index.html`` exists, also at ``/wikigen`` as an SPA.
        """
        dist = _PLUGIN_DIR / "ui" / "dist"
        return dist if dist.exists() else None

    # -- lifespan ---------------------------------------------------------

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Boot order: pack → secret/DB → bootstrap admin → core warmup → autostart.

        Mirrors :file:`main.py` ``lifespan`` 1:1.
        """
        await super().initialize(config)

        from llm_wiki import config as wikigen_config
        from llm_wiki.domain.registry import load_pack
        from llm_wiki.ingest_raw.jobs import get_registry
        from llm_wiki.observability.logging_config import configure_logging

        configure_logging(
            level_console=os.getenv("LOG_LEVEL_CONSOLE", "INFO"),
            level_file=os.getenv("LOG_LEVEL_FILE", "INFO"),
            log_format=os.getenv("LOG_FORMAT"),
        )

        if wikigen_config.APP_DOMAIN:
            try:
                pack = load_pack()
                logger.info("[wikigen] domain pack: %s (%s)", pack.name, pack.label)
                self._check_vault_pack_marker(pack.name, Path(wikigen_config.WIKI_ROOT))
            except Exception as exc:
                logger.error(
                    "[wikigen] pack load failed: %s — admin API still reachable", exc
                )
        else:
            logger.warning(
                "[wikigen] APP_DOMAIN unset — running in setup mode. "
                "Open the UI and complete the wizard, or run "
                "`wiki-wl init --domain <name>`."
            )

        if (
            wikigen_config.AUTH_REQUIRED
            and not (wikigen_config.SECRET_KEY or "").strip()
        ):
            raise RuntimeError(
                "AUTH_REQUIRED=true ma SECRET_KEY vuota. Genera con "
                '`python -c "import secrets; print(secrets.token_urlsafe(48))"` '
                "e imposta in .env."
            )

        if wikigen_config.POSTGRES_ENABLED:
            try:
                from llm_wiki.auth.bootstrap import bootstrap_admin_if_empty
                from llm_wiki.db.connection import health_check

                if health_check():
                    logger.info("[wikigen] DB ready")
                    bootstrap_admin_if_empty(vault_root=Path(wikigen_config.WIKI_ROOT))
                else:
                    logger.warning(
                        "[wikigen] DB health_check fail — auth/conv/memories diranno 503"
                    )
            except Exception as exc:
                logger.error("[wikigen] DB init failed: %s", exc)

        t0 = time.perf_counter()
        get_registry().set_loop(asyncio.get_running_loop())

        try:
            await self._preload_blocking()
            logger.info("[wikigen] core warmup done in %.2fs", time.perf_counter() - t0)
        except Exception as exc:
            logger.warning("[wikigen] partial warmup: %s", exc)

        # Fire-and-forget: LLM + examples + reranker preload. /api stays
        # responsive while the heavy models warm up in the background.
        asyncio.create_task(self._preload_background())

        if wikigen_config.APP_DOMAIN and getattr(
            wikigen_config, "AUTO_INGEST_ON_STARTUP", True
        ):
            try:
                from llm_wiki.api.routers.ingest import autostart_pending_ingest

                await autostart_pending_ingest()
            except Exception as exc:
                logger.warning("[wikigen] autostart ingest skipped: %s", exc)

    async def shutdown(self) -> None:
        try:
            from llm_wiki import config as wikigen_config

            if wikigen_config.POSTGRES_ENABLED:
                from llm_wiki.db.connection import close_pool

                close_pool()
        except Exception as exc:
            logger.warning("[wikigen][shutdown] close_pool: %s", exc)
        logger.info("[wikigen] bye")
        await super().shutdown()

    # -- helpers ----------------------------------------------------------

    @staticmethod
    async def _preload_blocking() -> None:
        """Synchronous warmup gating route availability: embedder + collection."""
        from llm_wiki.vectorstore.embedder import get_embedder
        from llm_wiki.vectorstore.qdrant_ops import create_collection

        await asyncio.to_thread(get_embedder)
        await asyncio.to_thread(create_collection)

    @staticmethod
    async def _preload_background() -> None:
        from llm_wiki import config as wikigen_config
        from llm_wiki.utils.llm import warmup_llm
        from llm_wiki.vectorstore.reranker import rerank

        try:
            await asyncio.to_thread(
                rerank,
                "warmup",
                [{"score": 1.0, "payload": {"raw_text": "ping"}}],
                top_k=1,
            )
        except Exception as exc:
            logger.debug("[wikigen] reranker warmup skipped: %s", exc)
        if wikigen_config.APP_DOMAIN:
            try:
                await asyncio.to_thread(warmup_llm, wikigen_config.INGEST_OLLAMA_MODEL)
            except Exception as exc:
                logger.warning("[wikigen] LLM warmup failed: %s", exc)
            try:
                from llm_wiki.ingest_raw.examples import _load_candidates

                await asyncio.to_thread(_load_candidates)
            except Exception as exc:
                logger.debug("[wikigen] examples preload skipped: %s", exc)

    @staticmethod
    def _check_vault_pack_marker(pack_name: str, vault_root: Path) -> None:
        """Detect cross-pack vault collisions at boot.

        Each vault carries a ``.pack-id`` marker (written by scaffold + here
        on first boot). Mismatch with the active pack name produces a loud
        warning so RAG/ingest do not silently operate on the wrong dataset.
        """
        marker = vault_root / ".pack-id"
        try:
            if marker.exists():
                recorded = marker.read_text(encoding="utf-8").strip()
                if recorded and recorded != pack_name:
                    logger.warning(
                        "[wikigen] VAULT/PACK MISMATCH: vault %s carries "
                        "pack-id=%r but APP_DOMAIN=%r — RAG/ingest will "
                        "operate on the wrong pack's data. Use the wizard "
                        "/api/admin/tenants/{name}/activate to realign "
                        "WIKI_ROOT, or edit .env so APP_DOMAIN=%s.",
                        vault_root,
                        recorded,
                        pack_name,
                        recorded,
                    )
                    return
            else:
                vault_root.mkdir(parents=True, exist_ok=True)
                marker.write_text(pack_name + "\n", encoding="utf-8")
        except OSError as exc:
            logger.debug("[wikigen] pack-id marker check skipped: %s", exc)

    # -- middleware integration ------------------------------------------

    @classmethod
    def setup_app_middleware(cls, app: Any) -> None:
        """Plugin hook invoked by ``core.api.factory.create_app``.

        Defers to :meth:`apply_app_middleware` so the helper stays callable
        manually (e.g. from a custom factory or a test harness).
        """
        cls.apply_app_middleware(app)

    @staticmethod
    def apply_app_middleware(app: FastAPI) -> None:
        """Apply the wikigen-specific app-level middleware stack.

        BaselithCore's plugin contract has no app-middleware extension
        point, so integrators that need full parity with the original
        :file:`main.py` invoke this helper once at app construction.

        Registration order mirrors the original. Starlette wraps in
        reverse, so the effective request flow becomes::

            request → RequestId → CORS → SecurityHeaders → TenantMiddleware
                                                         → HttpMetrics → routes
        """
        from llm_wiki import config as wikigen_config
        from llm_wiki.observability.http_middleware import HttpMetricsMiddleware
        from llm_wiki.observability.request_id import RequestIdMiddleware
        from llm_wiki.observability.tracing import setup_tracing

        try:
            setup_tracing(app)
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "[wikigen] OpenTelemetry setup fallito (continuo senza): %s", exc
            )

        # Innermost first (Starlette inverts order on add_middleware).
        app.add_middleware(HttpMetricsMiddleware)

        if wikigen_config.POSTGRES_ENABLED:
            from llm_wiki.auth.middleware import (
                EmbedCORSMiddleware,
                SecurityHeadersMiddleware,
                TenantMiddleware,
            )
            from fastapi.middleware.cors import CORSMiddleware

            app.add_middleware(TenantMiddleware)
            app.add_middleware(SecurityHeadersMiddleware)
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["X-Tenant-ID", "X-Request-ID"],
            )
            app.add_middleware(EmbedCORSMiddleware)
        else:
            from fastapi.middleware.cors import CORSMiddleware

            app.add_middleware(
                CORSMiddleware,
                allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["X-Request-ID"],
            )

        app.add_middleware(RequestIdMiddleware)

        if wikigen_config.ADMIN_API_ENABLED:
            WikigenPlugin._install_admin_gate(app, wikigen_config)

    @staticmethod
    def _install_admin_gate(app: FastAPI, wikigen_config: Any) -> None:
        """Mount the loopback/bearer admin gate for ``/api/admin/*``."""
        import ipaddress as _ipaddress

        from fastapi import Request
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.responses import JSONResponse

        _PROXY_HEADER_NAMES = (
            "x-forwarded-for",
            "forwarded",
            "x-real-ip",
            "x-client-ip",
        )

        def _is_loopback_client(host: str | None) -> bool:
            if not host:
                return False
            try:
                return _ipaddress.ip_address(host).is_loopback
            except ValueError:
                return False

        class _AdminGateMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):  # type: ignore[override]
                path = request.url.path
                if not path.startswith("/api/admin"):
                    return await call_next(request)

                if wikigen_config.ADMIN_API_LOOPBACK_ONLY:
                    client_host = request.client.host if request.client else None
                    has_bearer = (
                        request.headers.get("authorization", "")
                        .lower()
                        .startswith("bearer ")
                    )
                    if not (wikigen_config.POSTGRES_ENABLED and has_bearer):
                        proxy_header = next(
                            (h for h in _PROXY_HEADER_NAMES if h in request.headers),
                            None,
                        )
                        if proxy_header is not None or not _is_loopback_client(
                            client_host
                        ):
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "detail": (
                                        "admin endpoints richiedono loopback "
                                        "(setup mode) o bearer admin (deploy)."
                                    )
                                },
                            )
                return await call_next(request)

        app.add_middleware(_AdminGateMiddleware)
