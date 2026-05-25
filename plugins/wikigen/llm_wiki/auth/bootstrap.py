"""First-boot superuser bootstrap.

Tre vie di accesso, tutte allineate alle best practice 2026:

1. **CLI** (``wiki-wl create-superuser``) — interattivo via
   :mod:`getpass`. Standard Django ``createsuperuser``-like. Nessuna
   credenziale in env / log / file.
2. **Endpoint loopback** (``POST /auth/bootstrap``) — invocato dal
   :mod:`SetupWizard` frontend al primo boot. Gate: loopback only se
   esistono utenti, libero se ``users_count==0``.
3. **Autostart legacy** (:func:`bootstrap_admin_if_empty`, lifespan) —
   abilitato SOLO se ``ADMIN_BOOTSTRAP_AUTOSTART=true`` (deprecato:
   default ``False``). Mantiene back-compat con docker-compose attuali
   che settano ``ADMIN_BOOTSTRAP_PASSWORD``. La password generata
   automaticamente NON è più scritta su file: solo banner stderr
   nel boot log corrente — operatore deve registrarla subito.

Tutti e tre instradano in :func:`create_superuser`, pure function
idempotent: rifiuta email duplicata.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
from pathlib import Path

from llm_wiki import config
from llm_wiki.auth.audit import write_event
from llm_wiki.db.tenants import create_tenant_with_owner
from llm_wiki.db.users import count_users, get_user_by_email, hash_password

logger = logging.getLogger(__name__)


# --- email + password validation ------------------------------------------

# Regex email "buono abbastanza" — RFC-5321 compliant non lo è nessuno
# in pratica. Validazione finale spetta al server SMTP del provider.
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PASSWORD_MIN_LEN = 12


class BootstrapError(Exception):
    """Errore funzionale del bootstrap (email duplicata / validazione /
    DB irraggiungibile). Pensato per essere catturato dal caller (CLI o
    endpoint) e mappato a un exit code o HTTP status appropriato."""


def _validate_email(email: str) -> str:
    cleaned = (email or "").strip().lower()
    if not cleaned:
        raise BootstrapError("Email obbligatoria.")
    if not _EMAIL_RE.match(cleaned):
        raise BootstrapError(f"Email non valida: {cleaned!r}.")
    return cleaned


def _validate_password(password: str) -> None:
    if not password or len(password) < PASSWORD_MIN_LEN:
        raise BootstrapError(f"Password deve essere di almeno {PASSWORD_MIN_LEN} caratteri.")


# --- core: pure function ---------------------------------------------------


def create_superuser(
    email: str,
    password: str,
    *,
    display_name: str = "",
    tenant_slug: str | None = None,
    tenant_name: str | None = None,
    source: str = "cli",
    must_change_password: bool = False,
) -> dict:
    """Crea tenant + user + assegna ruolo system ``superuser``.

    Idempotent rispetto all'email: rifiuta con :class:`BootstrapError`
    se esiste già un utente con quella email.

    Parametri::

        email          : richiesto, validato regex.
        password       : richiesta, min PASSWORD_MIN_LEN.
        display_name   : default "" (settabile via UI dopo).
        tenant_slug    : default ``slug(email)`` (es. "admin@x.com" → "admin-x-com").
                         Univoco per tenant.
        tenant_name    : default "<email> Workspace".
        source         : tag audit ("cli" / "web" / "lifespan-autostart").

    Ritorna ``{"user_id": str, "tenant_id": str, "email": str}``.
    Solleva :class:`BootstrapError` per errori funzionali, propaga le
    exception DB per errori sistemici (caller decide se loggare).
    """
    if not config.POSTGRES_ENABLED:
        raise BootstrapError("Postgres disabilitato — bootstrap impossibile.")

    email = _validate_email(email)
    _validate_password(password)

    # Email duplicate pre-check. Race con INSERT concorrente: se un
    # secondo bootstrap parte tra qui e l'INSERT, l'UNIQUE constraint
    # solleva → propaghiamo come BootstrapError.
    if get_user_by_email(email):
        raise BootstrapError(f"Utente con email {email!r} esiste già.")

    if not tenant_slug:
        tenant_slug = re.sub(r"[^a-z0-9-]+", "-", email).strip("-")[:50] or "admin"
    if not tenant_name:
        tenant_name = f"{email} Workspace"

    try:
        result = create_tenant_with_owner(
            tenant_name=tenant_name,
            tenant_slug=tenant_slug,
            user_email=email,
            user_password_hash=hash_password(password),
            user_display_name=display_name.strip() or email.split("@")[0],
            plan="enterprise",
            role="admin",  # legacy column (CHECK 'admin'/'user')
        )
    except Exception as exc:
        # Mappa i conflict UNIQUE (email/slug) a BootstrapError leggibile.
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            raise BootstrapError(
                "Conflitto: email o slug tenant già usati. Specifica un --tenant-slug diverso."
            ) from exc
        raise

    user_id = str(result["user"]["id"])
    tenant_id = str(result["tenant"]["id"])

    # Force password change baseline (009): se richiesto dal caller
    # (bootstrap autostart con password generata, password reset
    # admin-driven), setta il flag. L'utente sarà costretto a cambiare
    # password al primo login.
    if must_change_password:
        try:
            from llm_wiki.db.users import set_password_must_change

            set_password_must_change(user_id, True)
        except Exception as exc:
            logger.warning("[bootstrap] set_password_must_change failed: %s", exc)

    # RBAC (008): assegna ruolo system superuser.
    try:
        from llm_wiki.db.roles import assign_role_to_user, list_roles

        superuser = next(
            (r for r in list_roles() if r["slug"] == "superuser" and r["is_system"]),
            None,
        )
        if superuser:
            assign_role_to_user(user_id, superuser["id"])
        else:
            logger.warning(
                "[bootstrap] system role 'superuser' assente "
                "(migration 008 non applicata?) — utente creato ma senza RBAC"
            )
    except Exception as exc:
        logger.warning("[bootstrap] superuser role assignment failed: %s", exc)

    write_event(
        "admin.bootstrap",
        tenant_id=tenant_id,
        user_id=user_id,
        payload={
            "email": email,
            "tenant_slug": tenant_slug,
            "source": source,
        },
    )
    logger.info("[bootstrap] superuser created (source=%s): %s", source, email)
    return {"user_id": user_id, "tenant_id": tenant_id, "email": email}


# --- legacy lifespan autostart --------------------------------------------


def bootstrap_admin_if_empty(*, vault_root: Path) -> None:
    """Lifespan autostart legacy. Disabilitato di default da 008+.

    Abilitabile solo se ``ADMIN_BOOTSTRAP_AUTOSTART=true``. Sostituito
    da :func:`create_superuser` invocato via CLI o endpoint web. Tenuto
    qui per back-compat docker-compose esistenti.
    """
    if not config.POSTGRES_ENABLED:
        logger.info("[bootstrap] Postgres disabilitato — skip admin bootstrap")
        return

    if not getattr(config, "ADMIN_BOOTSTRAP_AUTOSTART", False):
        logger.debug(
            "[bootstrap] autostart disabilitato (ADMIN_BOOTSTRAP_AUTOSTART=false) "
            "— usa `wiki-wl create-superuser` o il setup wizard"
        )
        return

    try:
        existing = count_users()
    except Exception as exc:
        logger.error("[bootstrap] count_users fallito (DB non pronto?): %s — skip", exc)
        return

    if existing > 0:
        logger.debug("[bootstrap] users=%d, skip admin creation", existing)
        return

    email = (config.ADMIN_BOOTSTRAP_EMAIL or "admin@local").strip().lower()
    password = (config.ADMIN_BOOTSTRAP_PASSWORD or "").strip()
    generated = False
    if not password:
        password = secrets.token_urlsafe(24)
        generated = True

    try:
        create_superuser(
            email=email,
            password=password,
            display_name="Admin",
            tenant_slug="admin",
            tenant_name="Admin Workspace",
            source="lifespan-autostart",
            must_change_password=generated,
        )
    except BootstrapError as exc:
        logger.error("[bootstrap] %s", exc)
        return
    except Exception as exc:
        logger.error("[bootstrap] admin creation failed: %s", exc)
        return

    if generated:
        _emit_generated_password_notice(email=email, password=password, vault_root=vault_root)


def _emit_generated_password_notice(*, email: str, password: str, vault_root: Path) -> None:
    """Stampa banner stderr + dump file 0600. UNA sola volta, prima
    della prima richiesta. Output non torna in audit (mai loggare
    password in chiaro nel DB)."""
    logs_dir = vault_root / "logs"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback: cwd. Mai bloccare il boot per logging.
        logs_dir = Path.cwd()

    target = logs_dir / "bootstrap_admin.txt"
    try:
        target.write_text(
            f"email={email}\npassword={password}\n",
            encoding="utf-8",
        )
        os.chmod(target, 0o600)
    except Exception as exc:
        logger.warning("[bootstrap] cannot write %s: %s", target, exc)

    banner = (
        "\n"
        + "═" * 72
        + "\n"
        + " ⚠  ADMIN BOOTSTRAP — PASSWORD GENERATA, RUOTA SUBITO  ⚠\n"
        + "═" * 72
        + "\n"
        + f"  email:    {email}\n"
        + f"  password: {password}\n"
        + f"  file:     {target}  (perm 0600)\n"
        + "  azioni:   1) login → /auth/me\n"
        + "            2) cambia password → POST /auth/password\n"
        + "            3) elimina file: shred -u <path>\n"
        + "═" * 72
        + "\n"
    )
    # Stampa diretta a stderr — `print` cattura il banner anche con
    # logging configurato a WARNING.
    import sys

    print(banner, file=sys.stderr, flush=True)


__all__ = ["bootstrap_admin_if_empty"]
