"""Enterprise-hardening tests: governance, idempotency, resilience, authz.

Covers the prototype→enterprise upgrade: the config-wiring fix, inbound
idempotency, the audit trail, the runtime kill-switch, the resilient gateway,
fail-closed webhook authentication, and the RBAC route guards. Everything runs
hermetically — explicit ``fake`` gateway + in-memory store, no network, no LLM —
so the suite honours the plugin's no-infra contract regardless of ambient
``.env`` overrides.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.baselithtwin.audit.models import AuditAction
from plugins.baselithtwin.config import (
    AutonomyMode,
    GatewayKind,
    PersistenceKind,
    TwinConfig,
)
from plugins.baselithtwin.gateway._resilient import ResilientGateway
from plugins.baselithtwin.gateway.models import (
    InboundMessage,
    OutboundMessage,
    SendReceipt,
)
from plugins.baselithtwin.models import ReplyStatus, WhitelistEntry
from plugins.baselithtwin.plugin import BaselithTwinPlugin
from plugins.baselithtwin.service import TwinService


def _config(**overrides) -> TwinConfig:
    params: dict = {
        "owner_name": "Gio",
        "gateway": GatewayKind.FAKE,
        "persistence": PersistenceKind.MEMORY,
        "require_webhook_secret": False,
        "webhook_secret": "",  # override any ambient ``.env`` secret
    }
    params.update(overrides)
    return TwinConfig(**params)


async def _service(**overrides) -> TwinService:
    svc = TwinService(_config(**overrides))
    await svc.initialize()
    return svc


# -- Config wiring fix -------------------------------------------------------


async def test_plugin_initialize_honours_config_block() -> None:
    """The plugin must apply its config block, not silently fall back to defaults."""
    plugin = BaselithTwinPlugin()
    await plugin.initialize(
        {"owner_name": "Alice", "autonomy": "suggest", "gateway": "fake"}
    )
    assert plugin.config.owner_name == "Alice"
    assert plugin.config.autonomy is AutonomyMode.SUGGEST
    await plugin.shutdown()


# -- Inbound idempotency -----------------------------------------------------


async def test_duplicate_inbound_is_dropped() -> None:
    svc = await _service(autonomy=AutonomyMode.SUGGEST)
    first = await svc.ingest(InboundMessage(id="dup1", contact_id="c@c.us", text="hi"))
    second = await svc.ingest(InboundMessage(id="dup1", contact_id="c@c.us", text="hi"))
    assert first is not None
    assert second is None  # re-delivery dropped
    assert len(await svc.list_pending()) == 1


# -- Kill-switch -------------------------------------------------------------


async def test_pause_forces_queue_even_when_whitelisted() -> None:
    svc = await _service(autonomy=AutonomyMode.FULL)
    await svc.add_to_whitelist(WhitelistEntry(contact_id="c@c.us"))
    await svc.set_paused(True, actor="admin")

    async def _hi_conf(message, *_a, **_k):
        from plugins.baselithtwin.models import DraftReply

        return DraftReply(
            contact_id=message.contact_id,
            in_reply_to=message.id,
            text="sure",
            confidence=0.9,
        )

    svc._engine.draft = _hi_conf  # type: ignore[method-assign]
    pending = await svc.ingest(InboundMessage(id="p1", contact_id="c@c.us", text="yo"))
    assert pending is not None
    assert pending.status is ReplyStatus.QUEUED  # not auto-sent while paused
    assert await svc.is_paused() is True


# -- Audit trail -------------------------------------------------------------


async def test_decisions_are_audited_with_actor() -> None:
    svc = await _service(autonomy=AutonomyMode.SUGGEST)
    pending = await svc.ingest(InboundMessage(id="a1", contact_id="c@c.us", text="hi"))
    assert pending is not None
    await svc.approve(pending.id, actor="alice@corp", ip="10.0.0.1")
    events = await svc.list_audit()
    approved = [e for e in events if e.action is AuditAction.REPLY_APPROVED]
    assert approved and approved[0].actor == "alice@corp"
    assert approved[0].ip_address == "10.0.0.1"


async def test_whitelist_and_pause_audited() -> None:
    svc = await _service()
    await svc.add_to_whitelist(WhitelistEntry(contact_id="c@c.us"), actor="bob")
    await svc.set_paused(True, actor="bob")
    actions = {e.action for e in await svc.list_audit()}
    assert AuditAction.WHITELIST_ADDED in actions
    assert AuditAction.TWIN_PAUSED in actions


# -- Resilient gateway -------------------------------------------------------


class _FlakyGateway:
    """Fails the first ``fail_times`` sends, then succeeds."""

    def __init__(self, fail_times: int) -> None:
        self._left = fail_times
        self.calls = 0

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def is_connected(self) -> bool:
        return True

    async def send(self, message: OutboundMessage) -> SendReceipt:
        self.calls += 1
        if self._left > 0:
            self._left -= 1
            return SendReceipt(ok=False, error="transient")
        return SendReceipt(ok=True, message_id="ok")


async def test_resilient_gateway_retries_then_succeeds() -> None:
    inner = _FlakyGateway(fail_times=2)
    gw = ResilientGateway(inner, name="twin_test_ok", max_attempts=3)
    receipt = await gw.send(OutboundMessage(contact_id="c@c.us", text="x"))
    assert receipt.ok is True
    assert inner.calls == 3  # two failures + one success


async def test_resilient_gateway_degrades_to_failed_receipt() -> None:
    inner = _FlakyGateway(fail_times=99)
    gw = ResilientGateway(inner, name="twin_test_fail", max_attempts=2)
    receipt = await gw.send(OutboundMessage(contact_id="c@c.us", text="x"))
    assert receipt.ok is False  # never raises into the caller


# -- HTTP surface: webhook auth + RBAC guards --------------------------------


def _client(**cfg) -> tuple[TestClient, BaselithTwinPlugin]:
    plugin = BaselithTwinPlugin()
    plugin._twin_config = _config(**cfg)
    app = FastAPI()
    app.include_router(plugin.create_router())
    return TestClient(app), plugin


def test_webhook_rejected_when_secret_unset() -> None:
    client, _ = _client(require_webhook_secret=True)
    resp = client.post(
        "/webhook", json={"id": "w1", "contact_id": "c@c.us", "text": "hi"}
    )
    assert resp.status_code == 503  # fail-closed


def test_webhook_requires_matching_secret() -> None:
    client, _ = _client(require_webhook_secret=True, webhook_secret="s3cret")
    bad = client.post(
        "/webhook",
        json={"id": "w2", "contact_id": "c@c.us", "text": "hi"},
        headers={"X-Webhook-Secret": "wrong"},
    )
    assert bad.status_code == 401
    good = client.post(
        "/webhook",
        json={"id": "w3", "contact_id": "c@c.us", "text": "hi"},
        headers={"X-Webhook-Secret": "s3cret"},
    )
    assert good.status_code == 200


def test_reads_open_but_mutations_guarded_off_auth() -> None:
    # Auth not enforced + require_admin (default) ⇒ reads open, sends denied.
    client, _ = _client(require_admin=True)
    assert client.get("/status").status_code == 200
    assert client.post("/replies/none/approve").status_code == 403
    assert client.post("/control/pause").status_code == 403


def test_mutations_allowed_when_admin_requirement_relaxed() -> None:
    client, _ = _client(require_admin=False)
    assert client.post("/control/pause").status_code == 200


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
