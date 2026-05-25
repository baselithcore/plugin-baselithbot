"""Internal helpers shared across auth route modules.

Kept lightweight (no DB / token / crypto imports) so route modules can
pull what they need without hitting circular-import traps.
"""

from __future__ import annotations

import datetime
import re

from fastapi import HTTPException, Request, Response, status

from llm_wiki import config
from llm_wiki.auth.rate_limit import RateLimitExceeded, rate_limiter

REFRESH_COOKIE_NAME = "llm_wiki_refresh"
_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Rate limit specifici per auth (più stretti dei default user/admin).
RL_LOGIN_PER_MIN_IP = 10
RL_LOGIN_PER_MIN_EMAIL = 5
RL_REGISTER_PER_HOUR_IP = 5
RL_REFRESH_PER_MIN_IP = 30


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "-"


def ua(request: Request) -> str:
    return (request.headers.get("user-agent") or "")[:500]


def slugify(value: str) -> str:
    s = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return s or "tenant"


def set_refresh_cookie(response: Response, token: str, expires_at: datetime.datetime) -> None:
    max_age = int((expires_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=max(0, max_age),
        httponly=True,
        secure=config.AUTH_COOKIE_SECURE,
        samesite=config.AUTH_COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/auth",
        httponly=True,
        secure=config.AUTH_COOKIE_SECURE,
        samesite=config.AUTH_COOKIE_SAMESITE,  # type: ignore[arg-type]
    )


def check_rate(identifier: str, limit: int, window: int) -> None:
    try:
        rate_limiter.check(identifier, limit, window)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Troppi tentativi, riprova fra poco.",
        ) from exc


def client_is_loopback(request: Request) -> bool:
    import ipaddress as _ip

    host = client_ip(request)
    if not host or host == "-":
        return False
    try:
        return _ip.ip_address(host).is_loopback
    except ValueError:
        return False
