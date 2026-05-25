"""Entry point: FastAPI app served via Uvicorn on Unix socket."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router as api_router
from .api.middleware import (
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    TenantMiddleware,
)
from .core.config import settings
from .core.logging import log, setup_logging
from .core.telemetry import setup_tracing
from .db.migrate import upgrade_to_head
from .db.rls import install_rls_hook
from .db.session import SessionLocal
from .services import policy_index


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.debug)
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    setup_tracing()
    upgrade_to_head()
    install_rls_hook()
    try:
        async with SessionLocal() as db:
            n = await policy_index.reindex_all(db)
            log.info("policy_index.reindex_complete", rules_indexed=n)
    except Exception as exc:
        log.warning("policy_index.reindex_skipped", error=str(exc))
    log.info("docheck.startup", version=settings.version)
    yield
    log.info("docheck.shutdown")


app = FastAPI(
    title="doCheck Engine",
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3100",
        "app://docheck",
    ],
    # Permit Electron / VSCode webview / Tauri origins via regex.
    allow_origin_regex=r"^(vscode-webview://[^/]+|app://[^/]+|tauri://[^/]+|file://)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-User-Id", "X-Tenant-Id", "X-Request-Id"],
    expose_headers=["X-Request-Id", "X-Tenant-Id"],
)

app.include_router(api_router, prefix="/api/v1")


def main() -> None:
    setup_logging(settings.debug)
    socket_path = str(settings.socket_path)
    if settings.bind_tcp:
        host, port_str = settings.bind_tcp.split(":")
        log.warning("docheck.bind_tcp", host=host, port=port_str)
        uvicorn.run(
            "docheck.main:app",
            host=host,
            port=int(port_str),
            reload=settings.debug,
            # Watch only source. Avoids reload storm from site-packages cache files.
            reload_dirs=["src/docheck"] if settings.debug else None,
            reload_excludes=["*.pyc", "__pycache__/*", "storage/*"]
            if settings.debug
            else None,
        )
    else:
        # Unix domain socket — no TCP exposure
        if os.path.exists(socket_path):
            os.remove(socket_path)
        uvicorn.run("docheck.main:app", uds=socket_path)


if __name__ == "__main__":
    main()
