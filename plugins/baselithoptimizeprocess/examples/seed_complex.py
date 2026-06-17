"""Seed a COMPLEX process to exercise the harder analysis paths.

Creates an insurance ``claims-handling`` process with the structures a real
enterprise flow has — a triage decision, a parallel fraud/damage assessment, a
documentation rework loop, stacked approvals, and a reject branch — plus rich
cost + multi-KPI data. Then mines a ``procurement`` process from a multi-variant
event log. Together they show off: parallelism-aware simulation, rework/loop
detection, structural + cost optimization, multi-KPI monitoring with a breach
forecast, what-if, and a governed apply.

Usage::

    python plugins/baselithoptimizeprocess/examples/seed_complex.py
    BOP_API=... BOP_TENANT=... python .../seed_complex.py
"""

from __future__ import annotations

import os

import httpx

API = os.getenv("BOP_API", "http://localhost:8000/api/baselithoptimizeprocess")
TENANT = os.getenv("BOP_TENANT", "default")
_HEADERS = {"X-Tenant-ID": TENANT, "X-Actor-ID": "demo-seeder"}


def _node(
    nid: str, name: str, kind: str, rate: float, secs: float, rework: float = 0.0
) -> dict:
    return {
        "id": nid,
        "name": name,
        "kind": kind,
        "cost": {
            "labor_cost_per_hour": rate,
            "avg_handling_seconds": secs,
            "rework_rate": rework,
            "fixed_cost": 0.0,
        },
    }


_CLAIMS_NODES: list[dict] = [
    _node("intake", "First Notice of Loss", "start", 40, 600),
    _node("register", "Register Claim", "task", 45, 900),
    _node("triage", "Triage Severity", "decision", 70, 600),
    _node("fast_approve", "Fast-track Approve", "task", 70, 600),
    _node("fraud", "Fraud Check", "parallel", 95, 2400, 0.15),
    _node("damage", "Damage Assessment", "parallel", 85, 3600),
    _node("consolidate", "Consolidate Findings", "parallel", 60, 900),
    _node("request_docs", "Request Documents", "task", 35, 600),
    _node("doc_review", "Review Documents", "task", 55, 1800, 0.4),
    _node("adjuster", "Adjuster Review", "task", 90, 3000),
    _node("decision_gate", "Approve or Reject?", "decision", 80, 600),
    _node("mgr_approve", "Manager Approval", "task", 120, 1200),
    _node("snr_approve", "Senior Approval", "task", 160, 1500),
    _node("payout", "Issue Payout", "task", 50, 900),
    _node("reject", "Reject Claim", "task", 60, 900),
    _node("notify", "Notify Customer", "task", 30, 300),
    _node("close", "Close Claim", "end", 30, 300),
]

_CLAIMS_EDGES: list[dict] = [
    {"source": "intake", "target": "register"},
    {"source": "register", "target": "triage"},
    {"source": "triage", "target": "fast_approve", "condition": "low severity"},
    {"source": "triage", "target": "fraud", "condition": "standard"},
    {"source": "triage", "target": "damage", "condition": "standard"},
    {"source": "fast_approve", "target": "payout"},
    {"source": "fraud", "target": "consolidate"},
    {"source": "damage", "target": "consolidate"},
    {"source": "consolidate", "target": "request_docs"},
    {"source": "request_docs", "target": "doc_review"},
    {"source": "doc_review", "target": "request_docs", "condition": "incomplete"},
    {"source": "doc_review", "target": "adjuster", "condition": "complete"},
    {"source": "adjuster", "target": "decision_gate"},
    {"source": "decision_gate", "target": "mgr_approve", "condition": "approve"},
    {"source": "decision_gate", "target": "reject", "condition": "reject"},
    {"source": "mgr_approve", "target": "snr_approve"},
    {"source": "snr_approve", "target": "payout"},
    {"source": "payout", "target": "notify"},
    {"source": "reject", "target": "notify"},
    {"source": "notify", "target": "close"},
]

CLAIMS = {
    "id": "claims-handling",
    "name": "Insurance Claims Handling",
    "description": "FNOL -> triage -> parallel assessment -> approvals -> payout.",
    "currency": "EUR",
    "annual_case_volume": 48000,
    "nodes": _CLAIMS_NODES,
    "edges": _CLAIMS_EDGES,
    "kpis": [
        {
            "id": "cycle_days",
            "name": "Cycle time",
            "unit": "d",
            "direction": "minimize",
            "target": 10.0,
            "description": "FNOL to close.",
        },
        {
            "id": "reopen_rate",
            "name": "Reopen rate",
            "unit": "%",
            "direction": "minimize",
            "target": 8.0,
            "description": "Claims reopened after close.",
        },
        {
            "id": "csat",
            "name": "Customer satisfaction",
            "unit": "pts",
            "direction": "maximize",
            "target": 85.0,
            "description": "Post-claim survey score.",
        },
    ],
}

# cycle rising past 10d target (+anomaly); reopen healthy; csat sliding below 85.
_CYCLE = [7, 8, 8, 9, 10, 11, 12, 13, 14, 15, 60]
_REOPEN = [4.0, 5.0, 4.5, 6.0, 5.5]
_CSAT = [90, 88, 86, 84, 82, 80, 78]

