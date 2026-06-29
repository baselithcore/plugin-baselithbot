"""Tests for the auth NIS2 incident-trail hooks (account lockout)."""

from __future__ import annotations

from types import SimpleNamespace

import plugins.auth.security_incidents as sec
from core.incidents import (
    IncidentSeverity,
    IncidentService,
    InMemoryIncidentStore,
)


def _use_fresh_service(monkeypatch) -> IncidentService:
    """Point the hook at an isolated in-memory incident service."""
    service = IncidentService(store=InMemoryIncidentStore())
    monkeypatch.setattr(sec, "get_incident_service", lambda: service)
    return service


def _set_enabled(monkeypatch, enabled: bool) -> None:
    # The hook reads only ``.enabled``; a stub avoids the aliased settings env.
    monkeypatch.setattr(
        sec, "get_incident_config", lambda: SimpleNamespace(enabled=enabled)
    )


async def test_lockout_noop_when_disabled(monkeypatch) -> None:
    service = _use_fresh_service(monkeypatch)
    _set_enabled(monkeypatch, False)

    await sec.report_account_lockout("u-1", 5, source_ip="1.2.3.4")

    assert await service.list_incidents() == []


async def test_lockout_records_incident_when_enabled(monkeypatch) -> None:
    service = _use_fresh_service(monkeypatch)
    _set_enabled(monkeypatch, True)

    await sec.report_account_lockout("u-1", 7, source_ip="9.9.9.9")

    incidents = await service.list_incidents()
    assert len(incidents) == 1
    inc = incidents[0]
    # Lockout belongs to the handling trail, not the regulatory reporting clock.
    assert inc.significant is False
    assert inc.severity == IncidentSeverity.MEDIUM
    assert inc.affected_systems == ["auth"]
    assert inc.affected_subjects == 1
    assert inc.details["event"] == "account_lockout"
    assert inc.details["user_id"] == "u-1"
    assert inc.details["failed_attempts"] == 7
    assert inc.details["source_ip"] == "9.9.9.9"
    # Non-significant incidents carry no reporting milestones.
    assert service.milestones(inc) == []


async def test_lockout_never_raises(monkeypatch) -> None:
    # A failure in the incident path must never propagate into the login flow.
    def _boom() -> None:
        raise RuntimeError("incident backend down")

    _set_enabled(monkeypatch, True)
    monkeypatch.setattr(sec, "get_incident_service", _boom)

    # Must swallow the error rather than raise.
    await sec.report_account_lockout("u-1", 5)
