"""FastAPI dependencies per autenticazione + autorizzazione.

Triade canonica:

- :func:`get_current_user` — restituisce il dict user (o None) — usalo
  quando l'auth è opzionale (rotte che cambiano comportamento se loggato
  ma funzionano anche anonimi).
- :func:`require_user` — solleva 401 se non autenticato. Default per
  rotte chat/conversations/memories/feedback.
- :func:`require_admin` — solleva 403 se non admin. Default per setup
  wizard, scaffold, tenant management.

Tutte e tre fanno ANCHE rate-limiting per identifier (user_id se
loggato, ip altrimenti) — un solo posto, garantito on-path.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, status

from llm_wiki import config
from llm_wiki.auth.rate_limit import RateLimitExceeded, rate_limiter
from llm_wiki.auth.tokens import decode_access_token

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    """IP client real-aware (X-Forwarded-For dietro proxy)."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "-"


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token or None
    return None


def _resolve_user(request: Request) -> dict[str, Any] | None:
    """JWT → user dict. None se token assente/invalido/utente disattivo."""
    token = _extract_bearer(request)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub") or payload.get("uid")
    if not user_id:
        return None

    # Lazy import: evita ciclo db ↔ auth in casi sentry/test.
    try:
        from llm_wiki.db.users import get_user_by_id

        user = get_user_by_id(str(user_id))
    except Exception as exc:
        logger.warning("[auth] user lookup failed: %s", exc)
        return None

    if not user or not user.get("is_active"):
        return None

    # Coerenza JWT↔DB già verificata dal TenantMiddleware. Qui ci
    # fidiamo del payload + lookup user. Aggiungiamo `role_from_jwt`
    # nel caso il chiamante voglia distinguere "ruolo al login" vs
    # "ruolo attuale" (escalation rilevabile).
    user = dict(user)
    user["_token_role"] = payload.get("role")

    # RBAC: permessi e domain grants risolti al volo dal DB.
    # Niente claim JWT per evitare bloat e tenere i permessi freschi
    # quando un admin modifica i ruoli (no attesa expiry token).
    #
    # Per-wiki scoping (008+): se ``APP_DOMAIN`` è settato — i.e. il
    # processo serve una wiki specifica — i permessi effettivi sono
    # l'unione di global user_roles + user_domain_grants per quel
    # dominio. Senza APP_DOMAIN (setup mode / admin tools cross-wiki)
    # restituiamo i soli global perms.
    try:
        from llm_wiki.db.roles import (
            get_user_domain_grants,
            get_user_permissions,
            get_user_roles,
        )

        active_domain = (config.APP_DOMAIN or "").strip() or None
        user["perms"] = get_user_permissions(str(user["id"]), domain_slug=active_domain)
        user["roles"] = [r["slug"] for r in get_user_roles(str(user["id"]))]
        user["domains"] = get_user_domain_grants(str(user["id"]))
        user["active_domain"] = active_domain
    except Exception as exc:
        logger.warning("[auth] RBAC lookup failed (fallback role-only): %s", exc)
        legacy_role = user.get("role")
        user["perms"] = []
        user["roles"] = [legacy_role] if legacy_role else []
        user["domains"] = []
        user["active_domain"] = None
    return user


def _enforce_rate_limit(
    request: Request, user: dict[str, Any] | None, limit_per_minute: int
) -> None:
    if limit_per_minute <= 0:
        return
    identifier = f"user:{user['id']}" if user else f"ip:{_client_ip(request)}"
    try:
        rate_limiter.check(identifier, limit_per_minute, config.RATE_LIMIT_WINDOW_SECONDS)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit superato, riprova tra pochi secondi.",
        ) from exc


# --- public dependencies ---------------------------------------------------


def get_current_user(request: Request) -> dict[str, Any] | None:
    """Auth opzionale. Restituisce ``None`` se anonimo."""
    user = _resolve_user(request)
    _enforce_rate_limit(request, user, config.RATE_LIMIT_USER_PER_MINUTE)
    return user


