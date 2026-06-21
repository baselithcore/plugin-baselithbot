"""Authorization scope of the control-plane inventory projection.

Ordinary users must not be shown **disabled** (explicitly turned-off) plugins —
those are an admin concern (only an admin can re-enable them). Everything else
stays visible to everyone: active, not-yet-activated (``discovered``) and
``failed`` plugins remain so the system-status section and status widgets keep
working for all users. These tests pin that boundary at the aggregator — the
pure projection layer — without standing up the FastAPI app.
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
    cards = aggregator.inventory(include_disabled=True).plugins
    by_name = {c.name: c.state for c in cards}
    assert by_name == {
        "alpha": PluginState.active,
        "beta": PluginState.discovered,
        "gamma": PluginState.failed,
        "epsilon": PluginState.disabled,
    }


def test_user_scope_hides_only_disabled(aggregator: ControlAggregator) -> None:
    cards = aggregator.inventory(include_disabled=False).plugins
    # Disabled is gone; active/discovered/failed stay so system status + widgets
    # keep working for ordinary users.
    assert [c.name for c in cards] == ["alpha", "beta", "gamma"]
    assert all(c.state != PluginState.disabled for c in cards)


def test_default_scope_is_full(aggregator: ControlAggregator) -> None:
    # Back-compat: the default keeps the full catalog (admin-equivalent).
    assert len(aggregator.inventory().plugins) == 4


def test_overview_counts_follow_scope(aggregator: ControlAggregator) -> None:
    admin = aggregator.overview(include_disabled=True)
    user = aggregator.overview(include_disabled=False)
    # Both still surface the failed plugin (system status must reach everyone);
    # only the disabled card drops out of the user's totals.
    assert admin.total == 4 and admin.down == 1
    assert user.total == 3 and user.down == 1


def test_ui_registry_excludes_disabled_surfaces(aggregator: ControlAggregator) -> None:
    # No static paths in the double → no surfaces either way, but the call must
    # honour the scope flag without error and never leak a disabled surface.
    assert aggregator.ui_registry(include_disabled=False) == []
