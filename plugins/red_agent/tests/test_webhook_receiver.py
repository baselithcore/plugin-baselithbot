"""WebhookReceiver tests — signature verification + event parsing + apply."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from uuid import UUID, uuid4

import pytest

from plugins.red_agent.integrations.webhook_receiver import (
    WebhookEvent,
    WebhookReceiver,
)
from plugins.red_agent.models import FindingState, FindingTriageUpdate


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# --- signature verification ------------------------------------------


def test_signature_required_rejects_missing_header() -> None:
    r = WebhookReceiver(enabled=True, secret="s", require_signature=True)
    assert r.verify_signature(b"x", None) is False


def test_signature_required_rejects_missing_secret() -> None:
    r = WebhookReceiver(enabled=True, secret=None, require_signature=True)
    assert r.verify_signature(b"x", "sha256=abc") is False


def test_signature_valid_passes() -> None:
    secret = "topsecret"
    body = b'{"x":1}'
    r = WebhookReceiver(enabled=True, secret=secret, require_signature=True)
    assert r.verify_signature(body, _sign(secret, body)) is True


def test_signature_mismatch_fails() -> None:
    secret = "topsecret"
    body = b'{"x":1}'
    r = WebhookReceiver(enabled=True, secret=secret, require_signature=True)
    assert r.verify_signature(body, _sign("wrong-secret", body)) is False


def test_signature_malformed_header_fails() -> None:
    r = WebhookReceiver(enabled=True, secret="s", require_signature=True)
    assert r.verify_signature(b"x", "not-a-sha256-prefix") is False


def test_signature_bypass_when_not_required() -> None:
    r = WebhookReceiver(enabled=True, secret=None, require_signature=False)
    assert r.verify_signature(b"x", None) is True


# --- parse_event -----------------------------------------------------


class _PersistenceStub:
    def __init__(self, *, by_ref: dict[str, UUID] | None = None) -> None:
        self.by_ref = by_ref or {}
        self.triage_calls: list[tuple[UUID, FindingTriageUpdate, str]] = []
        self.applied: bool = True

    async def find_by_external_ref(self, external_ref: str) -> UUID | None:
        return self.by_ref.get(external_ref)

    async def update_finding_triage(
        self, finding_id: UUID, update: FindingTriageUpdate, actor: str
    ) -> bool:
        self.triage_calls.append((finding_id, update, actor))
        return self.applied


class _AuditStub:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def record(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


@pytest.mark.asyncio
async def test_parse_event_resolves_external_ref() -> None:
    finding_id = uuid4()
    persistence = _PersistenceStub(by_ref={"JIRA-1": finding_id})
    r = WebhookReceiver(enabled=True, require_signature=False)
    body = json.dumps(
        {"external_ref": "JIRA-1", "state": "fixed", "actor": "ops"}
    ).encode()
    ev = await r.parse_event(body, persistence=persistence)  # type: ignore[arg-type]
    assert ev is not None
    assert ev.finding_id == finding_id
    assert ev.state == FindingState.FIXED
    assert ev.actor == "ops"


@pytest.mark.asyncio
async def test_parse_event_resolves_finding_id_directly() -> None:
    finding_id = uuid4()
    persistence = _PersistenceStub()
    r = WebhookReceiver(enabled=True, require_signature=False)
    body = json.dumps({"finding_id": str(finding_id), "state": "wontfix"}).encode()
    ev = await r.parse_event(body, persistence=persistence)  # type: ignore[arg-type]
    assert ev is not None
    assert ev.finding_id == finding_id
    assert ev.state == FindingState.WONTFIX


@pytest.mark.asyncio
async def test_parse_event_aliases_resolved_to_fixed() -> None:
    finding_id = uuid4()
    persistence = _PersistenceStub(by_ref={"X": finding_id})
    r = WebhookReceiver(enabled=True, require_signature=False)
    for alias in ("resolved", "closed", "Done"):
        body = json.dumps({"external_ref": "X", "state": alias}).encode()
        ev = await r.parse_event(body, persistence=persistence)  # type: ignore[arg-type]
        assert ev is not None
        assert ev.state == FindingState.FIXED


@pytest.mark.asyncio
async def test_parse_event_alias_in_progress_to_triaged() -> None:
    finding_id = uuid4()
    persistence = _PersistenceStub(by_ref={"X": finding_id})
    r = WebhookReceiver(enabled=True, require_signature=False)
    body = json.dumps({"external_ref": "X", "state": "in_progress"}).encode()
    ev = await r.parse_event(body, persistence=persistence)  # type: ignore[arg-type]
    assert ev is not None
    assert ev.state == FindingState.TRIAGED


@pytest.mark.asyncio
async def test_parse_event_unknown_state_returns_none_state() -> None:
    finding_id = uuid4()
    persistence = _PersistenceStub(by_ref={"X": finding_id})
    r = WebhookReceiver(enabled=True, require_signature=False)
    body = json.dumps({"external_ref": "X", "state": "garbage"}).encode()
    ev = await r.parse_event(body, persistence=persistence)  # type: ignore[arg-type]
    assert ev is not None
    assert ev.state is None


@pytest.mark.asyncio
async def test_parse_event_returns_none_when_external_ref_unresolved() -> None:
    persistence = _PersistenceStub(by_ref={})
    r = WebhookReceiver(enabled=True, require_signature=False)
    body = json.dumps({"external_ref": "MISSING-1", "state": "fixed"}).encode()
    ev = await r.parse_event(body, persistence=persistence)  # type: ignore[arg-type]
    assert ev is None


@pytest.mark.asyncio
async def test_parse_event_returns_none_on_invalid_json() -> None:
    persistence = _PersistenceStub()
    r = WebhookReceiver(enabled=True, require_signature=False)
    ev = await r.parse_event(b"not-json", persistence=persistence)  # type: ignore[arg-type]
    assert ev is None


@pytest.mark.asyncio
async def test_parse_event_returns_none_on_missing_reference() -> None:
    persistence = _PersistenceStub()
    r = WebhookReceiver(enabled=True, require_signature=False)
    body = json.dumps({"state": "fixed"}).encode()
    ev = await r.parse_event(body, persistence=persistence)  # type: ignore[arg-type]
    assert ev is None


# --- apply_event ----------------------------------------------------


@pytest.mark.asyncio
async def test_apply_event_calls_triage_and_audit() -> None:
    finding_id = uuid4()
    persistence = _PersistenceStub()
    audit = _AuditStub()
    r = WebhookReceiver(enabled=True, require_signature=False)
    ev = WebhookEvent(
        finding_id=finding_id,
        state=FindingState.FIXED,
        notes="closed via Jira",
        assignee="alice",
        actor="jira-webhook",
    )
    ok = await r.apply_event(ev, persistence=persistence, audit=audit)  # type: ignore[arg-type]
    assert ok is True
    assert len(persistence.triage_calls) == 1
    fid, update, actor = persistence.triage_calls[0]
    assert fid == finding_id
    assert update.state == FindingState.FIXED
    assert update.notes == "closed via Jira"
    assert update.assignee == "alice"
    assert actor == "jira-webhook"
    assert len(audit.events) == 1
    assert audit.events[0]["event"] == "soar.webhook_applied"
    assert audit.events[0]["payload"]["state"] == "fixed"
    assert audit.events[0]["payload"]["applied"] is True


@pytest.mark.asyncio
async def test_apply_event_audits_even_when_persistence_returns_false() -> None:
    finding_id = uuid4()
    persistence = _PersistenceStub()
    persistence.applied = False
    audit = _AuditStub()
    r = WebhookReceiver(enabled=True, require_signature=False)
    ev = WebhookEvent(finding_id=finding_id, state=FindingState.OPEN)
    ok = await r.apply_event(ev, persistence=persistence, audit=audit)  # type: ignore[arg-type]
    assert ok is False
    assert audit.events[0]["payload"]["applied"] is False
