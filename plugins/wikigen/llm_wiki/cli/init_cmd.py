"""``wiki-wl init`` — scaffold a fresh Domain Pack.

Thin wrapper over :func:`llm_wiki.admin.scaffold.scaffold_pack` so the
CLI shares one source of truth with the UI wizard for validation, YAML
rewrites and ``.env`` upserts.
"""

from __future__ import annotations

import typer
from rich.panel import Panel

from llm_wiki.cli._output import (
    EXIT_USAGE_ERROR,
    EXIT_USER_ERROR,
    emit_error,
    emit_json,
    get_ctx,
)


def init(
    ctx: typer.Context,
    domain: str = typer.Option(
        ..., "--domain", "-d", help="New domain name (snake_case ASCII)."
    ),
    label: str = typer.Option(
        "", "--label", "-l", help="Human label, e.g. 'Wiki Legale'."
    ),
    description: str = typer.Option("", "--description", help="Short description."),
    language: str = typer.Option("it", "--language", help="ISO 639-1 language code."),
    vault_root: str = typer.Option(
        "",
        "--vault-root",
        help="Absolute path to the vault root. Defaults to ./vaults/<domain>.",
    ),
    write_env: bool = typer.Option(
        True,
        "--write-env/--no-write-env",
        help="Write .env with APP_DOMAIN + WIKI_ROOT.",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing domain dir."
    ),
    synthesize: bool = typer.Option(
        True,
        "--synthesize/--no-synthesize",
        help=(
            "Call the configured LLM at scaffold time to generate a "
            "domain-tuned system prompt (default: on). Disable to keep "
            "the bare _template skeleton unchanged."
        ),
    ),
) -> None:
    """Scaffold a fresh Domain Pack from the ``_template`` skeleton."""
    from pydantic import ValidationError

    from llm_wiki.admin.scaffold import (
        ScaffoldError,
        ScaffoldRequest,
        repo_root,
        scaffold_pack,
    )

    try:
        req = ScaffoldRequest(
            name=domain,
            label=label,
            description=description,
            language=language,
            vault_root=vault_root,
            write_env=write_env,
            force=force,
            activate=write_env,
            synthesize_prompts=synthesize,
        )
    except ValidationError as exc:
        first = exc.errors()[0]
        emit_error(ctx, message=first["msg"], exit_code=EXIT_USAGE_ERROR)
        raise

    try:
        result = scaffold_pack(req)
    except ScaffoldError as exc:
        emit_error(ctx, message=str(exc), exit_code=EXIT_USER_ERROR)
        raise

    octx = get_ctx(ctx)
    rr = repo_root()
    pack_rel = result.target_pack_dir.relative_to(rr)

    if octx.json_output:
        emit_json(
            {
                "ok": True,
                "name": result.name,
                "target_pack_dir": str(result.target_pack_dir),
                "vault_path": str(result.vault_path),
                "env_written": result.env_written,
                "env_path": str(result.env_path) if result.env_path else None,
                "activated": result.activated,
                "synthesis_applied": result.synthesis_applied,
                "synthesis_model": result.synthesis_model,
                "synthesis_warning": result.synthesis_warning,
                "next_steps": result.next_steps,
            }
        )
        return

    env_line = (
        f"[green]✓[/green] Wrote [bold].env[/bold] with APP_DOMAIN={result.name}\n"
        if result.env_written
        else f"[yellow]·[/yellow] .env unchanged — set [cyan]APP_DOMAIN={result.name}[/cyan] manually\n"
    )
    if result.synthesis_applied:
        synthesis_line = (
            f"[green]✓[/green] Synthesised domain-tuned prompts via "
            f"[bold]{result.synthesis_model}[/bold]\n"
        )
    elif result.synthesis_warning:
        synthesis_line = (
            f"[yellow]·[/yellow] Prompt synthesis skipped "
            f"([dim]{result.synthesis_warning}[/dim]) — using _template defaults\n"
        )
    else:
        synthesis_line = ""
    next_lines = "\n".join(
        f"  {i + 1}. {step}" for i, step in enumerate(result.next_steps)
    )
    octx.console.print(
        Panel.fit(
            f"[green]✓[/green] Scaffolded domain pack at [bold]{pack_rel}[/bold]\n"
            f"[green]✓[/green] Vault directory at [bold]{result.vault_path}[/bold]\n"
            + env_line
            + synthesis_line
            + "\nNext steps:\n"
            + next_lines,
            title=f"Domain '{result.name}' ready",
        )
    )
