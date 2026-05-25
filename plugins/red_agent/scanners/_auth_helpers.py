"""Render :class:`AuthProfile` into per-scanner wire format.

Different DAST tools accept authenticated traffic in different
shapes:

- nuclei: ``-H "Header: value"`` repeated.
- ZAP baseline: a context file that names the authentication script.
- schemathesis: ``--header`` / ``--auth user:pass``.

The helpers below produce three normalized representations
(headers, cookies, basic-auth tuple) that each adapter then maps onto
its own argv. Validation is centralized so an under-specified profile
fails *before* the scanner runs, rather than silently issuing
unauthenticated traffic.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

from core.observability.logging import get_logger
from plugins.red_agent.auth_profile import AuthKind, AuthProfile

logger = get_logger(__name__)


class AuthProfileError(ValueError):
    """Raised when the operator-supplied profile is incomplete."""


@dataclass(frozen=True)
class RenderedAuth:
    """Wire-format auth context consumed by the scanner adapters."""

    headers: dict[str, str]
    cookies: dict[str, str]
    basic_auth: tuple[str, str] | None


def _basic_header(username: str, password: str) -> str:
    raw = f"{username}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


async def render_auth(profile: AuthProfile) -> RenderedAuth:
    """Resolve an :class:`AuthProfile` to wire-format auth context.

    For every ``AuthKind`` other than ``OAUTH2_CLIENT_CREDENTIALS``
    the rendering is purely local. The OAuth path performs a single
    token-endpoint POST and stops; subsequent scanner traffic carries
    the resulting bearer token. The function is async so callers can
    treat the OAuth and non-OAuth paths uniformly.
    """

    headers = dict(profile.extra_headers)
    cookies: dict[str, str] = {}
    basic: tuple[str, str] | None = None

    kind = profile.kind
    if kind == AuthKind.NONE:
        return RenderedAuth(headers=headers, cookies=cookies, basic_auth=None)

    if kind == AuthKind.BASIC:
        if not profile.username or profile.password is None:
            raise AuthProfileError("BASIC auth requires username + password")
        basic = (profile.username, profile.password.get_secret_value())
        headers["Authorization"] = _basic_header(*basic)

    elif kind == AuthKind.BEARER:
        if profile.token is None:
            raise AuthProfileError("BEARER auth requires token")
        headers["Authorization"] = f"Bearer {profile.token.get_secret_value()}"

    elif kind == AuthKind.COOKIE:
        if profile.token is None:
            raise AuthProfileError("COOKIE auth requires token (cookie value)")
        name = profile.cookie_name or "session"
        cookies[name] = profile.token.get_secret_value()

    elif kind == AuthKind.FORM_LOGIN:
        if not profile.login_url or not profile.username or profile.password is None:
            raise AuthProfileError("FORM_LOGIN requires login_url, username, password")
        # ZAP/schemathesis consume login_url + field names directly;
        # adapters that lack a login-script path (nuclei) trigger the
        # POST themselves and cache the resulting Set-Cookie.
        async with httpx.AsyncClient(follow_redirects=False, timeout=30) as client:
            resp = await client.post(
                profile.login_url,
                data={
                    profile.login_form_user_field: profile.username,
                    profile.login_form_password_field: (
                        profile.password.get_secret_value()
                    ),
                },
            )
        for k, v in resp.cookies.items():
            cookies[k] = v

    elif kind == AuthKind.OAUTH2_CLIENT_CREDENTIALS:
        if (
            not profile.oauth2_token_url
            or not profile.oauth2_client_id
            or profile.oauth2_client_secret is None
        ):
            raise AuthProfileError(
                "OAUTH2_CLIENT_CREDENTIALS requires token_url, client_id, client_secret"
            )
        data = {
            "grant_type": "client_credentials",
            "client_id": profile.oauth2_client_id,
            "client_secret": profile.oauth2_client_secret.get_secret_value(),
        }
        if profile.oauth2_scope:
            data["scope"] = profile.oauth2_scope
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(profile.oauth2_token_url, data=data)
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise AuthProfileError("OAuth2 response missing access_token")
        headers["Authorization"] = f"Bearer {token}"

    return RenderedAuth(headers=headers, cookies=cookies, basic_auth=basic)


def headers_to_nuclei_argv(headers: dict[str, str]) -> list[str]:
    """Render headers into nuclei ``-H "K: V"`` flags."""

    argv: list[str] = []
    for k, v in headers.items():
        argv.extend(["-H", f"{k}: {v}"])
    return argv


def cookies_to_cookie_header(cookies: dict[str, str]) -> str | None:
    """Collapse a cookie jar into a single ``Cookie:`` header value."""

    if not cookies:
        return None
    return "; ".join(f"{k}={v}" for k, v in cookies.items())
