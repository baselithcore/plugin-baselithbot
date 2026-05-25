"""GraphQL / JWT / WAF evasion scanner tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest

from plugins.red_agent.models import ScanIntensity, Severity, Target, TargetType
from plugins.red_agent.scanners.graphql_audit import GraphQLAuditScanner
from plugins.red_agent.scanners.jwt_audit import (
    JWTAuditScanner,
    _split_jwt,
)
from plugins.red_agent.scanners.waf_evasion import (
    WAFEvasionScanner,
    _fullwidth,
    _mixed_case,
    _url_double_encode,
)


_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _client(handler) -> httpx.AsyncClient:
    return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler))


# --- graphql_audit ---


def _gql_target() -> Target:
    return Target(
        type=TargetType.URL,
        value="https://api.example.com",
        metadata={"graphql_path": "/graphql"},
    )


@pytest.mark.asyncio
async def test_graphql_introspection_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode("utf-8"))
        if isinstance(body, list):
            return httpx.Response(
                200, json=[{"data": {"__typename": "Q"}}, {"data": {"__typename": "Q"}}]
            )
        query = body.get("query", "")
        if "__schema" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "__schema": {
                            "types": [{"name": "User"}, {"name": "Query"}],
                        }
                    }
                },
            )
        if "__typenameXX" in query:
            return httpx.Response(
                200,
                json={"errors": [{"message": 'Did you mean "__typename"?'}]},
            )
        if "a0:" in query:
            return httpx.Response(200, json={"data": {"a0": "Q"}})
        return httpx.Response(200, json={"data": {}})

    sc = GraphQLAuditScanner()
    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: _client(handler))

    findings = await sc.run(_gql_target(), ScanIntensity.ACTIVE)
    titles = [f.title for f in findings]

    assert any("introspection enabled" in t for t in titles)
    assert any("field-suggestion" in t for t in titles)
    assert any("alias overload" in t for t in titles)
    assert any("batch operations" in t for t in titles)


@pytest.mark.asyncio
async def test_graphql_skips_when_introspection_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"errors": [{"message": "forbidden"}]})

    sc = GraphQLAuditScanner()
    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: _client(handler))

    findings = await sc.run(_gql_target(), ScanIntensity.ACTIVE)
    titles = [f.title for f in findings]
    assert not any("introspection enabled" in t for t in titles)


# --- jwt_audit ---


def _make_jwt(
    header: dict[str, Any], payload: dict[str, Any], secret: str | None
) -> str:
    h = base64.urlsafe_b64encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    ).rstrip(b"=")
    p = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).rstrip(b"=")
    signing_input = h + b"." + p
    if secret is None:
        sig = b""
    else:
        sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s = base64.urlsafe_b64encode(sig).rstrip(b"=")
    return (signing_input + b"." + s).decode("ascii")


def _jwt_target(token: str) -> Target:
    return Target(
        type=TargetType.URL,
        value="https://api.example.com",
        metadata={"jwt_samples": [token]},
    )


@pytest.mark.asyncio
async def test_jwt_alg_none_flagged() -> None:
    token = _make_jwt({"alg": "none", "typ": "JWT"}, {"sub": "alice"}, None)
    sc = JWTAuditScanner()
    [f] = await sc.run(_jwt_target(token), ScanIntensity.ACTIVE)
    assert f.title == "JWT alg=none accepted"
    assert f.severity == Severity.CRITICAL


@pytest.mark.asyncio
async def test_jwt_weak_hs256_secret_cracked() -> None:
    token = _make_jwt({"alg": "HS256"}, {"iss": "x", "sub": "u"}, "secret")
    sc = JWTAuditScanner()
    findings = await sc.run(_jwt_target(token), ScanIntensity.ACTIVE)
    assert any("weak secret" in f.title for f in findings)
    cracked = [f for f in findings if "weak secret" in f.title][0]
    assert cracked.severity == Severity.CRITICAL


@pytest.mark.asyncio
async def test_jwt_kid_traversal_flagged() -> None:
    token = _make_jwt(
        {"alg": "RS256", "kid": "../../../../etc/passwd"},
        {"sub": "u"},
        "doesnotmatter",
    )
    sc = JWTAuditScanner()
    findings = await sc.run(_jwt_target(token), ScanIntensity.ACTIVE)
    assert any("kid path traversal" in f.title for f in findings)


@pytest.mark.asyncio
async def test_jwt_jku_external_flagged() -> None:
    token = _make_jwt(
        {"alg": "RS256", "jku": "https://attacker.example/jwks.json"},
        {"sub": "u"},
        "x",
    )
    sc = JWTAuditScanner()
    findings = await sc.run(_jwt_target(token), ScanIntensity.ACTIVE)
    assert any("jku references external" in f.title for f in findings)


@pytest.mark.asyncio
async def test_jwt_strong_hs256_not_cracked() -> None:
    token = _make_jwt(
        {"alg": "HS256"}, {"sub": "u"}, "this-is-a-really-long-strong-secret-32+"
    )
    sc = JWTAuditScanner()
    findings = await sc.run(_jwt_target(token), ScanIntensity.ACTIVE)
    assert not any("weak secret" in f.title for f in findings)


def test_split_jwt_handles_bearer_prefix_and_pad() -> None:
    token = _make_jwt({"alg": "HS256"}, {"sub": "u"}, "secret")
    parsed = _split_jwt("Bearer  " + token)
    assert parsed is not None


def test_split_jwt_rejects_garbage() -> None:
    assert _split_jwt("not.a.token") is None
    assert _split_jwt("only-one-segment") is None


# --- waf_evasion ---


def test_waf_evasion_encoders_independent() -> None:
    assert _url_double_encode("' OR 1=1") == "%2527%2520OR%25201%253D1"
    assert _mixed_case("admin") == "aDmIn"
    assert _fullwidth("admin") == "ａｄｍｉｎ"


@pytest.mark.asyncio
async def test_waf_evasion_refuses_below_intrusive() -> None:
    sc = WAFEvasionScanner()
    target = Target(type=TargetType.URL, value="https://example.com")
    findings = await sc.run(target, ScanIntensity.ACTIVE)
    assert findings == []


@pytest.mark.asyncio
async def test_waf_evasion_detects_vendor_and_evasion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_payloads: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        q = req.url.params.get("q", "")
        seen_payloads.append(q)
        # First request: fingerprint trigger ("../"*8). Return Cloudflare header.
        if q.startswith("../"):
            return httpx.Response(
                200,
                headers={"server": "cloudflare", "cf-ray": "abc"},
                text="ok",
            )
        # Baseline payloads → blocked.
        if q in {"' OR 1=1 --", "<script>alert(1)</script>", "../../../etc/passwd"}:
            return httpx.Response(403, text="blocked")
        # Encoded variants slip through.
        return httpx.Response(200, text="ok")

    sc = WAFEvasionScanner()
    monkeypatch.setattr(httpx, "AsyncClient", lambda *_a, **_k: _client(handler))

    target = Target(type=TargetType.URL, value="https://example.com")
    findings = await sc.run(target, ScanIntensity.INTRUSIVE)

    titles = [f.title for f in findings]
    assert any("WAF detected: Cloudflare" in t for t in titles)
    assert any("WAF evasion succeeded" in t for t in titles)
    evasion_finding = [f for f in findings if "evasion succeeded" in f.title][0]
    assert evasion_finding.severity == Severity.HIGH
