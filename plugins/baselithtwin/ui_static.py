"""Static mount for the bundled React dashboard.

Serves the Vite build output (``ui/dist``) under the plugin's router with an SPA
fallback so client-side routes resolve to ``index.html``. Kept separate from the
API router so transport-vs-asset concerns stay split and neither file approaches
the size cap. A missing build degrades to a helpful placeholder, never a 500.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.observability.logging import get_logger

logger = get_logger(__name__)

_UI_DIST = Path(__file__).resolve().parent / "ui" / "dist"


def mount_dashboard_ui(router: Any) -> None:
    """Attach dashboard static routes to ``router`` if a build exists."""
    from fastapi import HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    index_file = _UI_DIST / "index.html"

    @router.get("/ui/", include_in_schema=False)
    async def _ui_root() -> Any:
        if not index_file.exists():
            return HTMLResponse(
                "<h1>BaselithTwin</h1><p>Dashboard not built. Run "
                "<code>npm install &amp;&amp; npm run build</code> under "
                "<code>ui/</code>.</p>",
                status_code=200,
            )
        return FileResponse(index_file)

    @router.get("/ui/{path:path}", include_in_schema=False)
    async def _ui_asset(path: str) -> Any:
        candidate = (_UI_DIST / path).resolve()
        if _UI_DIST in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        if index_file.exists():
            return FileResponse(index_file)  # SPA fallback
        raise HTTPException(status_code=404, detail="asset not found")

    logger.info("twin_dashboard_ui_mounted", dist_exists=index_file.exists())


__all__ = ["mount_dashboard_ui"]
