"""Seed the running BaselithOptimizeProcess backend with a full demo tour.

Run it against a live server to populate EVERY dashboard tab and exercise every
capability, so you can explore the plugin end-to-end without entering anything by
hand.

Usage::

    python plugins/baselithoptimizeprocess/examples/seed_demo.py
    # custom server / tenant:
    BOP_API=http://localhost:8000/api/baselithoptimizeprocess \\
    BOP_TENANT=acme python plugins/baselithoptimizeprocess/examples/seed_demo.py

Creates three processes and walks the whole lifecycle:

* ``order-to-cash`` — costed + KPI-tracked. Metrics (rising trend → breach +
  forecast, plus an injected anomaly), automation rules (breach + predicted
  breach), optimizer pass with a proposal APPROVED, a metrics connector ingest,
  a what-if simulation, and a governed APPLY (with auto-rollback guard) that
  mints v2 — so Map, Monitor, Optimize, Automate, Simulate, Govern, and the
  exported report are all populated.
* ``support-tickets`` — discovered by mining an event log → Analyze tab
  (variants, rework loop, concurrent activities).
* ``invoice-approval`` — imported from BPMN XML → exercises the import path.

Idempotent: deletes the demo processes first, then recreates them.
"""

from __future__ import annotations

import os

import httpx

API = os.getenv("BOP_API", "http://localhost:8000/api/baselithoptimizeprocess")
TENANT = os.getenv("BOP_TENANT", "default")
_HEADERS = {"X-Tenant-ID": TENANT, "X-Actor-ID": "demo-seeder"}


def _cost(rate: float, secs: float, rework: float = 0.0) -> dict:
    return {
        "labor_cost_per_hour": rate,
        "avg_handling_seconds": secs,
        "rework_rate": rework,
        "fixed_cost": 0.0,
    }


def _node(nid: str, name: str, kind: str = "task", **cost: float) -> dict:
    node: dict = {"id": nid, "name": name, "kind": kind}
    if cost:
        node["cost"] = _cost(**cost)
    return node


_CYCLE_KPI = {
    "id": "cycle_hours",
    "name": "Cycle time",
    "unit": "h",
    "direction": "minimize",
    "target": 48.0,
    "description": "End-to-end order fulfilment time.",
}
_DEFECT_KPI = {
    "id": "defect_rate",
    "name": "Defect rate",
    "unit": "%",
    "direction": "minimize",
    "target": 5.0,
    "description": "Share of orders shipped with an error.",
}

ORDER_TO_CASH = {
    "id": "order-to-cash",
    "name": "Order to Cash",
    "description": "Quote -> order -> fulfil -> invoice, with stacked approvals.",
    "currency": "EUR",
    "annual_case_volume": 12000,
    "nodes": [
        _node("intake", "Receive Order", "start", rate=45, secs=600),
        _node("credit", "Credit Check", rate=55, secs=900, rework=0.2),
        _node("approve_mgr", "Manager Approval", rate=80, secs=1200),
        _node("approve_dir", "Director Approval", rate=120, secs=1500),
        _node("approve_fin", "Finance Approval", rate=110, secs=1500),
        _node("pick", "Pick Goods", rate=35, secs=1800),
        _node("pack", "Pack & Label", rate=35, secs=900),
        _node("ship", "Ship", "end", rate=40, secs=600),
    ],
    "edges": [
        {"source": "intake", "target": "credit"},
        {"source": "credit", "target": "approve_mgr"},
        {"source": "approve_mgr", "target": "approve_dir"},
        {"source": "approve_dir", "target": "approve_fin"},
        {"source": "approve_fin", "target": "pick"},
        {"source": "pick", "target": "pack"},
        {"source": "pack", "target": "ship"},
    ],
    "kpis": [_CYCLE_KPI, _DEFECT_KPI],
}

