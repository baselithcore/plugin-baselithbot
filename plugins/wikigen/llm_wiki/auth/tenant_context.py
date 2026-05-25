"""Tenant context per la richiesta corrente (Fase 1 — minimo).

Solo il :class:`contextvars.ContextVar` + helpers sincroni. Il middleware
HTTP che lo popola arriva in Fase 2 portando ``TenantMiddleware`` da
``agent-jira`` (verifica anti-tampering JWT↔DB).

Pattern: il pool DB in ``llm_wiki/db/connection.py`` legge il contextvar
ad ogni ``getconn()`` e setta ``app.current_tenant_id`` (GUC sessione)
così le policy RLS della migration 006 filtrano per tenant in modo
trasparente — niente ``WHERE tenant_id = ...`` sparso nei moduli CRUD.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass


@dataclass(frozen=True)
class TenantInfo:
    """Identità del tenant corrente. ``slug`` e ``plan`` opzionali —
    popolati dal middleware quando disponibili (cache)."""

    tenant_id: str
    slug: str | None = None
    plan: str | None = None


_tenant_context: contextvars.ContextVar[TenantInfo | None] = contextvars.ContextVar(
    "tenant_info", default=None
)


def get_current_tenant() -> TenantInfo | None:
    return _tenant_context.get()


def get_current_tenant_id() -> str | None:
    tenant = _tenant_context.get()
    return tenant.tenant_id if tenant else None


def set_current_tenant(tenant: TenantInfo | None) -> contextvars.Token:
    """Imposta il tenant nel context. Ritorna il token per ``reset()``."""
    return _tenant_context.set(tenant)


def reset_tenant(token: contextvars.Token) -> None:
    _tenant_context.reset(token)


def require_tenant_id() -> str:
    """Solleva ``RuntimeError`` se il tenant non è stato impostato.

    Usalo nei punti dove il tenant è strutturalmente obbligatorio (CRUD
    su tabelle scoped). Per gli endpoint pubblici (wiki shared, status)
    usa :func:`get_current_tenant_id` che restituisce ``None``.
    """
    tenant = _tenant_context.get()
    if tenant is None:
        raise RuntimeError(
            "Tenant context non inizializzato — chiamata fuori da una richiesta autenticata?"
        )
    return tenant.tenant_id


__all__ = [
    "TenantInfo",
    "get_current_tenant",
    "get_current_tenant_id",
    "set_current_tenant",
    "reset_tenant",
    "require_tenant_id",
]
