"""Tests for per-plugin LLM cost attribution (ledger + token-sink wrapper)."""

from __future__ import annotations

import contextvars

import pytest

from plugins.baselithcontrol.service.cost_store import CostStore
from plugins.baselithcontrol.service.llm_cost import (
    UNBOUND,
    LlmCostLedger,
    attribute_tokens,
    current_plugin,
    get_llm_ledger,
    install_llm_cost_tracking,
)


def test_ledger_record_costs_and_calls() -> None:
    ledger = LlmCostLedger()
    # gpt-5 list price = 10/M in, 30/M out
    ledger.record("t1", "bot", "gpt-5", prompt_tokens=1000, completion_tokens=500)
    _, rows = ledger.snapshot()
    row = rows[0]
    assert row["plugin"] == "bot" and row["calls"] == 1
    assert row["prompt_tokens"] == 1000 and row["completion_tokens"] == 500
    assert abs(row["cost_usd"] - (1000 * 10 + 500 * 30) / 1e6) < 1e-9


def test_ledger_streaming_chunks_dont_inflate_call_count() -> None:
    ledger = LlmCostLedger()
    ledger.record("t1", "bot", "gpt-5", 300, 0)  # prompt side → counts as 1 call
    for _ in range(3):
        ledger.record("t1", "bot", "gpt-5", 0, 10)  # completion chunks → no new call
    _, rows = ledger.snapshot()
    row = rows[0]
    assert row["calls"] == 1
    assert row["completion_tokens"] == 30 and row["prompt_tokens"] == 300


def test_snapshot_scopes_by_tenant_and_aggregates_global() -> None:
    ledger = LlmCostLedger()
    ledger.record("alice", "bot", "gpt-5", 1000, 100)
    ledger.record("bob", "bot", "gpt-5", 2000, 200)

    # Per-tenant: only that tenant's usage, tenant dimension collapsed out.
    _, alice = ledger.snapshot("alice")
    assert len(alice) == 1
    assert alice[0]["prompt_tokens"] == 1000 and alice[0]["completion_tokens"] == 100

    # Global (admin): every tenant's usage merged by (plugin, model).
    _, glob = ledger.snapshot()
    assert len(glob) == 1  # same (plugin, model) → one merged row
    assert glob[0]["prompt_tokens"] == 3000 and glob[0]["completion_tokens"] == 300
    assert glob[0]["calls"] == 2

    # An unknown tenant sees nothing.
    _, none = ledger.snapshot("carol")
    assert none == []


def test_attribute_pairs_input_then_output() -> None:
    # Use a private ledger via the module singleton; isolate with a fresh context.
    def call(plugin: str) -> None:
        tok = current_plugin.set(plugin)
        try:
            attribute_tokens(1000, "input")  # prompt side, label "input"
            attribute_tokens(400, "gpt-4o")  # completion side, real model
        finally:
            current_plugin.reset(tok)

    before = {
        (r["plugin"], r["model"]): dict(r) for r in get_llm_ledger().snapshot()[1]
    }
    contextvars.copy_context().run(call, "pluginX")
    rows = {(r["plugin"], r["model"]): r for r in get_llm_ledger().snapshot()[1]}
    row = rows[("pluginX", "gpt-4o")]
    base = before.get(
        ("pluginX", "gpt-4o"), {"prompt_tokens": 0, "completion_tokens": 0}
    )
    assert row["prompt_tokens"] - base["prompt_tokens"] == 1000
    assert row["completion_tokens"] - base["completion_tokens"] == 400


def test_attribute_without_plugin_is_unbound() -> None:
    def call() -> None:
        attribute_tokens(100, "input")
        attribute_tokens(50, "gpt-4o")

    contextvars.copy_context().run(call)
    rows = {(r["plugin"], r["model"]) for r in get_llm_ledger().snapshot()[1]}
    assert (UNBOUND, "gpt-4o") in rows


def test_resolve_plugin_matches_mounted_subapp() -> None:
    # Sub-app-mounted plugins (baselithbrain, baselithwiki, …) have no router
    # prefix, so the meter must recover them from the app's Mount routes — else
    # their LLM spend is mis-attributed to "unbound".
    from starlette.applications import Starlette
    from starlette.routing import Mount

    from plugins.baselithcontrol.service.plugin_meter import _resolve_plugin

    sub = Starlette()
    root = Starlette(routes=[Mount("/baselithbrain", app=sub, name="baselithbrain")])
    assert (
        _resolve_plugin({"path": "/baselithbrain/api/chat", "app": root})
        == "baselithbrain"
    )
    assert _resolve_plugin({"path": "/baselithbrain", "app": root}) == "baselithbrain"
    assert _resolve_plugin({"path": "/other/route", "app": root}) is None


def test_drain_deltas_accumulates_then_clears() -> None:
    ledger = LlmCostLedger()
    ledger.record("t1", "bot", "gpt-5", 100, 50)
    ledger.record("t1", "bot", "gpt-5", 0, 20)  # streamed chunk, same call
    deltas = ledger.drain_deltas()
    assert len(deltas) == 1
    d = deltas[0]
    assert d["tenant"] == "t1" and d["plugin"] == "bot" and d["model"] == "gpt-5"
    assert d["prompt_tokens"] == 100 and d["completion_tokens"] == 70
    assert d["calls"] == 1
    # Drained → empty next time, but the absolute snapshot is left intact.
    assert ledger.drain_deltas() == []
    _, rows = ledger.snapshot()
    assert rows[0]["completion_tokens"] == 70 and rows[0]["calls"] == 1


def test_cost_store_degrades_without_db(monkeypatch: pytest.MonkeyPatch) -> None:
    # No database configured → the store must degrade (route falls back to the
    # in-memory ledger) rather than raise. flush() is a safe no-op.
    import core.db.connection as conn

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("no database configured")

    monkeypatch.setattr(conn, "get_cursor", boom)
    store = CostStore()
    assert store.available() is False
    store.flush(
        [
            {
                "tenant": "t",
                "plugin": "p",
                "model": "m",
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "cost_usd": 0.001,
                "calls": 1,
            }
        ]
    )  # must not raise


def test_install_is_idempotent_and_wraps_sink() -> None:
    assert install_llm_cost_tracking() is True
    assert install_llm_cost_tracking() is True  # second call is a no-op
    import core.services.llm.service as mod

    # The sink still forwards (wrapper calls the original) and records usage.
    mod._report_tokens_to_middleware(10, model="input")
    mod._report_tokens_to_middleware(5, model="gpt-4o")
    rows = {(r["plugin"], r["model"]) for r in get_llm_ledger().snapshot()[1]}
    assert any(model == "gpt-4o" for _, model in rows)
