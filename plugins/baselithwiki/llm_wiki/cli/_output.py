"""Output + exit-code helpers shared by all CLI commands.

Centralised so each subcommand emits either Rich-formatted human output
or machine-readable JSON depending on the global ``--json`` flag, and so
exit codes follow a consistent BSD ``sysexits``-inspired mapping:

- ``0``  — success
- ``1``  — generic failure (logic, validation surfaced post-Typer)
- ``2``  — usage error (Typer also returns this for bad CLI input)
- ``3``  — infrastructure failure (Qdrant/LLM unreachable, FS unwritable)
- ``130`` — interrupted by SIGINT
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

import typer
from rich.console import Console

EXIT_OK = 0
EXIT_USER_ERROR = 1
EXIT_USAGE_ERROR = 2
EXIT_INFRA_ERROR = 3
EXIT_INTERRUPTED = 130


@dataclass
class OutputContext:
    """Per-invocation output state, attached to ``typer.Context.obj``."""

    json_output: bool = False
    verbose: bool = False
    quiet: bool = False
    no_color: bool = False
    console: Console = field(default_factory=Console)


def get_console(*, no_color: bool) -> Console:
    """Build a Rich console honouring ``NO_COLOR`` and the explicit flag."""
    disable = no_color or bool(os.environ.get("NO_COLOR"))
    return Console(no_color=disable, force_terminal=None)


def install_no_color(no_color: bool) -> None:
    """Propagate the no-color choice into ``NO_COLOR`` for downstream libs."""
    if no_color and not os.environ.get("NO_COLOR"):
        os.environ["NO_COLOR"] = "1"


def get_ctx(ctx: typer.Context) -> OutputContext:
    """Return the typed output context, falling back to defaults if missing."""
    obj = ctx.obj
    if isinstance(obj, OutputContext):
        return obj
    return OutputContext(console=get_console(no_color=False))


def emit_json(payload: Any, *, exit_code: int = EXIT_OK) -> None:
    """Print JSON to stdout and raise ``typer.Exit`` with the given code."""
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    sys.stdout.write("\n")
    sys.stdout.flush()
    raise typer.Exit(code=exit_code)


def emit_error(
    ctx: typer.Context,
    *,
    message: str,
    exit_code: int = EXIT_USER_ERROR,
    detail: dict[str, Any] | None = None,
) -> None:
    """Render an error in the active output mode and exit with ``exit_code``."""
    octx = get_ctx(ctx)
    if octx.json_output:
        payload = {"ok": False, "error": message}
        if detail:
            payload.update(detail)
        emit_json(payload, exit_code=exit_code)
    else:
        octx.console.print(f"[red]✗[/red] {message}")
    raise typer.Exit(code=exit_code)
