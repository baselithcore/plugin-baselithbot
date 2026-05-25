"""``wiki-wl questions ...`` — manage doc-grounded starter questions.

Subcommands:

- ``regenerate``  Rebuild ``pack.yaml.ui.suggested_questions`` from a
  fresh sample of pages in the active vault. Idempotent unless
  ``--force``; uses the marker file written by the post-ingest hook.
"""

from __future__ import annotations

from pathlib import Path

import typer

from llm_wiki.cli._output import (
    emit_error,
    emit_json,
    get_ctx,
)

questions_app = typer.Typer(help="Doc-grounded starter questions (homepage chips)")


@questions_app.command("regenerate")
def questions_regenerate(
    ctx: typer.Context,
    pack: str = typer.Option(
        "",
        "--pack",
        help="Slug of the pack to operate on. Defaults to APP_DOMAIN.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Bypass the one-shot marker and regenerate even if already done.",
    ),
    min_questions: int = typer.Option(
        0, "--min", help="Override QUESTIONS_FROM_DOCS_MIN (0 = use config)."
    ),
    max_questions: int = typer.Option(
        0, "--max", help="Override QUESTIONS_FROM_DOCS_MAX (0 = use config)."
    ),
) -> None:
    """Sample the active vault and rewrite ``pack.yaml.ui.suggested_questions``.

    Runs the same generator the auto-ingest finalizer triggers. Useful
    after re-uploading documents or when the original scaffold ran
    before any docs were ingested.
    """
    octx = get_ctx(ctx)

    import os as _os

    from llm_wiki import config as _cfg
    from llm_wiki.admin.questions_from_docs import regenerate_questions_from_docs
    from llm_wiki.admin.scaffold import repo_root

    slug = pack.strip() or _os.environ.get("APP_DOMAIN", "").strip()
    if not slug:
        emit_error(ctx, message="no pack specified (pass --pack or set APP_DOMAIN)")

    pack_dir = repo_root() / "domains" / slug
    if not pack_dir.is_dir():
        emit_error(ctx, message=f"pack directory not found: {pack_dir}")

    wiki_dir: Path = _cfg.WIKI_ROOT / "wiki"
    if not wiki_dir.is_dir():
        emit_error(ctx, message=f"wiki directory not found: {wiki_dir}")

    outcome = regenerate_questions_from_docs(
        pack_dir,
        wiki_dir,
        force=force,
        min_questions=min_questions or None,
        max_questions=max_questions or None,
    )

    payload = {
        "pack": slug,
        "applied": outcome.applied,
        "questions_written": outcome.questions_written,
        "model": outcome.model,
        "sampled_pages": outcome.sampled_pages,
        "skipped_reason": outcome.skipped_reason,
        "warning": outcome.warning,
    }
    if octx.json_output:
        emit_json(payload)
        return

    if outcome.applied:
        octx.console.print(
            f"[green]✓[/green] {outcome.questions_written} domande scritte in "
            f"[bold]{pack_dir / 'pack.yaml'}[/bold] "
            f"(modello: {outcome.model}, pagine campione: {outcome.sampled_pages})"
        )
        return

    if outcome.skipped_reason:
        octx.console.print(f"[yellow]skip:[/yellow] {outcome.skipped_reason}")
    if outcome.warning:
        octx.console.print(f"[red]warning:[/red] {outcome.warning}")
    raise typer.Exit(code=0 if outcome.skipped_reason else 1)


__all__ = ["questions_app"]
