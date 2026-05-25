"""HTTP tests for the cross-scan cockpit activity feed."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.red_agent import dependencies as deps
from plugins.red_agent.routers import activity_router


class _StubPersistence:
    available = True

    def __init__(self) -> None:
        self.dsn = "stub"
        self.calls: list[dict[str, Any]] = []
        self.rows: list[dict[str, Any]] = []
        self.event_counts: dict[str, int] = {}
        self.count_calls: list[dict[str, Any]] = []
        self.bucket_rows: list[dict[str, Any]] = []
        self.bucket_calls: list[dict[str, Any]] = []

    async def list_recent_activity(
        self,
        *,
        events_prefix: list[str] | None = None,
        tenant_id: str | None = None,
        engagement_id: Any = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "events_prefix": events_prefix,
                "tenant_id": tenant_id,
                "engagement_id": engagement_id,
                "limit": limit,
            }
        )
        return list(self.rows)

    async def bucket_recent_events(
        self,
        *,
        events: list[str],
        tenant_id: str | None = None,
        engagement_id: Any = None,
        since_hours: int = 24,
        bucket: str = "hour",
    ) -> list[dict[str, Any]]:
        self.bucket_calls.append(
            {
                "events": events,
                "tenant_id": tenant_id,
                "engagement_id": engagement_id,
                "since_hours": since_hours,
                "bucket": bucket,
            }
        )
        return list(self.bucket_rows)

    async def count_recent_events(
        self,
        *,
        events: list[str],
        tenant_id: str | None = None,
        engagement_id: Any = None,
        since_hours: int = 24,
    ) -> dict[str, int]:
        self.count_calls.append(
            {
                "events": events,
                "tenant_id": tenant_id,
                "engagement_id": engagement_id,
                "since_hours": since_hours,
            }
        )
        return {e: self.event_counts.get(e, 0) for e in events}


class _StubAgent:
    def __init__(self, persistence: _StubPersistence) -> None:
        self.persistence = persistence


@pytest.fixture()
def http() -> tuple[TestClient, _StubPersistence]:
    p = _StubPersistence()
    agent = _StubAgent(p)

    app = FastAPI()
    app.include_router(activity_router)

    async def _allow() -> None:
        return None

    app.dependency_overrides[deps._viewer_dep] = _allow
    app.dependency_overrides[deps.get_red_agent] = lambda: agent
    return TestClient(app), p


def test_cockpit_flag_uses_curated_prefixes(
    http: tuple[TestClient, _StubPersistence],
) -> None:
    client, p = http
    resp = client.get("/activity?cockpit=true")
    assert resp.status_code == 200
    call = p.calls[-1]
    assert "scan.critic_" in (call["events_prefix"] or [])
    assert "scan.roe_" in (call["events_prefix"] or [])


def test_engagement_id_passed_to_persistence(
    http: tuple[TestClient, _StubPersistence],
) -> None:
    client, p = http
    eng_id = uuid4()
    resp = client.get(f"/activity?cockpit=true&engagement_id={eng_id}")
    assert resp.status_code == 200
    call = p.calls[-1]
    assert str(call["engagement_id"]) == str(eng_id)


def test_explicit_event_prefix_overrides_cockpit(
    http: tuple[TestClient, _StubPersistence],
) -> None:
    client, p = http
    resp = client.get("/activity?cockpit=true&event_prefix=scan.guardrail_")
    assert resp.status_code == 200
    assert p.calls[-1]["events_prefix"] == ["scan.guardrail_"]


def test_governance_stats_aggregates_totals(
    http: tuple[TestClient, _StubPersistence],
) -> None:
    client, p = http
    p.event_counts = {
        "scan.roe_violation": 2,
        "scan.critic_veto": 3,
        "scan.guardrail_violation": 1,
        "scan.hitl_denied": 1,
        "scan.roe_adjusted": 4,
        "scan.critic_amended": 5,
        "scan.hitl_timeout": 2,
    }
    resp = client.get("/activity/governance-stats?since_hours=12")
    assert resp.status_code == 200
    body = resp.json()
    assert body["window_hours"] == 12
    assert body["totals"]["violations"] == 2 + 3 + 1 + 1
    assert body["totals"]["adjustments"] == 4 + 5
    assert body["totals"]["hitl_timeouts"] == 2
    assert body["counts"]["scan.critic_veto"] == 3


def test_governance_stats_passes_engagement_id_through(
    http: tuple[TestClient, _StubPersistence],
) -> None:
    client, p = http
    eng_id = uuid4()
    resp = client.get(f"/activity/governance-stats?engagement_id={eng_id}")
    assert resp.status_code == 200
    assert str(p.count_calls[-1]["engagement_id"]) == str(eng_id)


def test_governance_trend_aggregates_by_bucket(
    http: tuple[TestClient, _StubPersistence],
) -> None:
    client, p = http
    bucket1 = datetime(2026, 4, 29, 18, tzinfo=timezone.utc)
    bucket2 = datetime(2026, 4, 29, 19, tzinfo=timezone.utc)
    p.bucket_rows = [
        {"bucket": bucket1, "event": "scan.critic_veto", "count": 2},
        {"bucket": bucket1, "event": "scan.roe_adjusted", "count": 1},
        {"bucket": bucket2, "event": "scan.hitl_timeout", "count": 3},
    ]
    resp = client.get("/activity/governance-trend?since_hours=12&bucket=hour")
    assert resp.status_code == 200
    body = resp.json()
    assert body["bucket"] == "hour"
    points = {p["ts"]: p for p in body["series"]}
    assert points[bucket1.isoformat()]["violations"] == 2
    assert points[bucket1.isoformat()]["adjustments"] == 1
    assert points[bucket2.isoformat()]["hitl_timeouts"] == 3


def test_governance_stats_zero_when_no_events(
    http: tuple[TestClient, _StubPersistence],
) -> None:
    client, _ = http
    resp = client.get("/activity/governance-stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["totals"]["violations"] == 0
    assert body["totals"]["adjustments"] == 0


def test_response_includes_iso_timestamps(
    http: tuple[TestClient, _StubPersistence],
) -> None:
    client, p = http
    p.rows = [
        {
            "id": 1,
            "scan_id": str(uuid4()),
            "actor": "red_agent",
            "event": "scan.critic_veto",
            "payload": {"reason": "out of scope"},
            "created_at": datetime(2026, 4, 29, 18, 0, tzinfo=timezone.utc),
        }
    ]
    resp = client.get("/activity?cockpit=true")
    body = resp.json()
    assert body[0]["created_at"].startswith("2026-04-29T18:00")
    assert body[0]["event"] == "scan.critic_veto"
