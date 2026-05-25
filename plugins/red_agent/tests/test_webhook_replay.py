"""Webhook replay-protection tests (timestamp window + nonce cache)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import httpx
import pytest

from plugins.red_agent.integrations.webhook import WebhookNotifier
from plugins.red_agent.integrations.webhook_receiver import (
    _NonceCache,
    WebhookReceiver,
)
from plugins.red_agent.models import Finding, Severity


# --- _NonceCache ----------------------------------------------------


def test_nonce_cache_blocks_repeats() -> None:
    c = _NonceCache(ttl_seconds=10, max_size=1024)
    assert c.check_and_add("a", now=100.0) is True
    assert c.check_and_add("a", now=101.0) is False


def test_nonce_cache_evicts_after_ttl() -> None:
    c = _NonceCache(ttl_seconds=10, max_size=1024)
    c.check_and_add("a", now=100.0)
    # 11s later → "a" expired and re-accepted.
    assert c.check_and_add("a", now=111.0) is True


def test_nonce_cache_lru_size_bound() -> None:
    c = _NonceCache(ttl_seconds=3600, max_size=2)
    assert c.check_and_add("a", now=1.0)
    assert c.check_and_add("b", now=2.0)
    assert c.check_and_add("c", now=3.0)
    # "a" should be evicted by LRU; reaccepted now.
    assert c.check_and_add("a", now=4.0) is True


# --- Receiver: legacy mode (replay_protection=False) ----------------


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_legacy_signature_still_works_when_replay_off() -> None:
    secret = "s"
    body = b'{"x":1}'
    r = WebhookReceiver(enabled=True, secret=secret, require_signature=True)
    assert r.verify_signature(body, _sign(secret, body)) is True


# --- Receiver: replay-protected mode --------------------------------


def _signed_payload(secret: str, ts: int, body: bytes) -> str:
    payload = f"{ts}.".encode() + body
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_replay_mode_accepts_fresh_timestamped_request() -> None:
    secret = "s"
    body = b'{"x":1}'
    ts = int(time.time())
    r = WebhookReceiver(
        enabled=True,
        secret=secret,
        require_signature=True,
        replay_protection=True,
        replay_window_seconds=300,
    )
    sig = _signed_payload(secret, ts, body)
    assert (
        r.verify_signature(body, sig, timestamp_header=str(ts), nonce_header="n1")
        is True
    )


def test_replay_mode_rejects_stale_timestamp() -> None:
    secret = "s"
    body = b'{"x":1}'
    ts = int(time.time()) - 1000  # way outside the 300s window
    r = WebhookReceiver(
        enabled=True,
        secret=secret,
        require_signature=True,
        replay_protection=True,
        replay_window_seconds=300,
    )
    sig = _signed_payload(secret, ts, body)
    assert r.verify_signature(body, sig, timestamp_header=str(ts)) is False


def test_replay_mode_rejects_missing_timestamp() -> None:
    secret = "s"
    body = b'{"x":1}'
    r = WebhookReceiver(
        enabled=True,
        secret=secret,
        require_signature=True,
        replay_protection=True,
    )
    # body-only signature does not satisfy replay-protected verification.
    assert r.verify_signature(body, _sign(secret, body)) is False


def test_replay_mode_rejects_signature_for_different_timestamp() -> None:
    secret = "s"
    body = b'{"x":1}'
    ts = int(time.time())
    r = WebhookReceiver(
        enabled=True,
        secret=secret,
        require_signature=True,
        replay_protection=True,
    )
    sig = _signed_payload(secret, ts, body)
    # Attacker swaps timestamp but cannot recompute HMAC without secret.
    assert r.verify_signature(body, sig, timestamp_header=str(ts + 1)) is False


def test_replay_mode_rejects_duplicate_nonce() -> None:
    secret = "s"
    body = b'{"x":1}'
    ts = int(time.time())
    r = WebhookReceiver(
        enabled=True,
        secret=secret,
        require_signature=True,
        replay_protection=True,
    )
    sig = _signed_payload(secret, ts, body)
    assert (
        r.verify_signature(
            body, sig, timestamp_header=str(ts), nonce_header="repeat-me"
        )
        is True
    )
    # Same nonce inside window → rejected.
    assert (
        r.verify_signature(
            body, sig, timestamp_header=str(ts), nonce_header="repeat-me"
        )
        is False
    )


def test_replay_mode_invalid_timestamp_string_rejected() -> None:
    secret = "s"
    body = b'{"x":1}'
    r = WebhookReceiver(
        enabled=True,
        secret=secret,
        require_signature=True,
        replay_protection=True,
    )
    sig = _signed_payload(secret, 0, body)
    assert r.verify_signature(body, sig, timestamp_header="not-an-int") is False


# --- Notifier: outbound headers --------------------------------------


def _f(severity: Severity = Severity.HIGH) -> Finding:
    return Finding(
        scanner="trivy",
        title="t",
        description="d",
        severity=severity,
        target="example.com",
    )


@pytest.mark.asyncio
async def test_notifier_emits_timestamp_and_nonce_headers() -> None:
    captured: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    secret = "s"
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        secret=secret,
        replay_protection=True,
        client=client,
    )
    await n.notify([_f()])
    assert len(captured) == 1
    req = captured[0]
    ts = req.headers.get("X-RedAgent-Timestamp")
    nonce = req.headers.get("X-RedAgent-Nonce")
    sig = req.headers.get("X-RedAgent-Signature", "")
    assert ts is not None and nonce is not None and sig.startswith("sha256=")
    # Hub-compat alias intentionally omitted in replay mode.
    assert "X-Hub-Signature-256" not in req.headers
    # Verify HMAC of (ts.body) matches the header we sent.
    body = bytes(req.content)
    expected = _signed_payload(secret, int(ts), body)
    assert sig == expected
    await client.aclose()


@pytest.mark.asyncio
async def test_notifier_default_keeps_body_only_signature() -> None:
    captured: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    n = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        secret="s",
        replay_protection=False,
        client=client,
    )
    await n.notify([_f()])
    headers = captured[0].headers
    assert "X-RedAgent-Timestamp" not in headers
    assert "X-RedAgent-Nonce" not in headers
    assert "X-Hub-Signature-256" in headers
    await client.aclose()


# --- End-to-end: notifier → receiver ------------------------------


@pytest.mark.asyncio
async def test_notifier_payload_verifies_in_receiver() -> None:
    """Round-trip: signed outbound payload passes inbound verification."""
    secret = "shared-secret"
    captured: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = bytes(req.content)
        captured["headers"] = dict(req.headers)
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    notifier = WebhookNotifier(
        enabled=True,
        url="https://hook.example.com/in",
        secret=secret,
        replay_protection=True,
        client=client,
    )
    await notifier.notify([_f()])

    receiver = WebhookReceiver(
        enabled=True,
        secret=secret,
        require_signature=True,
        replay_protection=True,
    )
    body = captured["body"]
    headers = captured["headers"]
    ok = receiver.verify_signature(
        body,
        headers.get("x-redagent-signature"),
        timestamp_header=headers.get("x-redagent-timestamp"),
        nonce_header=headers.get("x-redagent-nonce"),
    )
    assert ok is True
    # Replay attempt: same headers → nonce already cached → rejected.
    ok2 = receiver.verify_signature(
        body,
        headers.get("x-redagent-signature"),
        timestamp_header=headers.get("x-redagent-timestamp"),
        nonce_header=headers.get("x-redagent-nonce"),
    )
    assert ok2 is False
    await client.aclose()


def _payload_dict(secret: str, body: bytes, ts: int) -> dict[str, str]:
    """Build a header dict that matches the receiver's expected shape."""
    sig = _signed_payload(secret, ts, body)
    return {
        "X-RedAgent-Timestamp": str(ts),
        "X-RedAgent-Signature": sig,
    }


def test_payload_helper_round_trip() -> None:
    """Sanity check: helper produces verifiable headers."""
    secret = "s"
    body = json.dumps({"a": 1}).encode()
    ts = int(time.time())
    headers = _payload_dict(secret, body, ts)
    r = WebhookReceiver(
        enabled=True,
        secret=secret,
        require_signature=True,
        replay_protection=True,
    )
    assert (
        r.verify_signature(
            body,
            headers["X-RedAgent-Signature"],
            timestamp_header=headers["X-RedAgent-Timestamp"],
        )
        is True
    )
