"""``wiki-wl ingest <file>`` — pipeline a single PDF into the vault."""

from __future__ import annotations

from pathlib import Path

import typer

from llm_wiki.cli._output import (
    EXIT_INFRA_ERROR,
    EXIT_USER_ERROR,
    emit_error,
    emit_json,
    get_ctx,
)


def ingest(
    ctx: typer.Context,
    file: Path = typer.Argument(..., help="Path to a PDF inside the vault `raw/` dir."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't write to disk."),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing pages."
    ),
    reindex: bool = typer.Option(
        True, "--reindex/--no-reindex", help="Reindex Qdrant."
    ),
    only_source: bool = typer.Option(
        False, "--only-source", help="Generate only the source page (skip derived)."
    ),
) -> None:
    """Run the ingest pipeline on a single raw PDF."""
    octx = get_ctx(ctx)

    target = file.expanduser()
    if not target.is_absolute():
        target = target.resolve()
    if not target.is_file():
        emit_error(
            ctx,
            message=f"file not found: {target}",
            exit_code=EXIT_USER_ERROR,
            detail={"file": str(target)},
        )
        raise

    try:
        from llm_wiki.ingest_raw import ingest_raw_file
    except ImportError as exc:
        emit_error(
            ctx,
            message=(
                "ingest stack unavailable — install with `pip install -e .[ingest]`. "
                f"Original error: {exc}"
            ),
            exit_code=EXIT_INFRA_ERROR,
        )
        raise

    try:
        result = ingest_raw_file(
            target,
            dry_run=dry_run,
            overwrite=overwrite,
            reindex=reindex,
            only_source_page=only_source,
        )
    except KeyboardInterrupt:
        octx.console.print("[yellow]·[/yellow] ingest interrupted")
        raise typer.Exit(code=130) from None
    except Exception as exc:
        emit_error(
            ctx,
            message=f"ingest failed: {exc}",
            exit_code=EXIT_INFRA_ERROR,
            detail={"file": str(target)},
        )
        raise

    if octx.json_output:
        emit_json(
            {
                "ok": True,
                "file": str(target),
                "summary": result.summary(),
                "pages": [
                    {"status": p.status, "target": str(p.target_path)}
                    for p in result.pages
                ],
            }
        )
        return

    octx.console.print(result.summary())
    for page in result.pages:
        octx.console.print(f"  [{page.status}] {page.target_path}")
