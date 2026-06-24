"""System-tier visibility gating in the control-plane inventory.

Framework / infrastructure plugins (manifest ``system: true``) are admin-only by
default and must be hidden from ordinary users unless the central RBAC policy
grants them — least privilege, enforced server-side at the aggregator. Ordinary
('application') plugins keep their default-allow visibility and are never touched
by the ``system_allow`` predicate. These tests pin that boundary at the pure
projection layer, without standing up the FastAPI app or the auth subsystem.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from plugins.baselithcontrol.service.aggregator import ControlAggregator


class FakeRegistry:
    """Minimal registry double exposing only what the aggregator reads."""

    def __init__(self, active: set[str]) -> None:
        self._active = active

    def list_plugins(self) -> list[dict]:
        return [{"name": n, "initialized": True} for n in sorted(self._active)]

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
        return {"healthy": True, "plugins": {}}

    def get_all_static_paths(self) -> dict:
        return {}

    def get_discovered_plugin(self, name: str) -> None:
        return None


@pytest.fixture
def aggregator(monkeypatch) -> ControlAggregator:
    """Aggregator over two active plugins where ``infra`` is system-tier.

    Disk-backed synthesis is stubbed out and ``is_system_plugin`` is forced so
    the projection is deterministic without any manifest on disk.
    """
    reg = FakeRegistry(active={"app", "infra"})
    monkeypatch.setattr(
        "plugins.baselithcontrol.service.aggregator.read_all", lambda: {}
    )
    monkeypatch.setattr(
        "plugins.baselithcontrol.service.aggregator.list_installed_plugins",
        lambda: [],
    )
    monkeypatch.setattr(
        "plugins.baselithcontrol.service.widgets.is_system_plugin",
        lambda name: name == "infra",
    )
    return ControlAggregator(reg)


def test_tier_reflects_system_flag(aggregator: ControlAggregator) -> None:
    tiers = {c.name: c.tier for c in aggregator.inventory().plugins}
    assert tiers == {"app": "application", "infra": "system"}


def test_admin_sees_system_plugins(aggregator: ControlAggregator) -> None:
    # ``system_allow=None`` is the admin scope: no system gating at all.
    names = [c.name for c in aggregator.inventory(system_allow=None).plugins]
    assert names == ["app", "infra"]


def test_ungranted_user_loses_system_plugins(aggregator: ControlAggregator) -> None:
    # A non-admin with no grant: the system plugin is hidden, the feature
    # plugin stays (default-allow is never touched for the application tier).
    names = [
        c.name for c in aggregator.inventory(system_allow=lambda _n: False).plugins
    ]
    assert names == ["app"]


def test_granted_user_regains_system_plugin(aggregator: ControlAggregator) -> None:
    names = [
        c.name
        for c in aggregator.inventory(system_allow=lambda n: n == "infra").plugins
    ]
    assert names == ["app", "infra"]


def test_overview_counts_follow_system_scope(aggregator: ControlAggregator) -> None:
    admin = aggregator.overview(system_allow=None)
    user = aggregator.overview(system_allow=lambda _n: False)
    # The hidden system plugin drops out of the non-admin's head-band totals too.
    assert admin.total == 2
    assert user.total == 1