# A variant that removes the senior approval and parallelises docs review out.
CLAIMS_V2 = {
    **CLAIMS,
    "name": "Claims Handling (lean approvals)",
    "nodes": [n for n in _CLAIMS_NODES if n["id"] != "snr_approve"],
    "edges": [
        e for e in _CLAIMS_EDGES if "snr_approve" not in (e["source"], e["target"])
    ]
    + [{"source": "mgr_approve", "target": "payout"}],
}

# Procurement event log: 6 cases, multiple variants, a revise loop, and a
# parallel PO-approval / vendor-onboarding pair (seen in both orders).
_PO_LOG = [
    (
        "p1",
        [
            "Requisition",
            "Approve PR",
            "Create PO",
            "Approve PO",
            "Onboard Vendor",
            "Receive",
            "Pay",
        ],
    ),
    (
        "p2",
        [
            "Requisition",
            "Approve PR",
            "Create PO",
            "Onboard Vendor",
            "Approve PO",
            "Receive",
            "Pay",
        ],
    ),
    (
        "p3",
        [
            "Requisition",
            "Revise PR",
            "Approve PR",
            "Create PO",
            "Approve PO",
            "Receive",
            "Pay",
        ],
    ),
    (
        "p4",
        [
            "Requisition",
            "Revise PR",
            "Revise PR",
            "Approve PR",
            "Create PO",
            "Approve PO",
            "Receive",
            "Pay",
        ],
    ),
    (
        "p5",
        [
            "Requisition",
            "Approve PR",
            "Create PO",
            "Approve PO",
            "Receive",
            "Dispute",
            "Receive",
            "Pay",
        ],
    ),
    (
        "p6",
        [
            "Requisition",
            "Approve PR",
            "Create PO",
            "Approve PO",
            "Onboard Vendor",
            "Receive",
            "Pay",
        ],
    ),
]


def _iso(step: int) -> str:
    minute = step * 30
    return f"2026-06-02T{minute // 60:02d}:{minute % 60:02d}:00Z"


def main() -> None:
    with httpx.Client(base_url=API, headers=_HEADERS, timeout=30.0) as client:
        _claims(client)
        _procurement(client)
    print(f"\nDone. Open {API}/ui/ — explore 'claims-handling' and 'procurement'.")


def _claims(client: httpx.Client) -> None:
    client.delete("/processes/claims-handling")
    client.post("/processes", json=CLAIMS).raise_for_status()
    print(
        f"[claims] registered ({len(_CLAIMS_NODES)} steps, decisions + parallel + rework loop)"
    )

    series = (
        [("cycle_days", v) for v in _CYCLE]
        + [("reopen_rate", v) for v in _REOPEN]
        + [("csat", v) for v in _CSAT]
    )
    for kpi_id, value in series:
        client.post(
            "/processes/claims-handling/metrics",
            json={
                "samples": [
                    {
                        "process_id": "claims-handling",
                        "kpi_id": kpi_id,
                        "value": float(value),
                    }
                ]
            },
        )
    print(
        f"[claims] ingested {len(series)} samples across 3 KPIs (cycle breach + csat slide + anomaly)"
    )

    client.post(
        "/processes/claims-handling/rules",
        json={
            "name": "Predict cycle breach",
            "trigger": {"type": "predicted_breach", "kpi_id": "cycle_days"},
            "action": {
                "type": "recommend_optimization",
                "message": "",
                "webhook_url": "",
            },
            "enabled": True,
        },
    )
    print("[claims] rule: predicted breach -> auto recommend optimization")

    proposals = client.post(
        "/processes/claims-handling/optimize",
        json={"context": "Reduce cycle time and approval cost", "max_proposals": 6},
    ).json()
    print(f"[claims] optimizer: {len(proposals)} proposal(s)")

    sim = client.get("/processes/claims-handling/simulate").json()
    print(
        f"[claims] baseline sim: cycle {sim['cycle_time_seconds']:.0f}s, cost {sim['cost_per_case']} EUR, bottleneck '{sim['bottleneck_node']}'"
    )
    cmp = client.post("/processes/claims-handling/simulate", json=CLAIMS_V2).json()
    print(
        f"[claims] what-if (lean approvals): cycle {cmp['cycle_time_pct']}%, cost {cmp['cost_pct']}%"
    )

    change = client.post(
        "/processes/claims-handling/apply",
        json={
            **CLAIMS_V2,
            "proposal_id": "",
            "guard": {"kpi_id": "cycle_days", "max_regression_pct": 20.0},
        },
    ).json()
    print(
        f"[claims] applied lean variant -> v{change['to_version']} ({change['status']}, guarded)"
    )


def _procurement(client: httpx.Client) -> None:
    client.delete("/processes/procurement")
    events = [
        {"case_id": cid, "activity": act, "timestamp": _iso(i)}
        for cid, seq in _PO_LOG
        for i, act in enumerate(seq)
    ]
    result = client.post(
        "/processes/mine",
        json={"id": "procurement", "name": "Procure to Pay", "events": events},
    ).json()
    print(
        f"[procurement] mined: {result['case_count']} cases, {len(result['variants'])} variants, "
        f"{int(result['rework_rate'] * 100)}% rework, concurrent {result['concurrent_activities']}, "
        f"self-loops {result['self_loops']}"
    )


if __name__ == "__main__":
    main()
