"""Plugin entry point for the Compliance (GRC) console.

Exposes a single governance surface over the framework's compliance primitives:

* :class:`RouterPlugin` — the async REST API under ``/api/compliance`` wrapping
  NIS2/DORA incidents (``core.incidents``), GDPR DSR (``core.privacy``), the
  DORA Register of Information (``core.thirdparty``), and AI-Act transparency
  (``core.transparency``).
* a mounted React/Vite dashboard SPA at ``/compliance`` (built artifacts only;
  ``ui/src`` never ships in the wheel).

It is a **system** plugin (``manifest.system: true``): platform-governance
machinery, admin-only in the nav, not per-tenant. ``core/`` is never modified
(Sacred Core); only framework primitives are imported.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.observability.logging import get_logger
from core.plugins import RouterPlugin

from .config import ComplianceConfig

logger = get_logger(__name__)
MOUNT_PATH = "/compliance"
_UI_DIST = Path(__file__).resolve().parent / "ui" / "dist"

__all__ = ["CompliancePlugin"]


class CompliancePlugin(RouterPlugin):
    """Governance/Risk/Compliance console: NIS2, DORA, GDPR, and the AI Act."""

    def __init__(self) -> None:
        super().__init__()
        self._compliance_config: ComplianceConfig | None = None

    @property
    def config(self) -> ComplianceConfig:
        """The validated runtime configuration (built on first access)."""
        if self._compliance_config is None:
            self._compliance_config = ComplianceConfig()
        return self._compliance_config

    async def initialize(self, config: dict[str, Any]) -> None:
        """Validate config and publish it for request-time service construction."""
        await super().initialize(config)
        self._compliance_config = ComplianceConfig.from_plugin_config(config)
        logger.info(
            "Compliance console initialized (require_admin=%s)",
            self._compliance_config.require_admin,
        )

    def create_router(self) -> Any:
        """Build the compliance API mounted at ``/api/compliance``."""
        from fastapi import APIRouter

        from .router import build_compliance_router

        router = APIRouter()
        router.include_router(build_compliance_router())
        return router

    def get_ui_tabs(self) -> list[dict[str, str]]:
        """Expose each regulatory domain as an individually gateable tab.

        Tab ids mirror the SPA's nav ids so the central RBAC matrix can restrict
        any one of them. As a system plugin these tabs are admin-only by default
        (the central tab discovery flips system-plugin tabs to effective-admin).
        """
        return [
            {"id": "incidents", "label": "Incident Reporting (NIS2)", "url": MOUNT_PATH},
            {"id": "dora", "label": "Major Incidents (DORA)", "url": MOUNT_PATH},
            {"id": "dsr", "label": "Data Subject Requests (GDPR)", "url": MOUNT_PATH},
            {
                "id": "thirdparty",
                "label": "ICT Third-Party Register (DORA)",
                "url": MOUNT_PATH,
            },
            {
                "id": "transparency",
                "label": "AI Transparency (AI Act)",
                "url": MOUNT_PATH,
            },
        ]

    @classmethod
    def setup_app_middleware(cls, app: Any) -> None:
        """Mount the built SPA before the middleware stack freezes.

        Runs at app-construction time. Missing build output degrades gracefully —
        the API still serves; only the bundled UI is unavailable.
        """
        if not _UI_DIST.exists():
            logger.info("Compliance UI not built; SPA mount skipped (%s)", _UI_DIST)
            return
        try:
            from fastapi.staticfiles import StaticFiles

            app.mount(
                MOUNT_PATH,
                StaticFiles(directory=str(_UI_DIST), html=True),
                name="compliance",
            )
            logger.info("Compliance SPA mounted at %s", MOUNT_PATH)
        except Exception as exc:  # noqa: BLE001 — never break app construction
            logger.error("Compliance SPA mount failed: %s", exc, exc_info=True)


def create_plugin() -> CompliancePlugin:
    """Plugin factory function (required by the plugin loader)."""
    return CompliancePlugin()
