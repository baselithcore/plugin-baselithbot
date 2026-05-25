"""``wiki-wl serve`` — start the FastAPI server (binds ``main:app``)."""

from __future__ import annotations

from typing import Any

import typer

from llm_wiki.cli._output import EXIT_INTERRUPTED, get_ctx


def serve(
    ctx: typer.Context,
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
    workers: int = typer.Option(
        1,
        "--workers",
        help="Uvicorn workers (mutually exclusive with --reload).",
        min=1,
        max=64,
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="Uvicorn log level: critical|error|warning|info|debug|trace.",
    ),
) -> None:
    """Start the FastAPI server."""
    import uvicorn

    from llm_wiki import config

    octx = get_ctx(ctx)
    config.print_banner()

    if reload and workers > 1:
        octx.console.print(
            "[yellow]![/yellow] --reload forces single-worker mode; ignoring --workers"
        )
        workers = 1

    # `reload_includes=*.py` keeps uvicorn focused on source changes. Without
    # it, watchfiles' default filter watches the whole cwd — so every page
    # written during ingestion (vaults/<name>/wiki/**/*.md, log.md,
    # index.md, raw/*.pdf uploads) triggers a worker restart, killing
    # in-flight jobs and looping `autostart_pending_ingest` forever.
    extra: dict[str, Any] = {}
    if reload:
        extra = {
            "reload_includes": ["*.py"],
            "reload_excludes": [
                "vaults/*",
                "domains/*/vault/*",
                "raw/*",
                "*.md",
                "*.yaml",
                "*.yml",
                "*.json",
                "frontend/*",
            ],
        }
    else:
        extra["workers"] = workers

    # Mark the env so the worker process can detect it's running under
    # `--reload` even though uvicorn itself exposes no canonical signal.
    # The admin /restart endpoint relies on this to decide between
    # touch-based reload (safe) vs SIGTERM (kills bare process).
    if reload:
        import os as _os

        _os.environ["LLMWIKI_RUN_RELOAD"] = "1"

    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level.lower(),
            **extra,
        )
    except KeyboardInterrupt:
        octx.console.print("[yellow]·[/yellow] interrupted")
        raise typer.Exit(code=EXIT_INTERRUPTED) from None
