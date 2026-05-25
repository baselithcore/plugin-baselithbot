"""``wiki-wl status`` — diagnostic view of pack + provider + vector store."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.table import Table

from llm_wiki.cli._output import (
    EXIT_USER_ERROR,
    emit_error,
    emit_json,
    get_ctx,
)
from llm_wiki.cli._version import resolve_version


def status(ctx: typer.Context) -> None:
    """Show active configuration and system health."""
    from llm_wiki import config
    from llm_wiki.admin.scaffold import repo_root
    from llm_wiki.domain.registry import load_pack

    octx = get_ctx(ctx)
    setup_mode = not bool(config.APP_DOMAIN)
    env_path = repo_root() / ".env"
    env_exists = env_path.is_file()

    if setup_mode:
        if octx.json_output:
            emit_json(
                {
                    "ok": True,
                    "setup_mode": True,
                    "version": resolve_version(),
                    "env_path": str(env_path) if env_exists else None,
                    "vault_root": str(config.WIKI_ROOT),
                    "llm": {"vendor": config.LLM_VENDOR},
                }
            )
            return
        octx.console.print(
            "[yellow]·[/yellow] Engine in setup mode — APP_DOMAIN not set. "
            "Run [cyan]wiki-wl init --domain <name>[/cyan] or use the wizard."
        )
        return

    try:
        pack = load_pack()
    except Exception as exc:
        emit_error(ctx, message=f"pack load failed: {exc}", exit_code=EXIT_USER_ERROR)
        raise

    qdrant_endpoint = (
        str(config.QDRANT_PATH) if config.QDRANT_MODE == "embedded" else config.QDRANT_URL
    )
    if octx.json_output:
        emit_json(
            {
                "ok": True,
                "setup_mode": False,
                "version": resolve_version(),
                "domain": pack.name,
                "label": pack.label,
                "language": pack.language,
                "page_types": [pt.id for pt in pack.page_types],
                "grouping_rules": [r.key for r in pack.grouping],
                "vault_root": str(config.WIKI_ROOT),
                "env_path": str(env_path) if env_exists else None,
                "qdrant": {
                    "mode": config.QDRANT_MODE,
                    "endpoint": qdrant_endpoint,
                    "collection": config.COLLECTION_NAME,
                },
                "llm": {
                    "vendor": config.LLM_VENDOR,
                    "model": (
                        config.OPENAI_MODEL
                        if config.LLM_VENDOR == "openai"
                        else config.OLLAMA_MODEL
                    ),
                },
                "embedder": config.EMBEDDER_MODEL,
                "graph_enabled": config.GRAPH_DB_ENABLED,
                "shell_env_overrides": _detect_env_overrides(env_path),
            }
        )
        return

    config.print_banner()
    t = Table(title=f"Wiki White-Label — Status (v{resolve_version()})")
    t.add_column("component", style="cyan")
    t.add_column("value", style="white")

    t.add_row("Domain", f"{pack.name}  ({pack.label})")
    t.add_row("Language", pack.language)
    t.add_row("Page types", ", ".join(pt.id for pt in pack.page_types))
    t.add_row("Grouping rules", ", ".join(r.key for r in pack.grouping) or "(none)")
    t.add_row("Vault root", str(config.WIKI_ROOT))
    t.add_row("Qdrant", f"{config.QDRANT_MODE} → {qdrant_endpoint} / {config.COLLECTION_NAME}")
    t.add_row("LLM vendor", config.LLM_VENDOR)
    t.add_row("Embedder", config.EMBEDDER_MODEL)
    t.add_row("Graph DB", "on" if config.GRAPH_DB_ENABLED else "off")
    t.add_row(".env", str(env_path) if env_exists else "(not present)")

    octx.console.print(t)

    overrides = _detect_env_overrides(env_path)
    if overrides:
        octx.console.print(
            "[yellow]![/yellow] Shell-exported variables override .env: " + ", ".join(overrides)
        )


def _detect_env_overrides(env_path: Path) -> list[str]:
    """Return the keys whose process env value differs from the .env file."""
    if not env_path.is_file():
        return []
    watched = ("APP_DOMAIN", "WIKI_ROOT", "LLM_VENDOR", "OLLAMA_MODEL", "OPENAI_MODEL")
    overrides: list[str] = []
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return []
    file_values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        file_values[k.strip()] = v.strip().strip('"').strip("'")
    for key in watched:
        file_v = file_values.get(key)
        env_v = os.environ.get(key)
        if file_v is not None and env_v is not None and file_v != env_v:
            overrides.append(key)
    return overrides
