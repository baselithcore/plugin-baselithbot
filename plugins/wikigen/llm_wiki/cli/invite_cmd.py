"""``wiki-wl invite-superuser`` (e ``invite-user``) — invitation token
emission da CLI.

Pattern allineato a GitHub org invites / Vaultwarden / Authentik:
- Token random 256 bit, hash-only in DB.
- Mostrato UNA volta come URL completo nello stdout.
- Maintainer manda l'URL al destinatario via canale sicuro (PEC,
  Signal, sealed envelope).
- Cliente apre URL → form set password → account creato.

Se ``--base-url`` non è passato, mostra solo il path
``/setup/invite?token=…`` — il maintainer lo prepende all'URL del
proprio deploy.
"""

from __future__ import annotations

import typer
from rich.panel import Panel

from llm_wiki.auth.invitations import InvitationError, create_invitation
from llm_wiki.cli._output import emit_error, emit_json, get_ctx


def invite_superuser_cmd(
    ctx: typer.Context,
    email: str = typer.Argument(..., help="Email del destinatario."),
    display_name: str = typer.Option("", "--display-name", help="Nome visualizzato."),
    tenant_slug: str = typer.Option(
        "", "--tenant-slug", help="Slug tenant (default: derivato dall'email)."
    ),
    note: str = typer.Option("", "--note", help="Annotazione interna (es. 'cliente acme srl')."),
    ttl_hours: int = typer.Option(24, "--ttl-hours", help="Validità in ore (default 24)."),
    base_url: str = typer.Option(
        "",
        "--base-url",
        help=(
            "URL pubblico del deploy (es. 'https://wiki.example.com'). "
            "Se passato, l'output mostra l'URL completo da inviare al "
            "destinatario; altrimenti solo il path relativo."
        ),
    ),
    role: str = typer.Option(
        "superuser",
        "--role",
        help="Slug ruolo system (superuser/admin/moderator/user).",
    ),
) -> None:
    """Emette un invitation token. Stampa l'URL UNA volta — non
    persistito né recuperabile dopo questa esecuzione."""
    output = get_ctx(ctx)
    console = output.console

    try:
        info = create_invitation(
            email=email,
            role_slug=role,
            tenant_slug=tenant_slug or None,
            display_name=display_name,
            note=note,
            ttl_hours=ttl_hours,
        )
    except InvitationError as exc:
        emit_error(ctx, message=str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        emit_error(ctx, message=f"Errore inatteso: {exc}")
        return

    path = f"/setup/invite?token={info['token_plain']}"
    accept_url = f"{base_url.rstrip('/')}{path}" if base_url else path

    if output.json_output:
        emit_json(
            {
                "status": "ok",
                "id": info["id"],
                "email": email,
                "role": role,
                "accept_url": accept_url,
                "expires_at": info["expires_at"],
            }
        )
        return

    console.print(
        Panel.fit(
            f"[bold green]✓[/] invitation emessa\n"
            f"  email:      [bold]{email}[/]\n"
            f"  ruolo:      {role}\n"
            f"  scadenza:   {info['expires_at']}\n\n"
            f"[bold yellow]URL da inviare al destinatario:[/]\n"
            f"  {accept_url}\n\n"
            f"[dim]Token plain mostrato UNA volta. Mai persistito. "
            f"Mai mostrato di nuovo.[/]",
            title="invite",
            border_style="green",
        )
    )
