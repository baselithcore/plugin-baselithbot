"""Tests for the EPSS/KEV + MITRE ATT&CK enrichers."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from plugins.red_agent.enrichers import AttackMapperEnricher, EpssKevEnricher
from plugins.red_agent.models import Finding, Severity


def _finding(
    *, cve: str | None = None, cwe: str | None = None, severity: Severity = Severity.LOW
) -> Finding:
    return Finding(
        scanner="test",
        title="t",
        description="d",
        severity=severity,
        cve=cve,
        cwe=cwe,
        target="https://example.com",
    )


# --- AttackMapper ---------------------------------------------------------


def test_attack_mapper_annotates_cwe() -> None:
    mapper = AttackMapperEnricher()
    findings = [_finding(cwe="CWE-79"), _finding(cwe="CWE-89")]
    out = mapper.enrich(findings)
    assert out[0].evidence["attack_techniques"][0]["id"] == "T1059.007"
    assert out[1].evidence["attack_techniques"][0]["id"] == "T1190"


def test_attack_mapper_unknown_cwe_passthrough() -> None:
    mapper = AttackMapperEnricher()
    f = _finding(cwe="CWE-99999")
    out = mapper.enrich([f])
    assert "attack_techniques" not in out[0].evidence


def test_attack_mapper_disabled() -> None:
    mapper = AttackMapperEnricher(enabled=False)
    f = _finding(cwe="CWE-79")
    out = mapper.enrich([f])
    assert "attack_techniques" not in out[0].evidence


def test_attack_mapper_no_cwe() -> None:
    mapper = AttackMapperEnricher()
    f = _finding()
    out = mapper.enrich([f])
    assert "attack_techniques" not in out[0].evidence


# --- EpssKevEnricher ------------------------------------------------------


class _MockTransport(httpx.AsyncBaseTransport):
    """Minimal mock transport that returns canned responses by URL."""

    def __init__(self, responses: dict[str, dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    async def handle_async_request(  # type: ignore[override]
        self, request: httpx.Request
    ) -> httpx.Response:
        url = str(request.url)
        self.calls.append(url)
        for key, body in self.responses.items():
            if key in url:
                return httpx.Response(200, json=body)
        return httpx.Response(404, json={"error": "not found"})


@pytest.mark.asyncio
async def test_epss_kev_enricher_bumps_severity_on_kev() -> None:
    kev_body = {
        "vulnerabilities": [
            {
                "cveID": "CVE-2024-9999",
                "shortDescription": "exploited in the wild",
                "dueDate": "2025-01-15",
                "requiredAction": "patch",
            }
        ]
    }
    epss_body = {
        "data": [{"cve": "CVE-2024-9999", "epss": "0.95", "percentile": "0.99"}]
    }
    transport = _MockTransport({"first.org": epss_body, "cisa.gov": kev_body})
    client = httpx.AsyncClient(transport=transport)
    enricher = EpssKevEnricher(client=client)
    f = _finding(cve="CVE-2024-9999", severity=Severity.LOW)
    out = await enricher.enrich([f])
    await client.aclose()

    assert out[0].severity == Severity.HIGH
    assert out[0].evidence["kev_listed"] is True
    assert out[0].evidence["epss_score"] == "0.95"


@pytest.mark.asyncio
async def test_epss_kev_enricher_high_epss_bumps_one_step() -> None:
    epss_body = {
        "data": [{"cve": "CVE-2024-1111", "epss": "0.7", "percentile": "0.95"}]
    }
    transport = _MockTransport(
        {"first.org": epss_body, "cisa.gov": {"vulnerabilities": []}}
    )
    client = httpx.AsyncClient(transport=transport)
    enricher = EpssKevEnricher(client=client)
    f = _finding(cve="CVE-2024-1111", severity=Severity.LOW)
    out = await enricher.enrich([f])
    await client.aclose()

    # LOW -> MEDIUM (one step)
    assert out[0].severity == Severity.MEDIUM
    assert out[0].evidence["epss_score"] == "0.7"
    assert out[0].evidence.get("kev_listed") is None


@pytest.mark.asyncio
async def test_epss_kev_enricher_no_cve_passthrough() -> None:
    transport = _MockTransport({})
    client = httpx.AsyncClient(transport=transport)
    enricher = EpssKevEnricher(client=client)
    out = await enricher.enrich([_finding()])
    await client.aclose()
    assert transport.calls == []
    assert out[0].severity == Severity.LOW


@pytest.mark.asyncio
async def test_epss_kev_enricher_fail_open_on_http_error() -> None:
    class _BoomTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(  # type: ignore[override]
            self, request: httpx.Request
        ) -> httpx.Response:
            raise httpx.ConnectError("boom")

    client = httpx.AsyncClient(transport=_BoomTransport())
    enricher = EpssKevEnricher(client=client)
    f = _finding(cve="CVE-2024-2222", severity=Severity.MEDIUM)
    out = await enricher.enrich([f])
    await client.aclose()

    # Original list returned untouched — no severity drift, no annotation.
    assert out[0].severity == Severity.MEDIUM
    assert "kev_listed" not in out[0].evidence
    assert "epss_score" not in out[0].evidence


@pytest.mark.asyncio
async def test_epss_kev_enricher_disabled() -> None:
    transport = _MockTransport({})
    client = httpx.AsyncClient(transport=transport)
    enricher = EpssKevEnricher(client=client, enabled=False)
    f = _finding(cve="CVE-2024-3333")
    out = await enricher.enrich([f])
    await client.aclose()
    assert transport.calls == []
    assert "kev_listed" not in out[0].evidence
