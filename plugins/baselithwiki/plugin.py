"""BaselithWiki plugin entrypoint.

Embeds the vendored *Wiki White-Label* engine (domain-agnostic LLM wiki:
RAG chat, PDF→wiki ingestion, hybrid Qdrant retrieval, optional knowledge
graph, multi-tenant auth) as a self-contained ASGI sub-application mounted at
``/baselithwiki`` plus its compiled React/Vite single-page-app.

Integration design
------------------

* **Mount, don't re-export.** The engine ships dozens of routers at canonical
  absolute paths (``/api/*``, ``/auth/*``, ``/healthz``, ``/metrics``). Rather
  than rewrite every prefix we mount the whole engine app under one path; the
  internal routes are preserved byte-for-byte and the SPA reaches them via the
  ``VITE_BASE_PATH`` it was built with. The mount is performed in the
  class-level :meth:`setup_app_middleware` hook because Starlette freezes the
  route table before the async plugin lifespan runs.

* **Drive the real lifespan, in the background.** A mounted sub-app never
  receives ASGI lifespan events, so :meth:`initialize` enters the engine's own
  ``lifespan`` context manager (verbatim: domain-pack load, optional Postgres
  bootstrap, embedder + Qdrant collection warmup, autostart ingest). It runs
  as a background task so a cold model download can never block core boot;
  engine endpoints already answer 503 until warmup completes.

* **Setup mode by default.** :mod:`._bootstrap` isolates the engine from the
  host ``.env`` so the plugin boots without an external Postgres/Ollama. Opt
  into a vertical, Postgres or auth via ``BASELITHWIKI_APP_DOMAIN`` /
  ``BASELITHWIKI_POSTGRES_ENABLED`` / ``BASELITHWIKI_AUTH_REQUIRED`` (and any
  other ``BASELITHWIKI_<KEY>`` engine override).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import yaml

from core.observability.logging import get_logger
from core.plugins import Plugin

from . import _bootstrap

logger = get_logger(__name__)

#: Path the engine + SPA are mounted under on the host application.
MOUNT_PATH = "/baselithwiki"

_CONFIG_FILE = Path(__file__).resolve().parents[2] / "configs" / "plugins.yaml"


def _plugin_enabled() -> bool:
    """Best-effort read of ``configs/plugins.yaml`` enablement.

    ``setup_app_middleware`` runs for every plugin that *declares* the hook,
    regardless of enablement, so we gate the mount ourselves. Defaults to
    enabled when the config is unreadable (mirrors loader leniency).
    """
    try:
        data = yaml.safe_load(_CONFIG_FILE.read_text(encoding="utf-8")) or {}
        entry = data.get("baselithwiki")
        if isinstance(entry, dict):
            return bool(entry.get("enabled", True))
    except (OSError, yaml.YAMLError):
        pass
    return True


class BaselithWikiPlugin(Plugin):
    """Embeds the white-label LLM wiki engine + SPA under ``/baselithwiki``."""

    def __init__(self) -> None:
        super().__init__()
        self._lifespan_cm: Any | None = None
        self._boot_task: asyncio.Task[None] | None = None

    # ---- app-construction-time mount -------------------------------------
    @classmethod
    def setup_app_middleware(cls, app: Any) -> None:
        """Mount the engine sub-app + SPA on the host application.

        Invoked synchronously by ``core.api.factory.create_app`` before the
        middleware stack freezes. Heavy work (model warmup, DB) is deferred to
        :meth:`initialize`; here we only build the route table.
        """
        if not _plugin_enabled():
            logger.info("BaselithWiki disabled in plugins.yaml — skipping mount")
            return
        try:
            _bootstrap.ensure_ready()
            from .app_factory import get_app

            app.mount(MOUNT_PATH, get_app(), name="baselithwiki")
            logger.info("🔌 BaselithWiki mounted at %s", MOUNT_PATH)
        except Exception as exc:  # noqa: BLE001 — never block host boot
            logger.error("BaselithWiki mount failed: %s", exc, exc_info=True)

    # ---- lifecycle -------------------------------------------------------
    async def initialize(self, config: dict[str, Any]) -> None:
        await super().initialize(config)
        _bootstrap.ensure_ready()
        try:
            from .app_factory import get_app

            wiki_app = get_app()
        except Exception as exc:  # noqa: BLE001
            logger.error("BaselithWiki engine import failed: %s", exc, exc_info=True)
            return

        # Enter the engine's verbatim lifespan in the background so a cold
        # embedder/model download can't stall core startup.
        self._lifespan_cm = wiki_app.router.lifespan_context(wiki_app)

        async def _boot() -> None:
            try:
                await self._lifespan_cm.__aenter__()  # type: ignore[union-attr]
                logger.info("✅ BaselithWiki engine warmup complete")
            except Exception as exc:  # noqa: BLE001 — degraded, endpoints 503
                logger.error("BaselithWiki engine warmup failed: %s", exc)

        self._boot_task = asyncio.create_task(_boot())
        logger.info("BaselithWiki initializing (warmup in background)")

    async def shutdown(self) -> None:
        if self._boot_task is not None:
            self._boot_task.cancel()
            try:
                await self._boot_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if self._lifespan_cm is not None:
            try:
                await self._lifespan_cm.__aexit__(None, None, None)
            except Exception as exc:  # noqa: BLE001
                logger.warning("BaselithWiki engine shutdown: %s", exc)
        await super().shutdown()

    # ---- dashboard surface ----------------------------------------------
    def get_ui_tabs(self) -> list[dict[str, str]]:
        return [
            {
                "id": "baselithwiki",
                "label": "Wiki",
                "url": MOUNT_PATH,
            }
        ]