def require_user(request: Request) -> dict[str, Any]:
    """Auth obbligatoria quando ``AUTH_REQUIRED=true``. 401 altrimenti.

    Dev mode (``AUTH_REQUIRED=false``): il chiamante deve trattare
    l'auth come opzionale e usare :func:`get_current_user` invece —
    questa funzione solleva sempre 401 per anonimi così le rotte
    "richiedono utente" restano coerenti.
    """
    user = _resolve_user(request)
    _enforce_rate_limit(request, user, config.RATE_LIMIT_USER_PER_MINUTE)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticazione richiesta.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(request: Request) -> dict[str, Any]:
    """403 se non admin. Usato per scaffold/wizard/tenant mgmt.

    Back-compat con i route handler esistenti (Fase 1+). I nuovi
    handler dovrebbero usare :func:`require_permission` con il permesso
    granulare richiesto. ``role == 'admin'`` (legacy column) **o**
    presenza del ruolo system ``admin`` (RBAC nuovo) passano entrambi.
    """
    user = _resolve_user(request)
    _enforce_rate_limit(request, user, config.RATE_LIMIT_ADMIN_PER_MINUTE)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticazione richiesta.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_roles = user.get("roles") or []
    # Back-compat con la colonna legacy ``users.role`` (CHECK 'admin'/'user'),
    # E con la gerarchia 008: superuser è il vero "all-access". Manteniamo
    # `admin` come accettato per non rompere route che non sono ancora
    # passate a `require_permission` granulare.
    is_admin = user.get("role") == "admin" or "superuser" in user_roles or "admin" in user_roles
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permessi admin richiesti.",
        )
    if user.get("password_must_change"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cambio password obbligatorio prima di proseguire.",
            headers={"X-Password-Must-Change": "true"},
        )
    return user


def require_permission(
    *perms: str,
    mode: str = "any",
    rate_limit: str = "user",
) -> Callable[[Request], dict[str, Any]]:
    """Dependency factory: 403 se l'utente non ha i permessi richiesti.

    ``mode='any'`` (default): basta UNO dei permessi. ``mode='all'``:
    richiede tutti.

    ``rate_limit='user'`` (default) → ``RATE_LIMIT_USER_PER_MINUTE``.
    ``rate_limit='admin'`` → ``RATE_LIMIT_ADMIN_PER_MINUTE``. Endpoint
    sotto ``/api/admin/*`` (RBAC management, scaffold, runtime ops)
    devono passare ``rate_limit='admin'`` per evitare burst di
    assign/revoke a velocità user-tier.

    Esempi::

        @router.delete("/wiki/{slug}",
            dependencies=[Depends(require_permission("wiki.delete"))])

        @router.post("/admin/rbac/users/{u}/roles",
            dependencies=[Depends(require_permission(
                "admin.user.manage", rate_limit="admin"))])
    """
    if mode not in ("any", "all"):
        raise ValueError("mode deve essere 'any' o 'all'")
    if rate_limit not in ("user", "admin"):
        raise ValueError("rate_limit deve essere 'user' o 'admin'")
    if not perms:
        raise ValueError("require_permission richiede almeno un permesso")

    rate_limit_value = (
        config.RATE_LIMIT_ADMIN_PER_MINUTE
        if rate_limit == "admin"
        else config.RATE_LIMIT_USER_PER_MINUTE
    )

    def _dep(request: Request) -> dict[str, Any]:
        user = _resolve_user(request)
        _enforce_rate_limit(request, user, rate_limit_value)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticazione richiesta.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_perms = set(user.get("perms") or [])
        ok = (
            any(p in user_perms for p in perms)
            if mode == "any"
            else all(p in user_perms for p in perms)
        )
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permesso richiesto: {', '.join(perms)}.",
            )
        # Force password change baseline (009): blocca anche endpoint
        # permission-protected. Il frontend deve aver già redirectato
        # l'utente a /auth/password al login.
        if user.get("password_must_change"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cambio password obbligatorio prima di proseguire.",
                headers={"X-Password-Must-Change": "true"},
            )
        return user

    return _dep


def require_user_password_current(request: Request) -> dict[str, Any]:
    """Variante stretta di :func:`require_user` che NEGA l'accesso se
    ``users.password_must_change == True``.

    Pattern allineato a NIST SP 800-63B "credential rotation": un
    utente con password forzata al cambio NON può accedere ad altre
    risorse fino a self-service password update. Endpoint
    consentiti durante il "must-change" hold:

    - ``POST /auth/password`` (cambio password che azzera il flag)
    - ``GET  /auth/me`` (per il frontend di sapere lo stato)
    - ``POST /auth/logout`` / ``logout-all``

    Tutti gli altri endpoint applicabili devono dipendere da QUESTA
    funzione invece di :func:`require_user` per ottenere l'enforcement
    hard. Override consapevole: rotte read-only di branding/status
    restano libere via :func:`get_current_user`.
    """
    user = require_user(request)
    if user.get("password_must_change"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cambio password obbligatorio prima di proseguire.",
            headers={"X-Password-Must-Change": "true"},
        )
    return user


__all__ = [
    "get_current_user",
    "require_user",
    "require_user_password_current",
    "require_admin",
    "require_permission",
]
