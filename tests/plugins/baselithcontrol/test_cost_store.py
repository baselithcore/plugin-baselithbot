"""Durable cost ledger: UPSERT params, micro-USD conversion, DB re-probe TTL.

The store is the reason per-worker LLM spend survives restarts and sums across
workers; these pin the flush/read shaping against a fake cursor and the new
timed re-probe (a "no DB" verdict must expire, not be terminal).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest

import core.db.connection as conn
from plugins.baselithcontrol.service import cost_store as cs_mod
from plugins.baselithcontrol.service.cost_store import CostStore

_DELTA = {
    "tenant": "t1",
    "plugin": "bot",
    "model": "gpt-5",
    "prompt_tokens": 1000,
    "completion_tokens": 500,
    "cost_usd": 0.0125,  # → 12500 micro-USD
    "calls": 2,
}


class _FakeCursor:
    def __init__(self, sink: dict[str, Any]) -> None:
        self._sink = sink

    def execute(self, sql: str, params: Any = None) -> None:
        self._sink.setdefault("execute", []).append((sql, params))

    def executemany(self, sql: str, params: list[dict[str, Any]]) -> None:
        self._sink["upsert_params"] = params


def _fake_get_cursor(sink: dict[str, Any]):
    @contextmanager
    def _cm():
        yield _FakeCursor(sink)

    return _cm


def test_flush_converts_to_micro_usd_and_upserts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink: dict[str, Any] = {}
    monkeypatch.setattr(conn, "get_cursor", _fake_get_cursor(sink))
    store = CostStore()
    store.flush([_DELTA])
    params = sink["upsert_params"][0]
    assert params["cm"] == 12500  # 0.0125 USD → 12_500 micro-USD (integer, exact)
    assert params["pt"] == 1000 and params["ct"] == 500 and params["calls"] == 2
    assert params["tenant"] == "t1" and params["plugin"] == "bot"


def test_flush_noop_on_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    sink: dict[str, Any] = {}
    monkeypatch.setattr(conn, "get_cursor", _fake_get_cursor(sink))
    CostStore().flush([])
    assert "upsert_params" not in sink


def test_negative_probe_expires_and_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 1000.0}
    monkeypatch.setattr(cs_mod.time, "monotonic", lambda: clock["t"])

    calls = {"n": 0}

    def flaky_cursor():
        calls["n"] += 1
        if calls["n"] == 1:  # first probe fails → no DB
            raise RuntimeError("db down")

        @contextmanager
        def _cm():
            yield _FakeCursor({})

        return _cm()

    monkeypatch.setattr(conn, "get_cursor", flaky_cursor)
    store = CostStore()

    assert store.available() is False  # first probe: down
    # Within the re-probe window the verdict is cached (no second DB hit).
    clock["t"] += 10
    assert store.available() is False
    assert calls["n"] == 1

    # Past the window the store re-probes and recovers automatically.
    clock["t"] += cs_mod._REPROBE_SECONDS + 1
    assert store.available() is True
    assert calls["n"] == 2


def test_positive_probe_is_permanent(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def ok_cursor():
        calls["n"] += 1

        @contextmanager
        def _cm():
            yield _FakeCursor({})

        return _cm()

    monkeypatch.setattr(conn, "get_cursor", ok_cursor)
    store = CostStore()
    assert store.available() is True
    assert store.available() is True  # cached — no re-probe once healthy
    assert calls["n"] == 1