# A variant that consolidates the three approvals into one — the redesign we
# simulate and then apply as a governed change.
ORDER_TO_CASH_V2 = {
    **ORDER_TO_CASH,
    "name": "Order to Cash (single approval)",
    "nodes": [
        _node("intake", "Receive Order", "start", rate=45, secs=600),
        _node("credit", "Credit Check", rate=55, secs=900, rework=0.2),
        _node("approve", "Single Approval", rate=110, secs=1500),
        _node("pick", "Pick Goods", rate=35, secs=1800),
        _node("pack", "Pack & Label", rate=35, secs=900),
        _node("ship", "Ship", "end", rate=40, secs=600),
    ],
    "edges": [
        {"source": "intake", "target": "credit"},
        {"source": "credit", "target": "approve"},
        {"source": "approve", "target": "pick"},
        {"source": "pick", "target": "pack"},
        {"source": "pack", "target": "ship"},
    ],
}

# Cycle time trending across the 48h target → breach + forecast; last point is an
# injected anomaly spike for the anomaly detector.
_CYCLE_SERIES = [38, 40, 42, 44, 46, 49, 52, 55, 58, 61, 240]
_DEFECT_SERIES = [3.0, 4.0, 3.5, 4.2, 3.8, 4.1]

# Event log over the order-to-cash activity ids: 3 conforming + 1 deviating.
_O2C_LOG = [
    (
        "o1",
        [
            "intake",
            "credit",
            "approve_mgr",
            "approve_dir",
            "approve_fin",
            "pick",
            "pack",
            "ship",
        ],
    ),
    (
        "o2",
        [
            "intake",
            "credit",
            "approve_mgr",
            "approve_dir",
            "approve_fin",
            "pick",
            "pack",
            "ship",
        ],
    ),
    (
        "o3",
        [
            "intake",
            "credit",
            "approve_mgr",
            "approve_dir",
            "approve_fin",
            "pick",
            "pack",
            "ship",
        ],
    ),
    ("o4", ["intake", "credit", "ship"]),  # skipped approvals + fulfilment
]

# Support-ticket event log: variants + rework (Triage twice) + concurrency.
_TICKET_LOG = [
    ("t1", "Open", 0),
    ("t1", "Triage", 5),
    ("t1", "Diagnose", 20),
    ("t1", "Assign", 22),
    ("t1", "Resolve", 60),
    ("t1", "Close", 65),
    ("t2", "Open", 0),
    ("t2", "Triage", 4),
    ("t2", "Triage", 9),
    ("t2", "Assign", 15),
    ("t2", "Diagnose", 18),
    ("t2", "Resolve", 70),
    ("t2", "Close", 74),
    ("t3", "Open", 0),
    ("t3", "Triage", 6),
    ("t3", "Diagnose", 25),
    ("t3", "Assign", 27),
    ("t3", "Resolve", 50),
    ("t3", "Close", 53),
    ("t4", "Open", 0),
    ("t4", "Escalate", 8),
    ("t4", "Resolve", 90),
    ("t4", "Close", 95),
]

_INVOICE_BPMN = """<?xml version="1.0"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <process id="invoice" name="Invoice Approval">
    <startEvent id="recv" name="Receive Invoice"/>
    <task id="validate" name="Validate"/>
    <exclusiveGateway id="amount" name="Amount OK?"/>
    <task id="approve" name="Approve"/>
    <endEvent id="paid" name="Paid"/>
    <sequenceFlow id="f1" sourceRef="recv" targetRef="validate"/>
    <sequenceFlow id="f2" sourceRef="validate" targetRef="amount"/>
    <sequenceFlow id="f3" sourceRef="amount" targetRef="approve"/>
    <sequenceFlow id="f4" sourceRef="approve" targetRef="paid"/>
  </process>
</definitions>"""


def _iso(minute: int) -> str:
    return f"2026-06-01T{minute // 60:02d}:{minute % 60:02d}:00Z"


def main() -> None:
    with httpx.Client(base_url=API, headers=_HEADERS, timeout=30.0) as client:
        _order_to_cash(client)
        _mined(client)
        _imported(client)
    print(f"\nDone. Open {API}/ui/ and explore the three demo processes.")


