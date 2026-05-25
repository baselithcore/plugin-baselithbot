"""``wiki-wl pack ...`` — manage installed Domain Packs.

Subcommands: ``list``, ``show``, ``validate``, ``activate``.

Reading uses the strict :class:`DomainPack` pydantic model so malformed
packs surface diagnostic errors instead of being silently skipped — a
habit-forming guard before deploying a vertical to production.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from rich.panel import Panel
from rich.table import Table

from llm_wiki.cli._output import (
    EXIT_USER_ERROR,
    emit_error,
    emit_json,
    get_ctx,
)

pack_app = typer.Typer(help="Domain Pack management")


def _domains_dir() -> Path:
    from llm_wiki.admin.scaffold import repo_root

    return repo_root() / "domains"


def _load_pack_safely(slug: str):
    """Return ``(pack | None, error_message | None)`` for a given slug."""
    import yaml
    from pydantic import ValidationError

    from llm_wiki.domain.pack import DomainPack

    pack_yaml = _domains_dir() / slug / "pack.yaml"
    if not pack_yaml.is_file():
        return None, f"no pack.yaml at {pack_yaml}"
    try:
        data = yaml.safe_load(pack_yaml.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return None, f"invalid YAML: {exc}"
    try:
        return DomainPack(**data), None
    except ValidationError as exc:
        errs = exc.errors()
        msg = errs[0]["msg"] if errs else str(exc)
        return None, f"validation: {msg}"


@pack_app.command("list")
def pack_list(ctx: typer.Context) -> None:
    """List Domain Packs available under ``domains/``."""
    from llm_wiki import config

    octx = get_ctx(ctx)
    domains_dir = _domains_dir()
    if not domains_dir.is_dir():
        emit_error(ctx, message="domains/ directory not found", exit_code=EXIT_USER_ERROR)
        raise

    rows: list[dict[str, Any]] = []
    for entry in sorted(domains_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not (entry / "pack.yaml").is_file():
            continue
        slug = entry.name
        pack, err = _load_pack_safely(slug)
        if pack is not None:
            rows.append(
                {
                    "name": pack.name,
                    "label": pack.label,
                    "language": pack.language,
                    "page_types": [pt.id for pt in pack.page_types],
                    "seed": bool(getattr(pack, "seed", False)),
                    "active": pack.name == config.APP_DOMAIN,
                    "path": str(entry),
                }
            )
        else:
            rows.append(
                {
                    "name": slug,
                    "label": f"<invalid: {err}>",
                    "language": None,
                    "page_types": [],
                    "seed": False,
                    "active": False,
                    "path": str(entry),
                    "error": err,
                }
            )

    if octx.json_output:
        emit_json({"ok": True, "packs": rows})
        return

    t = Table(title="Domain Packs")
    t.add_column("name", style="cyan")
    t.add_column("label", style="white")
    t.add_column("lang", style="dim")
    t.add_column("page types", style="dim")
    t.add_column("flags", style="white")
    for r in rows:
        flags = []
        if r.get("active"):
            flags.append("[green]active[/green]")
        if r.get("seed"):
            flags.append("[blue]seed[/blue]")
        if r.get("error"):
            flags.append("[red]invalid[/red]")
        t.add_row(
            str(r["name"]),
            str(r["label"]),
            str(r.get("language") or "-"),
            ", ".join(r["page_types"]) if r["page_types"] else "-",
            " ".join(flags) or "-",
        )
    octx.console.print(t)


@pack_app.command("show")
def pack_show(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Pack slug (the directory name under domains/)."),
) -> None:
    """Print the parsed Domain Pack metadata for one slug."""
    octx = get_ctx(ctx)
    pack, err = _load_pack_safely(name)
    if pack is None:
        emit_error(ctx, message=f"pack '{name}' invalid: {err}", exit_code=EXIT_USER_ERROR)
        raise

    if octx.json_output:
        emit_json({"ok": True, "pack": pack.model_dump()})
        return

    pack_dir = _domains_dir() / name
    body = (
        f"[bold]name[/bold]:        {pack.name}\n"
        f"[bold]label[/bold]:       {pack.label}\n"
        f"[bold]description[/bold]: {pack.description or '-'}\n"
        f"[bold]language[/bold]:    {pack.language}\n"
        f"[bold]seed[/bold]:        {bool(getattr(pack, 'seed', False))}\n"
        f"[bold]page types[/bold]:  "
        + ", ".join(f"{pt.id}({pt.folder})" for pt in pack.page_types)
        + "\n"
        "[bold]grouping[/bold]:    " + (", ".join(r.key for r in pack.grouping) or "-") + "\n"
        f"[bold]path[/bold]:        {pack_dir}"
    )
    octx.console.print(Panel.fit(body, title=f"Pack '{pack.name}'"))


@pack_app.command("validate")
def pack_validate(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Pack slug to validate."),
) -> None:
    """Validate a pack: pydantic shape + filesystem layout (prompts, schema)."""
    octx = get_ctx(ctx)
    pack_dir = _domains_dir() / name
    issues: list[str] = []

    pack, err = _load_pack_safely(name)
    if pack is None:
        issues.append(f"pack.yaml: {err}")
    if not (pack_dir / "schema.yaml").is_file():
        issues.append("schema.yaml: missing")
    for required in ("system.j2", "user.j2", "no_hits.j2"):
        if not (pack_dir / "prompts" / required).is_file():
            issues.append(f"prompts/{required}: missing")
    ingest_dir = pack_dir / "prompts" / "ingest"
    if not ingest_dir.is_dir():
        issues.append("prompts/ingest/: missing")

    ok = not issues
    if octx.json_output:
        emit_json(
            {"ok": ok, "name": name, "issues": issues},
            exit_code=0 if ok else EXIT_USER_ERROR,
        )
        return

    if ok:
        octx.console.print(f"[green]✓[/green] pack '{name}' is valid.")
        return
    octx.console.print(f"[red]✗[/red] pack '{name}' has {len(issues)} issue(s):")
    for it in issues:
        octx.console.print(f"  • {it}")
    raise typer.Exit(code=EXIT_USER_ERROR)


@pack_app.command("activate")
def pack_activate(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Pack slug to activate (writes APP_DOMAIN to .env)."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompt (for non-interactive use)."
    ),
) -> None:
    """Set ``APP_DOMAIN=<name>`` in ``.env``. Requires server restart to take effect."""
    octx = get_ctx(ctx)
    pack, err = _load_pack_safely(name)
    if pack is None:
        emit_error(ctx, message=f"pack '{name}' invalid: {err}", exit_code=EXIT_USER_ERROR)
        raise

    from llm_wiki.admin.scaffold import _upsert_env_kv, repo_root

    env_path = repo_root() / ".env"
    base = env_path.read_text(encoding="utf-8") if env_path.is_file() else ""

    if not yes and not octx.json_output:
        confirm = typer.confirm(
            f"Set APP_DOMAIN={name} in {env_path}? Server restart required.",
            default=True,
        )
        if not confirm:
            octx.console.print("[yellow]·[/yellow] aborted")
            raise typer.Exit(code=EXIT_USER_ERROR)

    new_base = _upsert_env_kv(base, "APP_DOMAIN", name)
    try:
        env_path.write_text(new_base, encoding="utf-8")
    except OSError as exc:
        emit_error(ctx, message=f"failed to write {env_path}: {exc}", exit_code=EXIT_USER_ERROR)
        raise

    if octx.json_output:
        emit_json({"ok": True, "activated": name, "env_path": str(env_path)})
        return
    octx.console.print(
        f"[green]✓[/green] APP_DOMAIN={name} written to [bold]{env_path}[/bold]. "
        "Restart the server to pick up the change."
    )
