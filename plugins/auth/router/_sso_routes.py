"""Public SSO flow: provider discovery, login redirect, OIDC callback,
SAML ACS, and SP metadata. All endpoints are unauthenticated by design."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from core.observability.logging import get_logger
from plugins.auth.config import AuthConfig
from plugins.auth.dependencies import get_auth_config_dep, get_auth_persistence_dep
from plugins.auth.persistence import AuthPersistence
from plugins.auth.router._helpers import client_ip, establish_session
from plugins.auth.sso import (
    SAML_AVAILABLE,
    OidcClient,
    extract_identity,
    extract_saml_identity,
    load_provider,
    login_redirect,
    metadata_xml,
    process_acs,
    provision_sso_user,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/sso")

_LOGIN_URL = "/auth/login"
_APP_URL = "/auth/"


def _err_redirect(reason: str) -> RedirectResponse:
    return RedirectResponse(url=f"{_LOGIN_URL}?sso_error={reason}", status_code=302)


def _clear_sso_cookies(resp: RedirectResponse) -> RedirectResponse:
    """Burn the transient OIDC state/nonce cookies (single-use)."""
    resp.delete_cookie("sso_state", path="/api/auth/sso")
    resp.delete_cookie("sso_nonce", path="/api/auth/sso")
    return resp


def _request_data(request: Request, form: dict | None = None) -> dict:
    url = request.url
    return {
        "https": url.scheme == "https",
        "host": url.hostname or "",
        "path": url.path,
        "port": url.port,
        "get_data": dict(request.query_params),
        "post_data": form or {},
    }


@router.get("/providers")
async def list_providers(
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Public list of enabled SSO providers (for login buttons)."""
    if not config.sso_enabled:
        return []
    return [
        {"slug": p["slug"], "name": p["name"], "protocol": p["protocol"]}
        for p in persistence.list_sso_providers(enabled_only=True)
    ]


@router.get("/{slug}/login")
async def sso_login(
    slug: str,
    request: Request,
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """Begin an SSO login (SP-initiated)."""
    if not config.sso_enabled:
        raise HTTPException(status_code=403, detail="SSO is disabled")
    provider = load_provider(persistence, slug)
    if not provider or not provider.get("enabled"):
        raise HTTPException(status_code=404, detail="Provider not found")

    base = config.app_base_url
    if provider["protocol"] == "oidc":
        client = OidcClient(provider)
        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(24)
        redirect_uri = f"{base}/api/auth/sso/{slug}/callback"
        try:
            url = await client.authorize_url(redirect_uri, state, nonce)
        except Exception as exc:
            logger.warning("OIDC authorize failed for %s: %s", slug, exc)
            return _err_redirect("provider_unavailable")
        resp = RedirectResponse(url=url, status_code=302)
        for key, value in (("sso_state", state), ("sso_nonce", nonce)):
            resp.set_cookie(
                key,
                value,
                httponly=True,
                secure=config.cookie_secure,
                samesite="lax",
                max_age=600,
                path="/api/auth/sso",
            )
        return resp

    # SAML
    if not SAML_AVAILABLE:
        raise HTTPException(status_code=503, detail="SAML not available on server")
    try:
        url = login_redirect(provider, base, _request_data(request), _APP_URL)
    except Exception as exc:
        logger.warning("SAML login failed for %s: %s", slug, exc)
        return _err_redirect("provider_unavailable")
    return RedirectResponse(url=url, status_code=302)


@router.get("/{slug}/callback")
async def oidc_callback(
    slug: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """OIDC redirect callback: exchange code, verify, provision, sign in.

    The ``state``/``nonce`` are bound to the browser via httponly cookies set at
    login start: an attacker cannot set the victim's cookie, and a missing or
    mismatched cookie is rejected. Cookies are single-use — cleared on every
    outcome below — so a captured state cannot be replayed.
    """
    stored_state = request.cookies.get("sso_state")
    if not code:
        return _clear_sso_cookies(_err_redirect("missing_code"))
    # Reject if the state cookie is missing or does not match the URL state.
    if not state or not stored_state or stored_state != state:
        return _clear_sso_cookies(_err_redirect("state_mismatch"))
    provider = load_provider(persistence, slug)
    if not provider or provider["protocol"] != "oidc":
        return _clear_sso_cookies(_err_redirect("provider_not_found"))

    nonce = request.cookies.get("sso_nonce", "")
    redirect_uri = f"{config.app_base_url}/api/auth/sso/{slug}/callback"
    client = OidcClient(provider)
    try:
        tokens = await client.exchange_code(code, redirect_uri)
        claims = await client.verify_id_token(tokens.get("id_token", ""), nonce)
        userinfo = await client.userinfo(tokens.get("access_token", ""))
    except Exception as exc:
        logger.warning("OIDC callback failed for %s: %s", slug, exc)
        return _clear_sso_cookies(_err_redirect("verification_failed"))

    subject, email, name = extract_identity(claims, userinfo)
    if not subject:
        return _clear_sso_cookies(_err_redirect("no_subject"))
    # _finish_sso clears the cookies on the success redirect.
    return _finish_sso(
        persistence, config, provider, subject, email, name, request, slug
    )


@router.post("/{slug}/acs")
async def saml_acs(
    slug: str,
    request: Request,
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """SAML assertion consumer service: validate assertion, provision, sign in."""
    if not SAML_AVAILABLE:
        raise HTTPException(status_code=503, detail="SAML not available on server")
    provider = load_provider(persistence, slug)
    if not provider or provider["protocol"] != "saml":
        return _err_redirect("provider_not_found")
    form = dict(await request.form())
    try:
        nameid, attrs = process_acs(
            provider, config.app_base_url, _request_data(request, form)
        )
    except Exception as exc:
        logger.warning("SAML ACS failed for %s: %s", slug, exc)
        return _err_redirect("verification_failed")
    subject, email, name = extract_saml_identity(nameid, attrs)
    if not subject:
        return _err_redirect("no_subject")
    return _finish_sso(
        persistence, config, provider, subject, email, name, request, slug
    )


@router.get("/{slug}/metadata")
async def saml_metadata(
    slug: str,
    config: AuthConfig = Depends(get_auth_config_dep),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
):
    """SP metadata XML for a SAML provider."""
    if not SAML_AVAILABLE:
        raise HTTPException(status_code=503, detail="SAML not available on server")
    provider = load_provider(persistence, slug)
    if not provider or provider["protocol"] != "saml":
        raise HTTPException(status_code=404, detail="Provider not found")
    try:
        xml = metadata_xml(provider, config.app_base_url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Metadata error: {exc}")
    return Response(content=xml, media_type="application/xml")


def _finish_sso(persistence, config, provider, subject, email, name, request, slug):
    """Provision/link the identity and issue a session, then redirect to the app."""
    from plugins.auth.sso import ProvisioningError

    try:
        user = provision_sso_user(
            persistence, provider, subject, email, name, config.sso_allow_signup
        )
    except ProvisioningError as exc:
        logger.info("SSO provisioning rejected for %s: %s", slug, exc)
        return _err_redirect("no_account")
    resp = RedirectResponse(url=_APP_URL, status_code=302)
    establish_session(user.id, resp, persistence, config)
    persistence.record_login_event(
        user.id,
        "login_success",
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
        method="sso",
        details={"provider": slug},
    )
    # Clear transient OIDC cookies.
    resp.delete_cookie("sso_state", path="/api/auth/sso")
    resp.delete_cookie("sso_nonce", path="/api/auth/sso")
    return resp
