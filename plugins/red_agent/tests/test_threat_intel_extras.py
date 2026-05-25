"""OSV.dev + GreyNoise enricher tests using a mocked httpx transport."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from plugins.red_agent.enrichers.greynoise import GreyNoiseEnricher
from plugins.red_agent.enrichers.osv import OSVEnricher
from plugins.red_agent.models import Finding, Severity


def _f(**kw: Any) -> Finding:
    base: dict[str, Any] = {
        "scanner": "trivy",
        "title": "t",
        "description": "d",
        "severity": Severity.MEDIUM,
        "target": "8.8.8.8",
    }
    base.update(kw)
    return Finding(**base)


# --- OSV --------------------------------------------------------------


def _osv_handler(routes: dict[str, dict[str, Any]]) -> Any:
    """Build an httpx MockTransport handler that maps URL → JSON body."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for prefix, payload in routes.items():
            if url.startswith(prefix):
                return httpx.Response(200, json=payload)
        return httpx.Response(404, json={})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_osv_disabled_passthrough() -> None:
    e = OSVEnricher(enabled=False)
    f = _f(cve="CVE-2024-1234")
    out = await e.enrich([f])
    assert "osv_id" not in out[0].evidence


@pytest.mark.asyncio
async def test_osv_lookup_by_cve_annotates_finding() -> None:
    payload = {
        "id": "GHSA-xxxx",
        "summary": "demo bug",
        "aliases": ["CVE-2024-1234", "GHSA-xxxx"],
        "references": [
            {"url": "https://example.com/a"},
            {"url": "https://example.com/b"},
        ],
        "affected": [
            {"ranges": [{"events": [{"introduced": "0"}, {"fixed": "1.2.3"}]}]}
        ],
    }
    routes = {"https://api.osv.dev/v1/vulns/CVE-2024-1234": payload}
    client = httpx.AsyncClient(transport=_osv_handler(routes))
    e = OSVEnricher(client=client)
    f = _f(cve="CVE-2024-1234")
    out = await e.enrich([f])
    ev = out[0].evidence
    assert ev["osv_id"] == "GHSA-xxxx"
    assert ev["osv_summary"] == "demo bug"
    assert ev["osv_aliases"] == ["CVE-2024-1234", "GHSA-xxxx"]
    assert ev["osv_fixed_in"] == ["1.2.3"]
    assert ev["osv_references"] == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    await client.aclose()


@pytest.mark.asyncio
async def test_osv_query_by_package_when_no_cve() -> None:
    payload = {
        "vulns": [
            {
                "id": "GHSA-yyyy",
                "summary": "lodash bug",
                "aliases": ["CVE-2024-9999"],
                "affected": [{"ranges": [{"events": [{"fixed": "4.17.21"}]}]}],
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path != "/v1/query":
            return httpx.Response(404)
        body = json.loads(request.content.decode())
        if (
            body["package"]["name"] == "lodash"
            and body["package"]["ecosystem"] == "npm"
            and body["version"] == "4.17.20"
        ):
            return httpx.Response(200, json=payload)
        return httpx.Response(200, json={"vulns": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    e = OSVEnricher(client=client)
    f = _f(
        scanner="grype",
        cve=None,
        evidence={
            "package": "lodash",
            "installed_version": "4.17.20",
            "ecosystem": "npm",
        },
    )
    out = await e.enrich([f])
    assert out[0].evidence["osv_id"] == "GHSA-yyyy"
    assert out[0].evidence["osv_fixed_in"] == ["4.17.21"]
    await client.aclose()


@pytest.mark.asyncio
async def test_osv_skips_non_eligible_findings() -> None:
    e = OSVEnricher(enabled=True)
    # No CVE, no package → nothing to look up
    f = _f(cve=None, evidence={})
    out = await e.enrich([f])
    assert "osv_id" not in out[0].evidence


@pytest.mark.asyncio
async def test_osv_404_passthrough() -> None:
    routes: dict[str, dict[str, Any]] = {}  # all return 404
    client = httpx.AsyncClient(transport=_osv_handler(routes))
    e = OSVEnricher(client=client)
    f = _f(cve="CVE-9999-9999")
    out = await e.enrich([f])
    assert "osv_id" not in out[0].evidence
    await client.aclose()


# --- GreyNoise -------------------------------------------------------


def _gn_handler(
    payload: dict[str, Any] | None, status: int = 200
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if status == 404 or payload is None:
            return httpx.Response(status, json={})
        return httpx.Response(status, json=payload)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_greynoise_disabled_passthrough() -> None:
    e = GreyNoiseEnricher(enabled=False)
    f = _f(target="8.8.8.8")
    out = await e.enrich([f])
    assert "greynoise_classification" not in out[0].evidence


@pytest.mark.asyncio
async def test_greynoise_annotates_public_ip() -> None:
    payload = {
        "noise": True,
        "riot": False,
        "classification": "benign",
        "name": "Censys Scanner",
        "link": "https://www.greynoise.io/8.8.8.8",
        "last_seen": "2026-04-29",
    }
    client = httpx.AsyncClient(transport=_gn_handler(payload))
    e = GreyNoiseEnricher(client=client)
    out = await e.enrich([_f(target="8.8.8.8")])
    ev = out[0].evidence
    assert ev["greynoise_classification"] == "benign"
    assert ev["greynoise_noise"] is True
    assert ev["greynoise_riot"] is False
    assert ev["greynoise_name"] == "Censys Scanner"
    await client.aclose()


@pytest.mark.asyncio
async def test_greynoise_skips_private_ip() -> None:
    client = httpx.AsyncClient(transport=_gn_handler(None, status=500))
    e = GreyNoiseEnricher(client=client)
    out = await e.enrich([_f(target="10.0.0.1")])
    assert "greynoise_classification" not in out[0].evidence
    await client.aclose()


@pytest.mark.asyncio
async def test_greynoise_skips_non_ip_target() -> None:
    client = httpx.AsyncClient(transport=_gn_handler(None, status=500))
    e = GreyNoiseEnricher(client=client)
    out = await e.enrich([_f(target="example.com")])
    assert "greynoise_classification" not in out[0].evidence
    await client.aclose()


@pytest.mark.asyncio
async def test_greynoise_404_caches_unknown() -> None:
    client = httpx.AsyncClient(transport=_gn_handler(None, status=404))
    e = GreyNoiseEnricher(client=client)
    out = await e.enrich([_f(target="8.8.8.8")])
    # 404 is a cache-able "not seen" — annotate as unknown.
    assert out[0].evidence["greynoise_classification"] == "unknown"
    await client.aclose()


@pytest.mark.asyncio
async def test_greynoise_dedups_repeated_ips() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200,
            json={"classification": "benign", "noise": False, "riot": False},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    e = GreyNoiseEnricher(client=client)
    findings = [_f(target="8.8.8.8") for _ in range(5)]
    await e.enrich(findings)
    assert len(seen) == 1
    await client.aclose()