def _order_to_cash(client: httpx.Client) -> None:
    client.delete("/processes/order-to-cash")
    client.post("/processes", json=ORDER_TO_CASH).raise_for_status()
    print("[order-to-cash] registered (v1)")

    for value in _CYCLE_SERIES:
        client.post(
            "/processes/order-to-cash/metrics",
            json={
                "samples": [
                    {
                        "process_id": "order-to-cash",
                        "kpi_id": "cycle_hours",
                        "value": float(value),
                    }
                ]
            },
        )
    print(
        f"[order-to-cash] ingested {len(_CYCLE_SERIES)} cycle samples (trend→breach + anomaly)"
    )

    # Defect-rate metrics via the CSV connector (exercises text ingestion).
    csv_text = "kpi_id,value\n" + "\n".join(f"defect_rate,{v}" for v in _DEFECT_SERIES)
    client.post(
        "/processes/order-to-cash/ingest",
        json={"text": csv_text, "kind": "metrics"},
    )
    print(
        f"[order-to-cash] connector ingested {len(_DEFECT_SERIES)} defect samples (CSV)"
    )

    for name, trigger in (
        ("Alert on cycle breach", {"type": "kpi_breach", "kpi_id": "cycle_hours"}),
        (
            "Predictive cycle alert",
            {"type": "predicted_breach", "kpi_id": "cycle_hours"},
        ),
    ):
        client.post(
            "/processes/order-to-cash/rules",
            json={
                "name": name,
                "trigger": trigger,
                "action": {"type": "alert", "message": name, "webhook_url": ""},
                "enabled": True,
            },
        )
    print("[order-to-cash] created 2 automation rules")

    proposals = client.post(
        "/processes/order-to-cash/optimize", json={"context": "", "max_proposals": 5}
    ).json()
    print(f"[order-to-cash] optimizer produced {len(proposals)} proposal(s)")
    if proposals:
        client.post(
            f"/proposals/{proposals[0]['id']}/approve", json={"note": "demo approval"}
        )
        print(f"[order-to-cash] approved proposal: {proposals[0]['title']}")

    events = [
        {"case_id": cid, "activity": act, "timestamp": _iso(i * 5)}
        for cid, seq in _O2C_LOG
        for i, act in enumerate(seq)
    ]
    conf = client.post(
        "/processes/order-to-cash/conformance", json={"events": events}
    ).json()
    print(
        f"[order-to-cash] conformance: fitness {conf['fitness']:.2f}, "
        f"alignment {conf['alignment_fitness']:.2f}, deviation cost {conf['deviation_cost']}"
    )

    cmp = client.post("/processes/order-to-cash/simulate", json=ORDER_TO_CASH_V2).json()
    print(
        "[order-to-cash] what-if (single approval): "
        f"cycle {cmp['cycle_time_pct']}% , cost {cmp['cost_pct']}%"
    )

    change = client.post(
        "/processes/order-to-cash/apply",
        json={
            **ORDER_TO_CASH_V2,
            "proposal_id": "",
            "guard": {"kpi_id": "cycle_hours", "max_regression_pct": 25.0},
        },
    ).json()
    print(
        f"[order-to-cash] applied governed change → v{change['to_version']} (status {change['status']})"
    )


def _mined(client: httpx.Client) -> None:
    client.delete("/processes/support-tickets")
    events = [
        {"case_id": c, "activity": a, "timestamp": _iso(m)} for c, a, m in _TICKET_LOG
    ]
    result = client.post(
        "/processes/mine",
        json={"id": "support-tickets", "name": "Support Tickets", "events": events},
    ).json()
    print(
        f"[support-tickets] mined: {result['case_count']} cases, "
        f"{len(result['variants'])} variants, {int(result['rework_rate'] * 100)}% rework, "
        f"concurrent {result['concurrent_activities']}"
    )


def _imported(client: httpx.Client) -> None:
    client.delete("/processes/invoice-approval")
    resp = client.post(
        "/processes/import",
        json={"id": "invoice-approval", "xml": _INVOICE_BPMN, "kpis": [_CYCLE_KPI]},
    )
    resp.raise_for_status()
    print(f"[invoice-approval] imported from BPMN ({len(resp.json()['nodes'])} steps)")


if __name__ == "__main__":
    main()
