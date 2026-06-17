"""Localized (en/it) transactional email templates.

Each template is a callable returning ``(subject, text_body, html_body)``.
Kept dependency-free: simple string interpolation, no templating engine.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple

Rendered = Tuple[str, str, str]

_BRAND = "Baselith"


def _wrap_html(
    title: str, intro: str, button_label: str, link: str, footer: str
) -> str:
    """Minimal responsive HTML shell shared by all templates."""
    return f"""\
<!doctype html><html><body style="margin:0;background:#f5f6fa;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1d2433">
  <div style="max-width:480px;margin:0 auto;padding:32px 24px">
    <h1 style="font-size:20px;font-weight:700;margin:0 0 16px">{title}</h1>
    <p style="font-size:14px;line-height:1.6;margin:0 0 24px">{intro}</p>
    <a href="{link}" style="display:inline-block;background:#3b5bdb;color:#fff;text-decoration:none;
       padding:12px 24px;border-radius:8px;font-size:14px;font-weight:600">{button_label}</a>
    <p style="font-size:12px;color:#6b7280;line-height:1.6;margin:24px 0 0">{footer}</p>
    <p style="font-size:12px;color:#9aa1ad;margin:8px 0 0;word-break:break-all">{link}</p>
  </div>
</body></html>"""


def _password_reset(link: str, locale: str) -> Rendered:
    if locale == "it":
        subject = f"{_BRAND} — Reimposta la password"
        intro = (
            "Abbiamo ricevuto una richiesta di reimpostazione della password. "
            "Clicca il pulsante per scegliere una nuova password. Il link scade tra 1 ora."
        )
        return (
            subject,
            f"{intro}\n\n{link}\n\nSe non hai richiesto tu, ignora questa email.",
            _wrap_html(
                "Reimposta la password",
                intro,
                "Reimposta password",
                link,
                "Se non hai richiesto la reimpostazione, ignora questa email.",
            ),
        )
    subject = f"{_BRAND} — Reset your password"
    intro = (
        "We received a request to reset your password. Click the button to choose "
        "a new one. This link expires in 1 hour."
    )
    return (
        subject,
        f"{intro}\n\n{link}\n\nIf you didn't request this, you can ignore this email.",
        _wrap_html(
            "Reset your password",
            intro,
            "Reset password",
            link,
            "If you didn't request a reset, you can safely ignore this email.",
        ),
    )


def _invitation(link: str, locale: str) -> Rendered:
    if locale == "it":
        subject = f"Sei stato invitato su {_BRAND}"
        intro = (
            "Sei stato invitato a unirti alla piattaforma. Clicca il pulsante per "
            "creare il tuo account. L'invito scade tra 7 giorni."
        )
        return (
            subject,
            f"{intro}\n\n{link}",
            _wrap_html(
                "Invito alla piattaforma",
                intro,
                "Accetta invito",
                link,
                "Se non ti aspettavi questo invito, ignora questa email.",
            ),
        )
    subject = f"You've been invited to {_BRAND}"
    intro = (
        "You've been invited to join the platform. Click the button to create your "
        "account. This invitation expires in 7 days."
    )
    return (
        subject,
        f"{intro}\n\n{link}",
        _wrap_html(
            "Platform invitation",
            intro,
            "Accept invitation",
            link,
            "If you weren't expecting this invitation, ignore this email.",
        ),
    )


def _email_verify(link: str, locale: str) -> Rendered:
    if locale == "it":
        subject = f"{_BRAND} — Verifica il tuo indirizzo email"
        intro = "Conferma il tuo indirizzo email per attivare l'account. Il link scade tra 24 ore."
        return (
            subject,
            f"{intro}\n\n{link}",
            _wrap_html(
                "Verifica email",
                intro,
                "Verifica email",
                link,
                "Se non hai creato un account, ignora questa email.",
            ),
        )
    subject = f"{_BRAND} — Verify your email address"
    intro = "Confirm your email address to activate your account. This link expires in 24 hours."
    return (
        subject,
        f"{intro}\n\n{link}",
        _wrap_html(
            "Verify your email",
            intro,
            "Verify email",
            link,
            "If you didn't create an account, ignore this email.",
        ),
    )


TEMPLATES: Dict[str, Callable[[str, str], Rendered]] = {
    "password_reset": _password_reset,
    "invitation": _invitation,
    "email_verify": _email_verify,
}


def render(template: str, link: str, locale: str) -> Rendered:
    """Render a named template into (subject, text, html) for the given locale."""
    fn = TEMPLATES.get(template)
    if fn is None:
        raise KeyError(f"Unknown email template: {template}")
    return fn(link, "it" if str(locale).lower().startswith("it") else "en")
