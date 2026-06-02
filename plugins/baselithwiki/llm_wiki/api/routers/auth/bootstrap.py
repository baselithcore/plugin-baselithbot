"""Bootstrap endpoints — first-superuser creation gated by loopback."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from llm_wiki import config
from llm_wiki.api.routers.auth.helpers import (
    check_rate,
    client_ip,
    client_is_loopback,
    set_refresh_cookie,
    ua,
)
from llm_wiki.api.routers.auth.models import (
    BootstrapRequest,
    BootstrapStatusResponse,
    TokenResponse,
)
from llm_wiki.auth.tokens import issue_access_token, issue_refresh_token

router = APIRouter()


@router.get("/bootstrap/status", response_model=BootstrapStatusResponse)
def bootstrap_status() -> BootstrapStatusResponse:
    """Pubblico — non leakk a info sensibili: solo conteggio utenti.

    Usato dal SetupWizard frontend per decidere se mostrare lo step
    "crea superuser" prima dello scaffold pack.
    """
    if not config.POSTGRES_ENABLED:
        return BootstrapStatusResponse(needs_bootstrap=False, users_count=0)
    try:
        from llm_wiki.db.users import count_users

        n = count_users()
    except Exception:
        # DB irraggiungibile: fail-open su questo metadata endpoint
        # (non espone dati sensibili). Frontend gestirà come "stato
        # incerto" e mostrerà un errore.
        return BootstrapStatusResponse(needs_bootstrap=False, users_count=0)
    return BootstrapStatusResponse(needs_bootstrap=(n == 0), users_count=n)


@router.post("/bootstrap", response_model=TokenResponse)
def bootstrap_superuser(
    body: BootstrapRequest,
    request: Request,
    response: Response,
) -> TokenResponse:
    """Crea il primo superuser. Gate stile :func:`_require_admin_or_first_boot`:

    - ``users_count == 0`` → libero (con loopback obbligatorio
      come hardening anti-LAN-attacker durante setup).
    - ``users_count > 0`` → 403, no-op. Per aggiungere altri superuser
      usare la CLI (``wiki-wl create-superuser --add``) o la UI admin
      RBAC con un superuser già loggato.

    Audit ``admin.bootstrap`` con ``source="web"``. Apre subito una
    sessione (login implicito) → frontend salta direttamente allo
    step scaffold senza richiedere login esplicito.
    """
    if not config.POSTGRES_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Postgres non disponibile.",
        )

    check_rate(
        identifier=f"bootstrap:{client_ip(request)}",
        limit=max(1, config.RATE_LIMIT_ADMIN_PER_MINUTE // 6),
        window=config.RATE_LIMIT_WINDOW_SECONDS,
    )

    try:
        from llm_wiki.db.users import count_users

        n = count_users()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DB irraggiungibile.",
        ) from exc

    if n > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap già completato.",
        )

    if not client_is_loopback(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap accessibile solo da loopback.",
        )

    from llm_wiki.auth.bootstrap import BootstrapError, create_superuser

    try:
        info = create_superuser(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            tenant_slug=body.tenant_slug or None,
            source="web",
        )
    except BootstrapError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    access, access_exp = issue_access_token(
        user_id=info["user_id"],
        tenant_id=info["tenant_id"],
        role="admin",
    )
    refresh_token, refresh_exp, _family = issue_refresh_token(
        user_id=info["user_id"],
        tenant_id=info["tenant_id"],
        user_agent=ua(request),
        ip_address=client_ip(request),
    )
    set_refresh_cookie(response, refresh_token, refresh_exp)

    return TokenResponse(
        access_token=access,
        expires_at=access_exp,
        user_id=info["user_id"],
        tenant_id=info["tenant_id"],
        role="admin",
        email=info["email"],
    )
