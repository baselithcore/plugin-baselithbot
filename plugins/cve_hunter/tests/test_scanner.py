"""Unit tests for `CVEScannerAgent` covering retry & SecretStr behaviour."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock

import httpx
import pytest

from plugins.cve_hunter.agents.scanner import CVEScannerAgent, _fetch_with_retry
from plugins.cve_hunter.config import CVEHunterConfig


pytestmark = pytest.mark.unit


def _make_config(**overrides: Any) -> CVEHunterConfig:
    base = CVEHunterConfig().model_dump()
    base.update(overrides)
    return CVEHunterConfig(**base)


@pytest.mark.asyncio
async def test_fetch_with_retry_recovers_after_transient_error():
    """Transient `httpx.RequestError` triggers retry until success."""
    response = httpx.Response(200, json={"ok": True})
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.side_effect = [
        httpx.ReadTimeout("first try"),
        response,
    ]

    out = await _fetch_with_retry(
        client,
        url="https://example/api",
        max_attempts=3,
        base_delay=0.0,
        source_label="unit-test",
    )

    assert out is response
    assert client.get.await_count == 2


@pytest.mark.asyncio
async def test_fetch_with_retry_returns_none_after_exhaustion():
    """After `max_attempts` failures the helper returns None instead of raising."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.side_effect = httpx.ConnectError("down")

    out = await _fetch_with_retry(
        client,
        url="https://example/api",
        max_attempts=2,
        base_delay=0.0,
        source_label="unit-test",
    )

    assert out is None
    assert client.get.await_count == 2


@pytest.mark.asyncio
async def test_scan_nvd_paginates_and_terminates(monkeypatch: pytest.MonkeyPatch):
    """`scan_nvd` should consume pages, yield CVEs, and stop at totalResults."""
    cfg = _make_config()
    agent = CVEScannerAgent(config=cfg)

    pages = [
        {
            "vulnerabilities": [
                {"cve": {"id": "CVE-2099-0001"}},
                {"cve": {"id": "CVE-2099-0002"}},
            ],
            "totalResults": 3,
        },
        {
            "vulnerabilities": [{"cve": {"id": "CVE-2099-0003"}}],
            "totalResults": 3,
        },
    ]

    fake_client = AsyncMock(spec=httpx.AsyncClient)
    responses = [httpx.Response(200, json=page) for page in pages]
    fake_client.get.side_effect = responses

    async def _get_client(self):
        return fake_client

    monkeypatch.setattr(CVEScannerAgent, "_get_client", _get_client)

    # Stub parser to return a sentinel record without depending on real parser.
    class _Stub:
        def __init__(self, cve_id: str) -> None:
            self.cve_id = cve_id

    def _parse(cve_data: Dict[str, Any], _config: CVEHunterConfig) -> _Stub:
        return _Stub(cve_data["id"])

    monkeypatch.setattr(
        "plugins.cve_hunter.agents.scanner.parse_nvd_cve",
        _parse,
    )

    # Avoid sleeping between pages.
    import asyncio

    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    found: List[str] = []
    async for cve in agent.scan_nvd(days_back=1, results_per_page=2):
        found.append(cve.cve_id)

    assert found == ["CVE-2099-0001", "CVE-2099-0002", "CVE-2099-0003"]


@pytest.mark.asyncio
async def test_scan_nvd_aborts_on_non_200(monkeypatch: pytest.MonkeyPatch):
    cfg = _make_config()
    agent = CVEScannerAgent(config=cfg)

    fake_client = AsyncMock(spec=httpx.AsyncClient)
    fake_client.get.return_value = httpx.Response(500, json={"error": "boom"})

    async def _get_client(self):
        return fake_client

    monkeypatch.setattr(CVEScannerAgent, "_get_client", _get_client)

    found = [cve async for cve in agent.scan_nvd(days_back=1, results_per_page=2)]
    assert found == []


@pytest.mark.asyncio
async def test_scan_source_dispatches_to_correct_generator(
    monkeypatch: pytest.MonkeyPatch,
):
    """`scan_source` is the synchronous-call adapter used by the swarm."""
    cfg = _make_config()
    agent = CVEScannerAgent(config=cfg)

    async def _empty(*_a: Any, **_kw: Any):
        if False:
            yield  # type: ignore[misc]
        return

    monkeypatch.setattr(agent, "scan_nvd", _empty)
    monkeypatch.setattr(agent, "scan_github", _empty)
    monkeypatch.setattr(agent, "scan_cisa_kev", _empty)
    monkeypatch.setattr(agent, "scan_osv", _empty)

    for source in ("nvd", "github", "cisa_kev", "osv", "unknown"):
        result = await agent.scan_source(source)
        assert result == []
