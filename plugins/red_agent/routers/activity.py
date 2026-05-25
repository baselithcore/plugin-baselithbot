"""Cross-scan activity feed for the operator cockpit.

Surfaces the audit-log events that matter most to a red-team operator
in real time: RoE adjustments, critic vetoes, HITL approvals, scan
status changes. Distinct from ``/targets/{id}/activity`` (per-target)
and ``/findings/{id}/evidence`` (per-finding) — this endpoint is the
firehose the Dashboard widget reads from.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from core.context import get_current_tenant_id
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.dependencies import get_red_agent, require_viewer

router = APIRouter(prefix="/activity", tags=["red-agent", "activity"])


_DEFAULT_COCKPIT_PREFIXES = [
    "scan.roe_",
    "scan.critic_",
    "scan.hitl_",
    "scan.guardrail_",
    "scan.cancel",
]

_GOVERNANCE_EVENTS = [
    "scan.roe_violation",
    "scan.roe_adjusted",
    "scan.critic_veto",
    "scan.critic_amended",
    "scan.guardrail_violation",
    "scan.hitl_denied",
    "scan.hitl_timeout",
]


def _tenant() -> str | None:
    try:
        return get_current_tenant_id()
    except Exception:  # noqa: BLE001
        return None


@router.get("", dependencies=[require_viewer()])
async def list_activity(
    agent: RedAgent = Depends(get_red_agent),
    event_prefix: list[str] | None = Query(default=None),
    limit: int = 100,
    cockpit: bool = False,
    engagement_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """Recent audit-log events.

    * ``event_prefix=scan.critic_`` (repeatable) filters by prefix.
    * ``cockpit=true`` applies the curated prefix list used by the
      Dashboard cockpit widget.
    * ``engagement_id`` scopes the feed to a specific engagement.
    """
    prefixes: list[str] | None
    if cockpit and not event_prefix:
        prefixes = list(_DEFAULT_COCKPIT_PREFIXES)
    else:
        prefixes = event_prefix
    rows = await agent.persistence.list_recent_activity(
        events_prefix=prefixes,
        tenant_id=_tenant(),
        engagement_id=engagement_id,
        limit=limit,
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        if r.get("created_at") is not None:
            r["created_at"] = r["created_at"].isoformat()
        out.append(r)
    return out


@router.get("/governance-stats", dependencies=[require_viewer()])
async def governance_stats(
    agent: RedAgent = Depends(get_red_agent),
    since_hours: int = 24,
    engagement_id: UUID | None = None,
) -> dict[str, Any]:
    """Trailing-window counts for RoE / critic / HITL governance events.

    Drives the cockpit KPI tiles (omit ``engagement_id`` for a global
    view) and the per-engagement governance card.
    """
    counts = await agent.persistence.count_recent_events(
        events=list(_GOVERNANCE_EVENTS),
        tenant_id=_tenant(),
        engagement_id=engagement_id,
        since_hours=since_hours,
    )
    totals = {
        "violations": (
            counts.get("scan.roe_violation", 0)
            + counts.get("scan.critic_veto", 0)
            + counts.get("scan.guardrail_violation", 0)
            + counts.get("scan.hitl_denied", 0)
        ),
        "adjustments": (
            counts.get("scan.roe_adjusted", 0) + counts.get("scan.critic_amended", 0)
        ),
        "hitl_timeouts": counts.get("scan.hitl_timeout", 0),
    }
    return {"window_hours": since_hours, "counts": counts, "totals": totals}


@router.get("/governance-trend", dependencies=[require_viewer()])
async def governance_trend(
    agent: RedAgent = Depends(get_red_agent),
    since_hours: int = 24,
    bucket: str = "hour",
    engagement_id: UUID | None = None,
) -> dict[str, Any]:
    """Time-bucketed governance event counts for sparkline charts.

    Returns one entry per bucket with the three roll-up totals
    (violations, adjustments, hitl_timeouts). Buckets with zero
    events are omitted; the UI fills gaps when rendering.
    """
    rows = await agent.persistence.bucket_recent_events(
        events=list(_GOVERNANCE_EVENTS),
        tenant_id=_tenant(),
        engagement_id=engagement_id,
        since_hours=since_hours,
        bucket=bucket,
    )
    by_bucket: dict[str, dict[str, int]] = {}
    for row in rows:
        ts = row["bucket"]
        ts_iso = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        slot = by_bucket.setdefault(
            ts_iso,
            {"violations": 0, "adjustments": 0, "hitl_timeouts": 0},
        )
        ev = row["event"]
        n = row["count"]
        if ev in (
            "scan.roe_violation",
            "scan.critic_veto",
            "scan.guardrail_violation",
            "scan.hitl_denied",
        ):
            slot["violations"] += n
        elif ev in ("scan.roe_adjusted", "scan.critic_amended"):
            slot["adjustments"] += n
        elif ev == "scan.hitl_timeout":
            slot["hitl_timeouts"] += n
    series = [{"ts": ts, **buckets} for ts, buckets in sorted(by_bucket.items())]
    return {"window_hours": since_hours, "bucket": bucket, "series": series}
