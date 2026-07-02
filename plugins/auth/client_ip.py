"""Trusted-proxy-aware client IP resolution.

Single source of truth shared by audit logging, rate limiting, and risk
assessment so a forged ``X-Forwarded-For`` header can never influence any of
them. Forwarded headers are honoured ONLY when the direct socket peer is a
configured trusted proxy (``AUTH_TRUSTED_PROXIES``; ``*`` trusts all);
otherwise the real socket peer is returned. Previously the rate limiter and the
risk engine read ``X-Forwarded-For`` unconditionally, so an attacker could
rotate the header per request to get a fresh rate-limit bucket (defeating the
login/MFA throttles) and poison the risk score / audit IP.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Request


def trusted_client_ip(request: Optional[Request]) -> Optional[str]:
    """Best-effort client IP, trusting forwarded headers only from a proxy."""
    if not request:
        return None
    peer = request.client.host if request.client else None
    try:
        from core.di.container import ServiceRegistry
        from plugins.auth.config import AuthConfig

        trusted = ServiceRegistry.get(AuthConfig).trusted_proxies
    except Exception:
        trusted = []
    if peer and ("*" in trusted or peer in trusted):
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    return peer


__all__ = ["trusted_client_ip"]
