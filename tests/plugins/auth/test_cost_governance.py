"""Tests for per-user LLM cost governance (pure logic + metering/enforcement).

No database: the persistence layer is faked and injected into the tracker, so
metering, the input/output pairing, and cap enforcement are exercised offline.
"""

from __future__ import annotations

import contextvars

import pytest

from core.context import set_user_context
from plugins.auth.cost import (
    UsageStatus,
    compute_status,
    micros_to_usd,
    usd_to_micros,
)
from plugins.auth.cost import tracker as trk


# ----- pure money + status logic -----------------------------------------


def test_usd_micros_roundtrip() -> None:
    assert usd_to_micros(20.0) == 20_000_000
    assert usd_to_micros(None) is None
    assert micros_to_usd(20_000_000) == 20.0
    assert micros_to_usd(None) is None
    # sub-cent precision survives (a tiny LLM call)
    assert usd_to_micros(0.0006) == 600


def test_compute_status_thresholds() -> None:
    # uncapped → always ok, no percentage
    assert compute_status(99, None, 80) == (UsageStatus.ok, None)
    # below warn
    assert compute_status(50, 100, 80) == (UsageStatus.ok, 50)
    # at/above warn but below 100 → warning
    assert compute_status(80, 100, 80) == (UsageStatus.warning, 80)
    assert compute_status(99, 100, 80) == (UsageStatus.warning, 99)
    # at/above cap → blocked
    assert compute_status(100, 100, 80) == (UsageStatus.blocked, 100)
    assert compute_status(150, 100, 80) == (UsageStatus.blocked, 150)


# ----- metering + enforcement (faked persistence) ------------------------


class _FakePersistence:
    def __init__(self, cap_micros, spend_micros=0, enforce=True, warn=80) -> None:
        self._cap = cap_micros
        self._spend = spend_micros
        self._enforce = enforce
        self._warn = warn
        self.records: list[dict] = []

    def effective_cap_micros(self, user_id):
        return self._cap

    def monthly_spend_micros(self, user_id):
        return self._spend

    def get_cost_policy(self):
        return {"enforce": self._enforce, "warn_threshold_pct": self._warn}

    def record_usage(self, user_id, *, spend_micros, prompt_tokens, completion_tokens):
        self.records.append(
            {
                "user_id": user_id,
                "spend_micros": spend_micros,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
        )


def _with_fake(monkeypatch, fake) -> None:
    monkeypatch.setattr(trk, "_persistence", lambda: fake)
    trk.invalidate_cache()


def test_meter_records_spend_for_authenticated_user(monkeypatch) -> None:
    fake = _FakePersistence(cap_micros=None)
    _with_fake(monkeypatch, fake)

    def call() -> None:
        set_user_context("alice")
        trk.meter(1000, "input")  # prompt side
        trk.meter(500, "gpt-5")  # completion side (10/M in, 30/M out)

    contextvars.copy_context().run(call)
    assert len(fake.records) == 1
    rec = fake.records[0]
    assert rec["user_id"] == "alice"
    assert rec["prompt_tokens"] == 1000 and rec["completion_tokens"] == 500
    # cost = (1000*10 + 500*30)/1e6 USD = 0.025 → 25_000 micros
    assert rec["spend_micros"] == 25_000


def test_meter_skips_unauthenticated(monkeypatch) -> None:
    fake = _FakePersistence(cap_micros=None)
    _with_fake(monkeypatch, fake)
    # no user bound in this fresh context
    contextvars.copy_context().run(
        lambda: (trk.meter(1000, "input"), trk.meter(5, "gpt-5"))
    )
    assert fake.records == []


def test_enforcement_blocks_when_over_cap(monkeypatch) -> None:
    # spend already at the cap → the input report must raise to block the call
    fake = _FakePersistence(cap_micros=10_000, spend_micros=10_000, enforce=True)
    _with_fake(monkeypatch, fake)

    def call() -> None:
        set_user_context("bob")
        trk.meter(100, "input")

    with pytest.raises(trk.BudgetExceededError):
        contextvars.copy_context().run(call)


def test_enforcement_disabled_does_not_block(monkeypatch) -> None:
    fake = _FakePersistence(cap_micros=10_000, spend_micros=99_999, enforce=False)
    _with_fake(monkeypatch, fake)

    def call() -> None:
        set_user_context("bob")
        trk.meter(100, "input")  # over cap but enforce=False → no raise

    contextvars.copy_context().run(call)  # should not raise


def test_under_cap_allows_call(monkeypatch) -> None:
    fake = _FakePersistence(cap_micros=1_000_000, spend_micros=10_000, enforce=True)
    _with_fake(monkeypatch, fake)

    def call() -> None:
        set_user_context("carol")
        trk.meter(100, "input")  # well under cap → no raise

    contextvars.copy_context().run(call)


def test_admin_is_never_blocked(monkeypatch) -> None:
    # Even at/over a cap, an admin is uncapped → no enforcement raise.
    fake = _FakePersistence(cap_micros=10_000, spend_micros=999_999, enforce=True)
    _with_fake(monkeypatch, fake)
    monkeypatch.setattr(
        "plugins.auth.cost._admin.is_unlimited_user", lambda uid: uid == "root"
    )

    def admin_call() -> None:
        set_user_context("root")
        trk.meter(100, "input")  # admin → must NOT raise despite being over cap

    contextvars.copy_context().run(admin_call)  # no exception = pass

    # a non-admin in the same state is still blocked
    trk.invalidate_cache()

    def user_call() -> None:
        set_user_context("dave")
        trk.meter(100, "input")

    with pytest.raises(trk.BudgetExceededError):
        contextvars.copy_context().run(user_call)
