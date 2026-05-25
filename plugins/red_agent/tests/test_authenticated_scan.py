"""Authenticated-scan and Vault credential-backend unit tests."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from plugins.red_agent._credential_resolver import (
    CredentialResolutionError,
    VaultBackend,
    get_backend,
    MetadataBackend,
    resolve_credentials,
)
from plugins.red_agent.auth_profile import AuthKind, AuthProfile
from plugins.red_agent.models import Target, TargetType
from plugins.red_agent.scanners._auth_helpers import (
    AuthProfileError,
    cookies_to_cookie_header,
    headers_to_nuclei_argv,
    render_auth,
)


# --- AuthProfile rendering ---


@pytest.mark.asyncio
async def test_render_auth_none_returns_extra_headers_only() -> None:
    profile = AuthProfile(extra_headers={"X-Tenant": "acme"})
    rendered = await render_auth(profile)
    assert rendered.headers == {"X-Tenant": "acme"}
    assert rendered.cookies == {}
    assert rendered.basic_auth is None


@pytest.mark.asyncio
async def test_render_auth_basic_sets_authorization_header() -> None:
    profile = AuthProfile(
        kind=AuthKind.BASIC, username="alice", password=SecretStr("hunter2")
    )
    rendered = await render_auth(profile)
    assert rendered.basic_auth == ("alice", "hunter2")
    assert rendered.headers["Authorization"].startswith("Basic ")


@pytest.mark.asyncio
async def test_render_auth_bearer() -> None:
    profile = AuthProfile(kind=AuthKind.BEARER, token=SecretStr("eyJ..."))
    rendered = await render_auth(profile)
    assert rendered.headers["Authorization"] == "Bearer eyJ..."


@pytest.mark.asyncio
async def test_render_auth_cookie_default_name() -> None:
    profile = AuthProfile(kind=AuthKind.COOKIE, token=SecretStr("abc"))
    rendered = await render_auth(profile)
    assert rendered.cookies == {"session": "abc"}


@pytest.mark.asyncio
async def test_render_auth_basic_missing_password_raises() -> None:
    profile = AuthProfile(kind=AuthKind.BASIC, username="alice")
    with pytest.raises(AuthProfileError):
        await render_auth(profile)


@pytest.mark.asyncio
async def test_render_auth_bearer_missing_token_raises() -> None:
    profile = AuthProfile(kind=AuthKind.BEARER)
    with pytest.raises(AuthProfileError):
        await render_auth(profile)


@pytest.mark.asyncio
async def test_render_auth_oauth2_requires_endpoint_and_secret() -> None:
    profile = AuthProfile(
        kind=AuthKind.OAUTH2_CLIENT_CREDENTIALS, oauth2_client_id="client"
    )
    with pytest.raises(AuthProfileError):
        await render_auth(profile)


def test_to_redacted_dict_redacts_secrets() -> None:
    profile = AuthProfile(
        kind=AuthKind.BEARER,
        token=SecretStr("topsecret"),
    )
    out = profile.to_redacted_dict()
    assert out["token"] == "<redacted>"
    assert out["kind"] == AuthKind.BEARER


def test_headers_to_nuclei_argv() -> None:
    argv = headers_to_nuclei_argv({"Authorization": "Bearer x", "X-T": "y"})
    assert argv == ["-H", "Authorization: Bearer x", "-H", "X-T: y"]


def test_cookies_to_cookie_header() -> None:
    assert cookies_to_cookie_header({}) is None
    assert cookies_to_cookie_header({"a": "1", "b": "2"}) == "a=1; b=2"


# --- Vault backend ---


class _FakeResponse:
    def __init__(self, *, status_code: int, payload: dict | None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError(
                "boom",
                request=None,  # type: ignore[arg-type]
                response=None,  # type: ignore[arg-type]
            )


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str, *, headers: dict[str, str]) -> _FakeResponse:
        self.calls.append((url, headers))
        return self._response


@pytest.mark.asyncio
async def test_vault_backend_resolves_kv2_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "data": {
            "data": {
                "username": "svc",
                "password": "p@ss",
                "domain": "CORP",
            }
        }
    }
    fake_client = _FakeClient(_FakeResponse(status_code=200, payload=payload))

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: fake_client)

    backend = VaultBackend(
        addr="https://vault.example",
        kv_mount="kv",
        token="t.abc",
    )

    cred = await backend.resolve(
        target=Target(type=TargetType.AD_DOMAIN, value="corp.example.com"),
        credentials_ref="red-agent/engagements/acme/ad",
    )

    assert cred.username == "svc"
    assert cred.password is not None and cred.password.get_secret_value() == "p@ss"
    assert cred.domain == "CORP"
    url, headers = fake_client.calls[0]
    assert url == "https://vault.example/v1/kv/data/red-agent/engagements/acme/ad"
    assert headers["X-Vault-Token"] == "t.abc"


@pytest.mark.asyncio
async def test_vault_backend_requires_credentials_ref() -> None:
    backend = VaultBackend(addr="https://v", kv_mount="kv", token="t")
    with pytest.raises(CredentialResolutionError):
        await backend.resolve(
            target=Target(type=TargetType.AD_DOMAIN, value="x"),
            credentials_ref=None,
        )


def test_get_backend_vault_falls_back_when_misconfigured() -> None:
    # Missing addr → metadata fallback (with warning).
    assert isinstance(
        get_backend("vault", vault_addr=None, vault_token="t"), MetadataBackend
    )
    assert isinstance(
        get_backend("vault", vault_addr="https://v", vault_token=None), MetadataBackend
    )


def test_get_backend_vault_constructs_when_configured() -> None:
    backend = get_backend(
        "vault", vault_addr="https://v", vault_kv_mount="kv", vault_token="t"
    )
    assert isinstance(backend, VaultBackend)


@pytest.mark.asyncio
async def test_resolve_credentials_routes_to_vault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"data": {"data": {"username": "u", "password": "p"}}}
    fake_client = _FakeClient(_FakeResponse(status_code=200, payload=payload))
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: fake_client)

    cred = await resolve_credentials(
        backend_name="vault",
        target=Target(type=TargetType.AD_DOMAIN, value="x"),
        credentials_ref="some/path",
        vault_addr="https://v",
        vault_kv_mount="kv",
        vault_token="t",
    )
    assert cred.username == "u"
