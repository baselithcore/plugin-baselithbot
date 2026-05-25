"""Provider-specific webhook adapter tests (Jira / ServiceNow / Linear)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

import pytest

from plugins.red_agent.integrations.adapters import (
    JiraAdapter,
    LinearAdapter,
    ServiceNowAdapter,
    get_adapter,
)
from plugins.red_agent.integrations.webhook_receiver import WebhookReceiver
from plugins.red_agent.models import FindingState, FindingTriageUpdate


# --- Jira ------------------------------------------------------------


def test_jira_adapter_parses_done_status() -> None:
    payload: dict[str, Any] = {
        "issue": {
            "key": "RA-42",
            "fields": {
                "status": {"name": "Done"},
                "assignee": {"emailAddress": "alice@example.com"},
            },
        },
        "user": {"displayName": "Alice"},
    }
    out = JiraAdapter().parse(payload)
    assert out is not None
    assert out["external_ref"] == "RA-42"
    assert out["state"] == "fixed"
    assert out["assignee"] == "alice@example.com"
    assert out["actor"] == "Alice"


def test_jira_adapter_in_progress_maps_to_triaged() -> None:
    out = JiraAdapter().parse(
        {
            "issue": {
                "key": "RA-1",
                "fields": {"status": {"name": "In Progress"}},
            }
        }
    )
    assert out is not None
    assert out["state"] == "triaged"


def test_jira_adapter_returns_none_when_issue_missing() -> None:
    assert JiraAdapter().parse({"webhookEvent": "ping"}) is None


def test_jira_adapter_unknown_status_yields_no_state() -> None:
    out = JiraAdapter().parse(
        {"issue": {"key": "RA-2", "fields": {"status": {"name": "Mystery"}}}}
    )
    assert out is not None
    assert out["state"] is None


def test_jira_adapter_picks_comment_body_as_notes() -> None:
    out = JiraAdapter().parse(
        {
            "issue": {"key": "RA-3", "fields": {"status": {"name": "Closed"}}},
            "comment": {"body": "fixed in 1.2.3"},
        }
    )
    assert out is not None
    assert out["notes"] == "fixed in 1.2.3"


# --- ServiceNow -----------------------------------------------------


def test_servicenow_adapter_resolved_state() -> None:
    payload: dict[str, Any] = {
        "number": "INC0010001",
        "state": "6",
        "work_notes": "patched",
        "assigned_to": {"display_value": "Bob"},
        "sys_updated_by": "snow-rule",
    }
    out = ServiceNowAdapter().parse(payload)
    assert out is not None
    assert out["external_ref"] == "INC0010001"
    assert out["state"] == "fixed"
    assert out["notes"] == "patched"
    assert out["assignee"] == "Bob"
    assert out["actor"] == "snow-rule"


def test_servicenow_adapter_in_progress_state() -> None:
    out = ServiceNowAdapter().parse({"number": "INC1", "state": "2"})
    assert out is not None
    assert out["state"] == "triaged"


def test_servicenow_adapter_cancelled_to_wontfix() -> None:
    out = ServiceNowAdapter().parse({"number": "INC9", "state": "8"})
    assert out is not None
    assert out["state"] == "wontfix"


def test_servicenow_adapter_returns_none_without_number() -> None:
    assert ServiceNowAdapter().parse({"state": "6"}) is None


def test_servicenow_adapter_assignee_string_form() -> None:
    out = ServiceNowAdapter().parse(
        {"number": "INC2", "state": "6", "assigned_to": "alice"}
    )
    assert out is not None
    assert out["assignee"] == "alice"


# --- Linear ---------------------------------------------------------


def test_linear_adapter_completed_state() -> None:
    payload: dict[str, Any] = {
        "action": "update",
        "data": {
            "identifier": "RA-7",
            "state": {"type": "completed", "name": "Done"},
            "assignee": {"email": "carol@example.com"},
            "description": "shipped fix",
        },
        "actor": {"name": "Carol"},
    }
    out = LinearAdapter().parse(payload)
    assert out is not None
    assert out["external_ref"] == "RA-7"
    assert out["state"] == "fixed"
    assert out["assignee"] == "carol@example.com"
    assert out["notes"] == "shipped fix"
    assert out["actor"] == "Carol"


def test_linear_adapter_canceled_to_wontfix() -> None:
    out = LinearAdapter().parse(
        {"data": {"identifier": "RA-8", "state": {"type": "canceled"}}}
    )
    assert out is not None
    assert out["state"] == "wontfix"


def test_linear_adapter_started_to_triaged() -> None:
    out = LinearAdapter().parse(
        {"data": {"identifier": "RA-9", "state": {"type": "started"}}}
    )
    assert out is not None
    assert out["state"] == "triaged"


def test_linear_adapter_returns_none_when_data_missing() -> None:
    assert LinearAdapter().parse({"action": "ping"}) is None


# --- registry --------------------------------------------------------


def test_registry_lookup_case_insensitive() -> None:
    assert isinstance(get_adapter("JIRA"), JiraAdapter)
    assert isinstance(get_adapter("ServiceNow"), ServiceNowAdapter)
    assert isinstance(get_adapter("linear"), LinearAdapter)
    assert get_adapter("unknown") is None


# --- end-to-end via WebhookReceiver --------------------------------


class _PersistenceStub:
    def __init__(self, by_ref: dict[str, UUID]) -> None:
        self.by_ref = by_ref
        self.triage_calls: list[tuple[UUID, FindingTriageUpdate, str]] = []

    async def find_by_external_ref(self, external_ref: str) -> UUID | None:
        return self.by_ref.get(external_ref)

    async def update_finding_triage(
        self, finding_id: UUID, update: FindingTriageUpdate, actor: str
    ) -> bool:
        self.triage_calls.append((finding_id, update, actor))
        return True


@pytest.mark.asyncio
async def test_receiver_parses_jira_payload_with_adapter() -> None:
    finding_id = uuid4()
    persistence = _PersistenceStub({"RA-42": finding_id})
    receiver = WebhookReceiver(enabled=True, require_signature=False)
    body = json.dumps(
        {
            "issue": {
                "key": "RA-42",
                "fields": {"status": {"name": "Done"}},
            }
        }
    ).encode()
    ev = await receiver.parse_event(
        body,
        persistence=persistence,
        adapter=JiraAdapter(),  # type: ignore[arg-type]
    )
    assert ev is not None
    assert ev.finding_id == finding_id
    assert ev.state == FindingState.FIXED


@pytest.mark.asyncio
async def test_receiver_returns_none_when_adapter_yields_none() -> None:
    persistence = _PersistenceStub({})
    receiver = WebhookReceiver(enabled=True, require_signature=False)
    body = json.dumps({"webhookEvent": "ping"}).encode()  # missing issue key
    ev = await receiver.parse_event(
        body,
        persistence=persistence,
        adapter=JiraAdapter(),  # type: ignore[arg-type]
    )
    assert ev is None


@pytest.mark.asyncio
async def test_receiver_swallows_adapter_exception() -> None:
    persistence = _PersistenceStub({})
    receiver = WebhookReceiver(enabled=True, require_signature=False)

    class _BoomAdapter:
        name = "boom"

        def parse(self, payload: dict[str, Any]) -> dict[str, Any] | None:
            raise RuntimeError("kaboom")

    body = b'{"x": 1}'
    ev = await receiver.parse_event(
        body,
        persistence=persistence,
        adapter=_BoomAdapter(),  # type: ignore[arg-type]
    )
    assert ev is None
