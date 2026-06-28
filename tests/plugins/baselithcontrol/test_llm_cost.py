"""Tests for per-plugin LLM cost attribution (ledger + token-sink wrapper)."""

from __future__ import annotations

import contextvars

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
    ledger.record("bot", "gpt-5", prompt_tokens=1000, completion_tokens=500)
    _, rows = ledger.snapshot()
    row = rows[0]
    assert row["plugin"] == "bot" and row["calls"] == 1
    assert row["prompt_tokens"] == 1000 and row["completion_tokens"] == 500
    assert abs(row["cost_usd"] - (1000 * 10 + 500 * 30) / 1e6) < 1e-9


def test_ledger_streaming_chunks_dont_inflate_call_count() -> None:
    ledger = LlmCostLedger()
    ledger.record("bot", "gpt-5", 300, 0)  # prompt side → counts as 1 call
    for _ in range(3):
        ledger.record("bot", "gpt-5", 0, 10)  # completion chunks → no new call
    _, rows = ledger.snapshot()
    row = rows[0]
    assert row["calls"] == 1
    assert row["completion_tokens"] == 30 and row["prompt_tokens"] == 300


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
    base = before.get(("pluginX", "gpt-4o"), {"prompt_tokens": 0, "completion_tokens": 0})
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
    assert _resolve_plugin({"path": "/baselithbrain/api/chat", "app": root}) == "baselithbrain"
    assert _resolve_plugin({"path": "/baselithbrain", "app": root}) == "baselithbrain"
    assert _resolve_plugin({"path": "/other/route", "app": root}) is None


def test_install_is_idempotent_and_wraps_sink() -> None:
    assert install_llm_cost_tracking() is True
    assert install_llm_cost_tracking() is True  # second call is a no-op
    import core.services.llm.service as mod

    # The sink still forwards (wrapper calls the original) and records usage.
    mod._report_tokens_to_middleware(10, model="input")
    mod._report_tokens_to_middleware(5, model="gpt-4o")
    rows = {(r["plugin"], r["model"]) for r in get_llm_ledger().snapshot()[1]}
    assert any(model == "gpt-4o" for _, model in rows)
