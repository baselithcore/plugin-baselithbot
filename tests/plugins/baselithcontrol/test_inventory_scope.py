"""Authorization scope of the control-plane inventory projection.

Ordinary users must only ever be shown **active** plugins; disabled, failed and
not-yet-activated plugins are operational state reserved for admins (the only
role allowed to act on them). These tests pin that boundary at the aggregator —
the pure projection layer — without standing up the FastAPI app.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from plugins.baselithcontrol.api_models import PluginState
from plugins.baselithcontrol.service.aggregator import ControlAggregator


class FakeRegistry:
    """Minimal registry double exposing only what the aggregator reads."""

    def __init__(self, rows: list[dict], active: set[str], health: dict) -> None:
        self._rows = rows
        self._active = active
        self._health = health

    def list_plugins(self) -> list[dict]:
        return self._rows

    def get_all(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                metadata=SimpleNamespace(
                    name=n, category="demo", version="1.0.0", description="", tags=[]
                )
            )
            for n in self._active
        ]

    def health_check(self) -> dict:
        return {"healthy": True, "plugins": self._health}

    def get_all_static_paths(self) -> dict:
        return {}

    def get_discovered_plugin(self, name: str) -> None:
        return None


@pytest.fixture
def aggregator(monkeypatch) -> ControlAggregator:
    """Aggregator over a registry with one card in each lifecycle state.

    Disk-backed synthesis (config file + on-disk manifests) is stubbed out so
    the projection is deterministic and the test stays a pure unit.
    """
    rows = [
        {"name": "alpha", "initialized": True},  # active
        {"name": "beta", "initialized": False},  # discovered
        {"name": "gamma", "initialized": True},  # health → failed
        {"name": "epsilon", "initialized": False},  # config-off → disabled
    ]
    health = {"gamma": {"status": "unhealthy"}}
    reg = FakeRegistry(rows, active={"alpha"}, health=health)

    monkeypatch.setattr(
        "plugins.baselithcontrol.service.aggregator.read_all",
        lambda: {"epsilon": False},
    )
    monkeypatch.setattr(
        "plugins.baselithcontrol.service.aggregator.list_installed_plugins",
        lambda: [],
    )
    return ControlAggregator(reg)


def test_admin_scope_sees_all_states(aggregator: ControlAggregator) -> None:
    cards = aggregator.inventory(include_inactive=True).plugins
    by_name = {c.name: c.state for c in cards}
    assert by_name == {
        "alpha": PluginState.active,
        "beta": PluginState.discovered,
        "gamma": PluginState.failed,
        "epsilon": PluginState.disabled,
    }


def test_user_scope_sees_only_active(aggregator: ControlAggregator) -> None:
    cards = aggregator.inventory(include_inactive=False).plugins
    assert [c.name for c in cards] == ["alpha"]
    assert all(c.state == PluginState.active for c in cards)


def test_default_scope_is_full(aggregator: ControlAggregator) -> None:
    # Back-compat: the default keeps the full catalog (admin-equivalent).
    assert len(aggregator.inventory().plugins) == 4


def test_overview_counts_follow_scope(aggregator: ControlAggregator) -> None:
    admin = aggregator.overview(include_inactive=True)
    user = aggregator.overview(include_inactive=False)
    assert admin.total == 4 and admin.down == 1
    assert user.total == 1 and user.down == 0


def test_ui_registry_hides_inactive_surfaces(aggregator: ControlAggregator) -> None:
    # No static paths in the double → no surfaces either way, but the call must
    # honour the scope flag without error and never leak a non-active surface.
    assert aggregator.ui_registry(include_inactive=False) == []
