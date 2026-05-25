"""``wiki-wl create-superuser`` — interactive bootstrap.

Pattern Django ``createsuperuser``-like: prompt email + password
(con conferma), nessun env var, password mai loggata. Supporta anche
flag non-interattivi per CI / docker entrypoint, ma il flusso primario
è interattivo.

Esempi
======

Interattivo::

    $ wiki-wl create-superuser
    email: admin@example.com
    password: ********
    confirm: ********
    ✓ superuser admin@example.com created (tenant: admin-example-com)

Non interattivo (CI / docker entrypoint)::

    $ wiki-wl create-superuser --email admin@x.com --password "$ADMIN_PWD"

Idempotenza
===========

Se ``users`` non è vuota e l'email passata coincide con un utente
esistente → exit 1 con messaggio chiaro. Per aggiungere ulteriori
superuser usare ``--add`` (richiede confermare email/password
distinti). Non sovrascrive mai utenti esistenti.
"""

from __future__ import annotations

import getpass
import sys

import typer
from rich.panel import Panel

from llm_wiki.auth.bootstrap import (
    PASSWORD_MIN_LEN,
    BootstrapError,
    create_superuser,
)
from llm_wiki.cli._output import (
    EXIT_USAGE_ERROR,
    emit_error,
    emit_json,
    get_ctx,
)


def _prompt_email(default: str | None) -> str:
    while True:
        prompt = f"email [{default}]: " if default else "email: "
        raw = input(prompt).strip()
        value = raw or (default or "")
        if value:
            return value
        sys.stderr.write("Email obbligatoria.\n")


def _prompt_password() -> str:
    while True:
        pw = getpass.getpass(f"password (min {PASSWORD_MIN_LEN} char): ")
        if len(pw) < PASSWORD_MIN_LEN:
            sys.stderr.write(f"Password troppo corta ({len(pw)} < {PASSWORD_MIN_LEN}).\n")
            continue
        confirm = getpass.getpass("confirm: ")
        if pw != confirm:
            sys.stderr.write("Password non coincidono. Riprova.\n")
            continue
        return pw


def create_superuser_cmd(
    ctx: typer.Context,
    email: str = typer.Option("", "--email", "-e", help="Email superuser."),
    password: str = typer.Option(
        "",
        "--password",
        "-p",
        help=(
            "Password (sconsigliato passarla via flag — usa il prompt "
            "interattivo o lo stdin per evitare leak nello shell history)."
        ),
    ),
    display_name: str = typer.Option("", "--display-name", help="Nome visualizzato."),
    tenant_slug: str = typer.Option(
        "", "--tenant-slug", help="Slug tenant (default: derivato dall'email)."
    ),
    add: bool = typer.Option(
        False,
        "--add",
        help=(
            "Aggiungi un ulteriore superuser anche se utenti esistono. "
            "Richiede email distinta — non promuove utenti esistenti."
        ),
    ),
    read_password_stdin: bool = typer.Option(
        False,
        "--password-stdin",
        help="Leggi la password da stdin (newline-terminated). Comodo per CI.",
    ),
) -> None:
    """Crea un superuser. Prompt interattivo se email/password non passati."""
    output = get_ctx(ctx)
    console = output.console

    # Resolve email
    if not email:
        if not sys.stdin.isatty():
            emit_error(
                ctx,
                message="--email è obbligatorio in modalità non interattiva.",
                exit_code=EXIT_USAGE_ERROR,
            )
        email = _prompt_email(default=None)

    # Resolve password
    if read_password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    if not password:
        if not sys.stdin.isatty():
            emit_error(
                ctx,
                message="--password (o --password-stdin) obbligatorio in modalità non interattiva.",
                exit_code=EXIT_USAGE_ERROR,
            )
        password = _prompt_password()

    # Pre-flight: bail out if "first-boot" semantics violated and --add
    # not specified. Lasciamo che ``create_superuser`` faccia comunque la
    # email-uniqueness check via DB; questo è solo per UX nel caso "ti
    # sei dimenticato di passare --add".
    try:
        from llm_wiki.db.users import count_users

        existing = count_users()
    except Exception as exc:
        emit_error(ctx, message=f"DB irraggiungibile: {exc}")
        return

    if existing > 0 and not add:
        emit_error(
            ctx,
            message=(
                f"Esistono già {existing} utenti nel DB. Per creare un "
                "ulteriore superuser usa `--add`. Per resettare il DB usa "
                "`alembic downgrade base && alembic upgrade head`."
            ),
        )
        return

    # Run
    try:
        info = create_superuser(
            email=email,
            password=password,
            display_name=display_name,
            tenant_slug=tenant_slug or None,
            source="cli",
        )
    except BootstrapError as exc:
        emit_error(ctx, message=str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        emit_error(ctx, message=f"Errore inatteso: {exc}")
        return

    if output.json_output:
        emit_json({"status": "ok", **info})
        return

    console.print(
        Panel.fit(
            f"[bold green]✓[/] superuser creato\n"
            f"  email:   [bold]{info['email']}[/]\n"
            f"  user_id: {info['user_id']}\n"
            f"  tenant:  {info['tenant_id']}",
            title="bootstrap",
            border_style="green",
        )
    )
