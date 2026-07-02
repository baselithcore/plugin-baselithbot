"""Minimal, dependency-light OpenID Connect (Authorization Code) client.

Supports discovery (``.well-known/openid-configuration``), the authorization
redirect, code→token exchange, and id_token verification via the provider's
JWKS. Userinfo is fetched as a fallback for missing email/name claims.
"""

import asyncio
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from core.observability.logging import get_logger

logger = get_logger(__name__)

DEFAULT_SCOPES = "openid email profile"
_TIMEOUT = httpx.Timeout(10.0)


class OidcError(Exception):
    """OIDC flow failure."""


class OidcClient:
    """Per-provider OIDC client. ``provider`` is the decrypted provider dict."""

    def __init__(self, provider: Dict[str, Any]) -> None:
        self.slug = provider["slug"]
        cfg = provider.get("config") or {}
        self.client_id = cfg.get("client_id", "")
        self.client_secret = provider.get("client_secret") or ""
        self.issuer = (cfg.get("issuer") or "").rstrip("/")
        self.discovery_url = cfg.get("discovery_url") or (
            f"{self.issuer}/.well-known/openid-configuration" if self.issuer else ""
        )
        self.scopes = cfg.get("scopes") or DEFAULT_SCOPES
        self._endpoints = {
            k: cfg.get(k)
            for k in (
                "authorization_endpoint",
                "token_endpoint",
                "jwks_uri",
                "userinfo_endpoint",
            )
            if cfg.get(k)
        }

    async def _discover(self) -> Dict[str, Any]:
        """Fetch and cache the provider's discovery document."""
        if {"authorization_endpoint", "token_endpoint", "jwks_uri"} <= set(
            self._endpoints
        ):
            return self._endpoints
        if not self.discovery_url:
            raise OidcError("OIDC provider missing issuer/discovery_url")
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(self.discovery_url)
            resp.raise_for_status()
            doc = resp.json()
        self._endpoints.update(
            {
                k: doc[k]
                for k in (
                    "authorization_endpoint",
                    "token_endpoint",
                    "jwks_uri",
                    "userinfo_endpoint",
                )
                if k in doc
            }
        )
        if not self.issuer:
            self.issuer = doc.get("issuer", "").rstrip("/")
        return self._endpoints

    async def authorize_url(self, redirect_uri: str, state: str, nonce: str) -> str:
        """Build the authorization-endpoint redirect URL."""
        eps = await self._discover()
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": self.scopes,
            "state": state,
            "nonce": nonce,
        }
        return f"{eps['authorization_endpoint']}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange an authorization code for tokens."""
        eps = await self._discover()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                eps["token_endpoint"],
                data=data,
                headers={"Accept": "application/json"},
            )
        if resp.status_code != 200:
            raise OidcError(f"Token exchange failed: {resp.status_code}")
        return resp.json()

    def _verify_sync(self, id_token: str, jwks_uri: str, nonce: str) -> Dict[str, Any]:
        signing_key = PyJWKClient(jwks_uri).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "ES256", "RS384", "RS512"],
            audience=self.client_id,
            issuer=self.issuer or None,
            options={"verify_iss": bool(self.issuer)},
        )
        if nonce and claims.get("nonce") and claims["nonce"] != nonce:
            raise OidcError("OIDC nonce mismatch")
        return claims

    async def verify_id_token(self, id_token: str, nonce: str) -> Dict[str, Any]:
        """Verify an id_token's signature and claims via the provider JWKS."""
        eps = await self._discover()
        jwks_uri = eps.get("jwks_uri")
        if not jwks_uri:
            raise OidcError("OIDC provider missing jwks_uri")
        try:
            return await asyncio.to_thread(self._verify_sync, id_token, jwks_uri, nonce)
        except OidcError:
            raise
        except Exception as exc:
            raise OidcError(f"id_token verification failed: {exc}")

    async def userinfo(self, access_token: str) -> Dict[str, Any]:
        """Fetch the userinfo endpoint (best-effort)."""
        eps = await self._discover()
        endpoint = eps.get("userinfo_endpoint")
        if not endpoint:
            return {}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                endpoint, headers={"Authorization": f"Bearer {access_token}"}
            )
        return resp.json() if resp.status_code == 200 else {}


def extract_identity(claims: Dict[str, Any], userinfo: Optional[Dict[str, Any]] = None):
    """Normalize (subject, email, name, email_verified) from claims + userinfo.

    ``email_verified`` gates auto-linking to a pre-existing local account
    (see :func:`plugins.auth.sso.provision_sso_user`). Providers send it as a
    real bool or the string ``"true"``; both are coerced.
    """
    merged = {**(userinfo or {}), **claims}
    subject = merged.get("sub")
    email = merged.get("email")
    name = merged.get("name") or merged.get("preferred_username")
    ev = merged.get("email_verified")
    email_verified = ev is True or str(ev).strip().lower() == "true"
    return subject, email, name, email_verified
