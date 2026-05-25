"""CLI entry point for the white-label wiki engine.

Commands:

- ``wiki-wl init --domain <name>``     scaffold a new Domain Pack from
  the ``_template`` skeleton. Single command from clone → running wiki.
- ``wiki-wl status``                   diagnostic view of the active pack
  + provider + vector store + vault.
- ``wiki-wl doctor``                   pre-flight health check (pack /
  vault / qdrant / llm / env conflicts).
- ``wiki-wl serve``                    start the FastAPI server.
- ``wiki-wl ingest <file>``            pipeline a single PDF.
- ``wiki-wl pack list|show|validate|activate`` manage installed Domain Packs.

Globals (any command):

- ``--version / -V``    print engine version and exit
- ``--verbose / -v``    DEBUG logging
- ``--quiet / -q``      ERROR-only logging
- ``--log-level``       explicit override (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- ``--log-format``      ``text`` (default) or ``json``
- ``--json``            emit machine-readable JSON to stdout (where supported)
- ``--no-color``        disable Rich colours (also honours ``NO_COLOR``)

Heavy dependencies (qdrant, sentence-transformers, docling) are NEVER
imported at module load so ``--help``/``--version`` stay sub-100ms and
``init`` works on a bare clone.
"""

from __future__ import annotations

import os
import sys

import typer

from llm_wiki.cli._logging import configure_logging
from llm_wiki.cli._output import (
    EXIT_INTERRUPTED,
    OutputContext,
    get_console,
    install_no_color,
)
from llm_wiki.cli._version import resolve_version
from llm_wiki.cli.doctor_cmd import doctor
from llm_wiki.cli.evals_cmd import evals_app
from llm_wiki.cli.graph_cmd import graph_app
from llm_wiki.cli.ingest_cmd import ingest
from llm_wiki.cli.init_cmd import init
from llm_wiki.cli.invite_cmd import invite_superuser_cmd
from llm_wiki.cli.pack_cmd import pack_app
from llm_wiki.cli.questions_cmd import questions_app
from llm_wiki.cli.serve_cmd import serve
from llm_wiki.cli.status_cmd import status
from llm_wiki.cli.superuser_cmd import create_superuser_cmd

EPILOG = """
Esempi:

  wiki-wl init --domain legal --label "Wiki Legale"
  wiki-wl status --json
  wiki-wl doctor --strict
  wiki-wl pack list
  wiki-wl pack activate legal
  wiki-wl serve --reload
"""

app = typer.Typer(
    help="White-label LLM Wiki CLI — multi-tenant RAG engine.",
    no_args_is_help=True,
    epilog=EPILOG,
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_show_locals=False,
    add_completion=True,
)
app.add_typer(pack_app, name="pack")
app.add_typer(evals_app, name="evals")
app.add_typer(graph_app, name="graph")
app.add_typer(questions_app, name="questions")
app.command(name="init")(init)
app.command(name="status")(status)
app.command(name="serve")(serve)
app.command(name="ingest")(ingest)
app.command(name="doctor")(doctor)
app.command(name="create-superuser")(create_superuser_cmd)
app.command(name="invite")(invite_superuser_cmd)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(resolve_version())
        raise typer.Exit(code=0)


@app.callback()
def _main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="DEBUG logging."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="ERROR-only logging."),
    log_level: str = typer.Option(
        "",
        "--log-level",
        help="Override log level (DEBUG/INFO/WARNING/ERROR/CRITICAL).",
    ),
    log_format: str = typer.Option(
        "text", "--log-format", help="Log format: text|json."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON to stdout (where supported)."
    ),
    no_color: bool = typer.Option(
        False, "--no-color", help="Disable Rich colours (also honours NO_COLOR env)."
    ),
    version: bool = typer.Option(
        None,
        "--version",
        "-V",
        help="Print engine version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    if verbose:
        level = "DEBUG"
    elif log_level:
        level = log_level.upper()
    elif quiet:
        level = "ERROR"
    else:
        level = "INFO"
    configure_logging(level=level, fmt=log_format)
    install_no_color(no_color)
    ctx.obj = OutputContext(
        json_output=json_output,
        verbose=verbose,
        quiet=quiet,
        no_color=no_color or bool(os.environ.get("NO_COLOR")),
        console=get_console(no_color=no_color),
    )


def main() -> int:
    """Console entry point with structured exit-code handling.

    Translates ``KeyboardInterrupt`` to exit 130 and any uncaught
    exception to exit 2 with a one-line stderr message — keeps the
    operator UX sane in CI logs.
    """
    try:
        app()
    except KeyboardInterrupt:
        sys.stderr.write("\n[wiki] interrupted\n")
        return EXIT_INTERRUPTED
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 0
    except Exception as exc:  # noqa: BLE001 — top-level catch-all on purpose
        sys.stderr.write(f"\n[wiki] fatal: {exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
