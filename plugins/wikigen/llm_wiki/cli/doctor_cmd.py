"""``wiki-wl doctor`` — pre-flight health check.

Runs five independent checks:

1. **pack**       — active Domain Pack loads through the registry.
2. **vault**      — ``WIKI_ROOT`` exists, is writable, has ``wiki/``.
3. **env**        — no shell-exported variable shadows ``.env`` values.
4. **qdrant**     — vector store is reachable (HTTP for server mode,
   filesystem for embedded).
5. **llm**        — configured provider responds to a tiny ``/api/tags``
   (Ollama) or ``/v1/models`` (OpenAI) probe.

Each check returns a status of ``ok`` | ``warn`` | ``fail``. Overall exit
code is 0 if every check is at least ``warn``-level (i.e. nothing
``fail``); otherwise 3 (infrastructure error). ``--strict`` upgrades
warnings to failures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import typer
from rich.table import Table

from llm_wiki.cli._output import (
    EXIT_INFRA_ERROR,
    EXIT_OK,
    emit_json,
    get_ctx,
)

CheckStatus = Literal["ok", "warn", "fail", "skip"]


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    detail: str
    extra: dict[str, str] = field(default_factory=dict)


def doctor(
    ctx: typer.Context,
    strict: bool = typer.Option(
        False, "--strict", help="Treat warnings as failures (exit non-zero)."
    ),
    timeout: float = typer.Option(
        3.0, "--timeout", min=0.5, max=60.0, help="Network probe timeout in seconds."
    ),
) -> None:
    """Run pre-flight health checks against the active configuration."""
    octx = get_ctx(ctx)

    checks: list[CheckResult] = [
        _check_pack(),
        _check_vault(),
        _check_env_overrides(),
        _check_qdrant(timeout=timeout),
        _check_llm(timeout=timeout),
    ]

    failed = any(c.status == "fail" for c in checks)
    warned = any(c.status == "warn" for c in checks)
    overall_ok = not failed and (not strict or not warned)
    exit_code = EXIT_OK if overall_ok else EXIT_INFRA_ERROR

    if octx.json_output:
        emit_json(
            {
                "ok": overall_ok,
                "strict": strict,
                "checks": [
                    {"name": c.name, "status": c.status, "detail": c.detail, **c.extra}
                    for c in checks
                ],
            },
            exit_code=exit_code,
        )
        return

    icon = {
        "ok": "[green]✓[/green]",
        "warn": "[yellow]·[/yellow]",
        "fail": "[red]✗[/red]",
        "skip": "[dim]-[/dim]",
    }
    t = Table(title="wiki-wl doctor")
    t.add_column("check", style="cyan")
    t.add_column("status")
    t.add_column("detail", style="white")
    for c in checks:
        t.add_row(c.name, icon[c.status], c.detail)
    octx.console.print(t)

    if exit_code != EXIT_OK:
        octx.console.print(
            f"[red]✗[/red] {sum(1 for c in checks if c.status == 'fail')} failure(s)"
            + (
                f", {sum(1 for c in checks if c.status == 'warn')} warning(s)"
                if warned
                else ""
            )
        )
        raise typer.Exit(code=exit_code)
    octx.console.print("[green]✓[/green] all checks passed")


def _check_pack() -> CheckResult:
    from llm_wiki import config

    if not config.APP_DOMAIN:
        return CheckResult("pack", "warn", "APP_DOMAIN unset — engine in setup mode")
    try:
        from llm_wiki.domain.registry import load_pack

        pack = load_pack()
    except Exception as exc:
        return CheckResult("pack", "fail", f"load failed: {exc}")
    return CheckResult(
        "pack",
        "ok",
        f"{pack.name} ({pack.label}, {len(pack.page_types)} page types)",
    )


def _check_vault() -> CheckResult:
    from llm_wiki import config

    root = Path(config.WIKI_ROOT)
    if not root.exists():
        return CheckResult("vault", "fail", f"{root} does not exist")
    if not root.is_dir():
        return CheckResult("vault", "fail", f"{root} is not a directory")
    probe = root / ".doctor_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return CheckResult("vault", "fail", f"{root} not writable: {exc}")
    if not (root / "wiki").is_dir():
        return CheckResult(
            "vault", "warn", f"{root}/wiki/ missing — run wizard or scaffold first"
        )
    return CheckResult("vault", "ok", f"{root} writable, wiki/ present")


def _check_env_overrides() -> CheckResult:
    from llm_wiki.admin.scaffold import repo_root
    from llm_wiki.cli.status_cmd import _detect_env_overrides

    env_path = repo_root() / ".env"
    if not env_path.is_file():
        return CheckResult("env", "warn", f"no .env at {env_path}")
    overrides = _detect_env_overrides(env_path)
    if overrides:
        return CheckResult(
            "env",
            "warn",
            f"shell-exported overrides: {', '.join(overrides)}",
            extra={"overrides": ",".join(overrides)},
        )
    return CheckResult("env", "ok", "no shell overrides")


def _check_qdrant(*, timeout: float) -> CheckResult:
    from llm_wiki import config

    if config.QDRANT_MODE == "embedded":
        path = Path(config.QDRANT_PATH)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return CheckResult("qdrant", "fail", f"{path} unwritable: {exc}")
        return CheckResult("qdrant", "ok", f"embedded → {path}")

    try:
        import httpx
    except ImportError:
        return CheckResult("qdrant", "skip", "httpx not installed")
    url = f"{config.QDRANT_URL.rstrip('/')}/collections"
    try:
        resp = httpx.get(url, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        return CheckResult("qdrant", "fail", f"{url} unreachable: {exc}")
    return CheckResult("qdrant", "ok", f"{config.QDRANT_URL} reachable")


def _check_llm(*, timeout: float) -> CheckResult:
    from llm_wiki import config

    try:
        import httpx
    except ImportError:
        return CheckResult("llm", "skip", "httpx not installed")

    if config.LLM_VENDOR == "ollama":
        url = f"{config.OLLAMA_URL.rstrip('/')}/api/tags"
        try:
            resp = httpx.get(url, timeout=timeout)
            resp.raise_for_status()
        except Exception as exc:
            return CheckResult("llm", "fail", f"{url} unreachable: {exc}")
        try:
            tags = resp.json().get("models", [])
            names = {m.get("name") or m.get("model") for m in tags}
            present = config.OLLAMA_MODEL in names
        except Exception:
            present = False
        if not present:
            return CheckResult(
                "llm",
                "warn",
                f"{config.OLLAMA_URL} up but model '{config.OLLAMA_MODEL}' not pulled",
            )
        return CheckResult(
            "llm", "ok", f"ollama @ {config.OLLAMA_URL} ({config.OLLAMA_MODEL} present)"
        )

    if config.LLM_VENDOR == "openai":
        if not config.OPENAI_API_KEY:
            return CheckResult("llm", "fail", "OPENAI_API_KEY missing")
        url = f"{config.OPENAI_API_BASE.rstrip('/')}/models"
        try:
            resp = httpx.get(
                url,
                timeout=timeout,
                headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            )
            resp.raise_for_status()
        except Exception as exc:
            return CheckResult("llm", "fail", f"{url} unreachable: {exc}")
        return CheckResult("llm", "ok", f"openai @ {config.OPENAI_API_BASE}")

    return CheckResult("llm", "warn", f"unknown vendor: {config.LLM_VENDOR}")
