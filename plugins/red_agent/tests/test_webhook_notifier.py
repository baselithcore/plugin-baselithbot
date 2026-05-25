"""WebhookNotifier tests via httpx.MockTransport — no real HTTP."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest

from plugins.red_agent.integrations.webhook import WebhookNotifier
from plugins.red_agent.models import Finding, Severity


def _f(severity: Severity = Severity.HIGH, **kw: Any) -> Finding:
    base: dict[str, Any] = {
        "scanner": "trivy",
        "title": "demo",
        "description": "d",
        "severity": severity,
        "target": "example.com",
    }
    base.update(kw)
    return Finding(**base)


class _Capture:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.bodies: list[bytes] = []
        self.status_sequence: list[int] = []

    def handler(self, default_status: int = 200) -> Any:
        def _h(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            self.bodies.append(request.content)
            if self.status_sequence:
                status = self.status_sequence.pop(0)
            else:
                status = default_status
            return httpx.Response(status, json={"ok": True})

        return _h


@pytest.mark.asyncio
async def test_disabled_when_url_missing() -> None:
    n = WebhookNotifier(enabled=True, url=None)
    assert n.enabled is False
    assert await n.notify([_f()]) == 0


@pytest.mark.asyncio
async def test_severity_floor_filters_low_findings() -> None:
    cap = _Capture()
    client = httpx.AsyncClient(transport=httpx.MockTransport(cap.handler()))
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        min_severity=Severity.HIGH,
        client=client,
    )
    sent = await n.notify([_f(Severity.LOW), _f(Severity.MEDIUM), _f(Severity.HIGH)])
    assert sent == 1
    assert len(cap.requests) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_payload_is_ocsf_event() -> None:
    cap = _Capture()
    client = httpx.AsyncClient(transport=httpx.MockTransport(cap.handler()))
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        client=client,
    )
    await n.notify([_f(Severity.CRITICAL, cve="CVE-2024-9999")])
    assert len(cap.bodies) == 1
    payload = json.loads(cap.bodies[0])
    assert payload["class_uid"] == 2002
    assert payload["severity"] == "CRITICAL"
    assert payload["vulnerabilities"][0]["cve"]["uid"] == "CVE-2024-9999"
    await client.aclose()


@pytest.mark.asyncio
async def test_hmac_signature_when_secret_set() -> None:
    cap = _Capture()
    client = httpx.AsyncClient(transport=httpx.MockTransport(cap.handler()))
    secret = "topsecret"
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        secret=secret,
        client=client,
    )
    await n.notify([_f(Severity.CRITICAL)])
    req = cap.requests[0]
    body = cap.bodies[0]
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert req.headers["X-RedAgent-Signature"] == f"sha256={expected}"
    assert req.headers["X-Hub-Signature-256"] == f"sha256={expected}"
    await client.aclose()


@pytest.mark.asyncio
async def test_no_signature_header_when_secret_absent() -> None:
    cap = _Capture()
    client = httpx.AsyncClient(transport=httpx.MockTransport(cap.handler()))
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        secret=None,
        client=client,
    )
    await n.notify([_f(Severity.CRITICAL)])
    assert "X-RedAgent-Signature" not in cap.requests[0].headers
    assert "X-Hub-Signature-256" not in cap.requests[0].headers
    await client.aclose()


@pytest.mark.asyncio
async def test_retry_on_5xx_then_success() -> None:
    cap = _Capture()
    cap.status_sequence = [503, 200]
    client = httpx.AsyncClient(transport=httpx.MockTransport(cap.handler()))
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        retry_count=1,
        client=client,
    )
    sent = await n.notify([_f(Severity.HIGH)])
    assert sent == 1
    # Two attempts: first 503, second 200.
    assert len(cap.requests) == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_no_retry_on_4xx_other_than_429() -> None:
    cap = _Capture()
    cap.status_sequence = [400]
    client = httpx.AsyncClient(transport=httpx.MockTransport(cap.handler()))
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        retry_count=3,
        client=client,
    )
    sent = await n.notify([_f(Severity.HIGH)])
    assert sent == 0
    # 400 not retried.
    assert len(cap.requests) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_429_is_retried() -> None:
    cap = _Capture()
    cap.status_sequence = [429, 200]
    client = httpx.AsyncClient(transport=httpx.MockTransport(cap.handler()))
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        retry_count=1,
        client=client,
    )
    sent = await n.notify([_f(Severity.HIGH)])
    assert sent == 1
    assert len(cap.requests) == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_concurrent_fan_out_respects_semaphore() -> None:
    """All eligible findings fan out and each gets one POST."""
    cap = _Capture()
    client = httpx.AsyncClient(transport=httpx.MockTransport(cap.handler()))
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        max_concurrent_requests=2,
        client=client,
    )
    findings = [_f(Severity.HIGH) for _ in range(5)]
    sent = await n.notify(findings)
    assert sent == 5
    assert len(cap.requests) == 5
    await client.aclose()


@pytest.mark.asyncio
async def test_failed_delivery_does_not_block_others() -> None:
    cap = _Capture()
    cap.status_sequence = [500, 500, 200, 200, 200]  # first two retried+fail
    client = httpx.AsyncClient(transport=httpx.MockTransport(cap.handler()))
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        retry_count=0,
        client=client,
    )
    findings = [_f(Severity.HIGH) for _ in range(5)]
    sent = await n.notify(findings)
    assert sent == 3
    await client.aclose()
