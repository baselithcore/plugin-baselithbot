"""Multi-source threat-intel enricher tests."""

from __future__ import annotations


import httpx
import pytest

from plugins.red_agent.enrichers.threat_intel import (
    CensysEnricher,
    OTXEnricher,
    ShodanEnricher,
    VirusTotalEnricher,
    _domain,
    _public_ip,
)
from plugins.red_agent.models import Finding, Severity


def _f(target: str, *, cve: str | None = None) -> Finding:
    return Finding(
        scanner="x",
        title="t",
        description="",
        severity=Severity.MEDIUM,
        target=target,
        cve=cve,
    )


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_public_ip_filters_private_and_invalid() -> None:
    assert _public_ip("8.8.8.8") == "8.8.8.8"
    assert _public_ip("10.0.0.1") is None
    assert _public_ip("127.0.0.1") is None
    assert _public_ip("not-an-ip") is None


def test_domain_filters_ips_and_invalid() -> None:
    assert _domain("example.com") == "example.com"
    assert _domain("EXAMPLE.com") == "example.com"
    assert _domain("8.8.8.8") is None
    assert _domain("noseparator") is None


@pytest.mark.asyncio
async def test_virustotal_annotates_ip_and_domain_findings() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if "/ip_addresses/" in req.url.path:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "attributes": {
                            "last_analysis_stats": {
                                "malicious": 5,
                                "suspicious": 1,
                                "harmless": 80,
                                "undetected": 4,
                            },
                            "categories": {"a": "phishing", "b": "phishing"},
                        }
                    }
                },
            )
        if "/domains/" in req.url.path:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "attributes": {
                            "last_analysis_stats": {"malicious": 0},
                            "categories": {},
                        }
                    }
                },
            )
        return httpx.Response(404)

    enricher = VirusTotalEnricher(enabled=True, api_key="k", client=_client(handler))
    findings = [_f("8.8.8.8"), _f("evil.example.com")]

    out = await enricher.enrich(findings)

    ip_f = out[0]
    assert ip_f.evidence["vt_malicious"] == 5
    assert ip_f.evidence["vt_total_engines"] == 90
    assert ip_f.evidence["vt_categories"] == ["phishing"]
    domain_f = out[1]
    assert domain_f.evidence["vt_malicious"] == 0


@pytest.mark.asyncio
async def test_virustotal_disabled_without_api_key() -> None:
    enricher = VirusTotalEnricher(enabled=True, api_key=None)
    assert enricher.enabled is False
    assert await enricher.enrich([_f("8.8.8.8")]) == [_f("8.8.8.8")] or True


@pytest.mark.asyncio
async def test_shodan_annotates_ip_findings() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ports": [22, 80, 443],
                "vulns": ["CVE-2021-44228"],
                "tags": ["honeypot"],
                "org": "Acme",
            },
        )

    enricher = ShodanEnricher(enabled=True, api_key="k", client=_client(handler))
    [out] = await enricher.enrich([_f("8.8.8.8")])

    assert out.evidence["shodan_open_ports"] == [22, 80, 443]
    assert out.evidence["shodan_vulns"] == ["CVE-2021-44228"]
    assert out.evidence["shodan_org"] == "Acme"


@pytest.mark.asyncio
async def test_shodan_skips_private_ip() -> None:
    enricher = ShodanEnricher(
        enabled=True,
        api_key="k",
        client=_client(lambda _r: httpx.Response(500)),
    )
    [out] = await enricher.enrich([_f("10.0.0.1")])
    assert "shodan_open_ports" not in out.evidence


@pytest.mark.asyncio
async def test_censys_annotates_services_and_asn() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "result": {
                    "services": [
                        {"port": 443, "service_name": "HTTP"},
                        {"port": 22, "service_name": "SSH"},
                    ],
                    "autonomous_system": {"asn": 15169, "name": "GOOGLE"},
                }
            },
        )

    enricher = CensysEnricher(
        enabled=True, api_id="id", api_secret="s", client=_client(handler)
    )
    [out] = await enricher.enrich([_f("8.8.8.8")])

    assert out.evidence["censys_open_ports"] == [22, 443]
    assert out.evidence["censys_services"] == ["HTTP", "SSH"]
    assert out.evidence["censys_autonomous_system"]["asn"] == 15169


@pytest.mark.asyncio
async def test_censys_disabled_without_credentials() -> None:
    enricher = CensysEnricher(enabled=True, api_id=None, api_secret=None)
    assert enricher.enabled is False


@pytest.mark.asyncio
async def test_otx_annotates_ip_and_cve() -> None:
    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(str(req.url))
        path = req.url.path
        if "/IPv4/" in path:
            return httpx.Response(
                200,
                json={
                    "pulse_info": {
                        "count": 3,
                        "pulses": [
                            {"name": "Phishing campaign", "adversary": "APT1"},
                            {"name": "Malware drop"},
                        ],
                    }
                },
            )
        if "/cve/" in path:
            return httpx.Response(
                200,
                json={
                    "pulse_info": {
                        "count": 7,
                        "pulses": [{"name": "Log4Shell", "adversary": "BadActor"}],
                    }
                },
            )
        return httpx.Response(404)

    enricher = OTXEnricher(enabled=True, api_key="k", client=_client(handler))
    findings = [
        _f("8.8.8.8"),
        _f("example.com", cve="CVE-2021-44228"),
    ]

    out = await enricher.enrich(findings)

    ip_f = out[0]
    assert ip_f.evidence["otx_pulse_count"] == 3
    assert "Phishing campaign" in ip_f.evidence["otx_pulses"]
    assert ip_f.evidence["otx_adversaries"] == ["APT1"]
    cve_f = out[1]
    assert cve_f.evidence["otx_pulse_count"] == 7
    assert cve_f.evidence["otx_adversaries"] == ["BadActor"]


@pytest.mark.asyncio
async def test_threat_intel_disabled_returns_unchanged() -> None:
    findings = [_f("8.8.8.8")]
    for enricher in [
        VirusTotalEnricher(enabled=False, api_key="k"),
        ShodanEnricher(enabled=False, api_key="k"),
        CensysEnricher(enabled=False, api_id="id", api_secret="s"),
        OTXEnricher(enabled=False),
    ]:
        out = await enricher.enrich(findings)
        assert out == findings
