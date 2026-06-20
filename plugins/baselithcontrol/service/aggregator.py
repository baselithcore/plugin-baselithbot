"""Read-side projection of the live plugin registry into wire views.

Pure, side-effect-free, and thread-safe (the registry guards its own state with
an ``RLock``). The aggregator never mutates anything — it composes the inventory
and status snapshots the dashboard renders, dynamically, from whatever plugins
happen to be loaded. No plugin is referenced by name.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.observability.logging import get_logger

from ..api_models import (
    EmbedSurface,
    HeadStat,
    InventoryView,
    OverviewView,
    PluginCardView,
    PluginState,
    StatusView,
)
from .config_store import read_all
from .manifests import list_installed_plugins, read_manifest
from .widgets import display_meta

logger = get_logger(__name__)


class ControlAggregator:
    """Read-only façade over ``app.state.plugin_registry``."""

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    # -- public surface ------------------------------------------------------
    def inventory(self, *, include_inactive: bool = True) -> InventoryView:
        """Project known plugins into cards.

        ``include_inactive`` is an authorization scope, not a display toggle.
        When ``False`` the catalog is restricted to **active** plugins — the
        only ones a non-privileged user can actually use. Disabled, failed and
        not-yet-activated plugins are operational state that only an admin (the
        sole role allowed to act on them via the lifecycle routes) may see, so
        their existence is never disclosed to ordinary users. Admins call with
        ``True`` and get the full catalog, including re-enableable plugins
        synthesized from on-disk manifests.
        """
        active = {self._name(p): p for p in self._safe(self._registry.get_all, [])}
        health = self._safe(self._registry.health_check, {}).get("plugins", {})
        static_paths = self._safe(self._registry.get_all_static_paths, {})
        config_enabled = self._safe(read_all, {})

        cards: list[PluginCardView] = []
        for row in self._safe(self._registry.list_plugins, []):
            name = row.get("name")
            if not name:
                continue
            plugin = active.get(name)
            disc = None if plugin else self._discovery(name)
            card = self._card(name, row, plugin, disc, health, static_paths)
            card.config_enabled = config_enabled.get(name)
            # A plugin turned off in config is not loaded at runtime, so it would
            # otherwise read as 'discovered'. Project it as 'disabled' so the
            # state survives a restart and matches the toggle — unless it is in
            # fact active (config just changed, runtime not yet synced).
            if card.config_enabled is False and card.state != PluginState.active:
                card.state = PluginState.disabled
            cards.append(card)

        if include_inactive:
            self._append_offline_cards(cards, config_enabled)
        else:
            # Non-privileged scope: disclose only active plugins. Skip the
            # offline-card synthesis entirely (it only ever yields 'disabled'
            # cards) and drop any non-active card the registry produced.
            cards = [c for c in cards if c.state == PluginState.active]

        cards.sort(key=lambda c: c.name)
        return InventoryView(total=len(cards), plugins=cards)

    def _append_offline_cards(
        self, cards: list[PluginCardView], config_enabled: dict[str, bool]
    ) -> None:
        """Add 'disabled' cards for installed plugins absent from the registry."""
        # Plugins turned off in config are skipped by the loader and so are
        # absent from the registry above. Surface them from their manifest as
        # 'disabled' cards so they stay visible and re-enableable after a restart.
        present = {c.name for c in cards}
        for name, enabled in config_enabled.items():
            if enabled or name in present:
                continue
            synthesized = self._disabled_card(name, enabled)
            if synthesized is not None:
                cards.append(synthesized)
                present.add(name)

        # A plugin can also be installed on disk yet never declared in config at
        # all — the loader filters discovery by config, so it is absent from both
        # the registry and ``config_enabled`` above. The control plane must still
        # surface every installed plugin so an operator can adopt it; project it
        # from its manifest as a 'disabled' card with no persisted config flag.
        for name in self._safe(list_installed_plugins, []):
            if name in present:
                continue
            synthesized = self._disabled_card(name, enabled=None)
            if synthesized is not None:
                cards.append(synthesized)
                present.add(name)

    def _disabled_card(self, name: str, enabled: bool | None) -> PluginCardView | None:
        """Build a 'disabled' card from the on-disk manifest (None if absent).

        ``enabled`` is the persisted config flag, or ``None`` for a plugin that
        is installed on disk but absent from ``configs/plugins.yaml`` entirely.
        """
        manifest = read_manifest(name)
        if not manifest:  # no plugin dir/manifest → not a real plugin, skip
            return None
        category = str(manifest.get("category") or "uncategorized")
        display = display_meta(name, category=category)
        return PluginCardView(
            name=name,
            version=str(manifest.get("version") or "0.0.0"),
            description=str(manifest.get("description") or ""),
            category=category,
            group=display["group"],
            tier=display["tier"],
            icon=display["icon"],
            instance=display["instance"],
            state=PluginState.disabled,
            healthy=None,
            initialized=False,
            config_enabled=enabled,
            provides_routes=False,
            router_prefix=None,
            surfaces=[],
            tags=list(manifest.get("tags") or []),
        )

    def ui_registry(
        self, allow: Any | None = None, *, include_inactive: bool = True
    ) -> list[EmbedSurface]:
        """Only the embeddable surfaces, for the shell's embed tabs.

        ``allow`` is an optional ``(plugin_name, tab_id) -> bool`` predicate used
        to filter surfaces the caller may not access (central tab policy). When
        ``None`` every embeddable surface is returned (no filtering).
        ``include_inactive`` mirrors :meth:`inventory`: non-admins never get
        embed surfaces for non-active plugins.
        """
        surfaces: list[EmbedSurface] = []
        for card in self.inventory(include_inactive=include_inactive).plugins:
            for s in card.surfaces:
                if not s.embeddable:
                    continue
                if allow is not None and not allow(card.name, s.tab_id):
                    continue
                surfaces.append(s)
        return surfaces

    def status(self, system_metrics: dict | None = None) -> StatusView:
        """Aggregated health + system metrics overview."""
        hc = self._safe(self._registry.health_check, {})
        return StatusView(
            healthy=bool(hc.get("healthy", False)),
            plugins=hc.get("plugins", {}),
            metrics=system_metrics or {},
        )

    def overview(self, *, include_inactive: bool = True) -> OverviewView:
        """Framework-wide head-band summary derived from the inventory.

        Scoped to the caller: a non-admin's counts only cover the active
        plugins they can see (``include_inactive=False``).
        """
        cards = self.inventory(include_inactive=include_inactive).plugins
        healthy = sum(1 for c in cards if c.healthy is True)
        degraded = sum(1 for c in cards if c.healthy is False)
        down = sum(1 for c in cards if c.state == PluginState.failed)
        embeddable = sum(1 for c in cards if any(s.embeddable for s in c.surfaces))
        with_routes = sum(1 for c in cards if c.provides_routes)
        total = len(cards)
        stats = [
            HeadStat(key="total", label="Plugins", value=total),
            HeadStat(
                key="healthy",
                label="Healthy",
                value=healthy,
                tone="success" if healthy == total else "neutral",
            ),
            HeadStat(
                key="degraded",
                label="Degraded",
                value=degraded,
                tone="warning" if degraded else "neutral",
            ),
            HeadStat(
                key="down",
                label="Down",
                value=down,
                tone="danger" if down else "neutral",
            ),
        ]
        return OverviewView(
            total=total,
            healthy=healthy,
            degraded=degraded,
            down=down,
            embeddable=embeddable,
            with_routes=with_routes,
            stats=stats,
        )

    # -- card assembly -------------------------------------------------------
    def _card(
        self,
        name: str,
        row: dict,
        plugin: Any | None,
        disc: Any | None,
        health: dict,
        static_paths: dict[str, Path],
    ) -> PluginCardView:
        meta = getattr(plugin, "metadata", None) or getattr(disc, "metadata", None)
        hstate = health.get(name, {})
        static_path = static_paths.get(name) or getattr(disc, "static_path", None)
        category = str(getattr(meta, "category", "uncategorized"))
        display = display_meta(name, category=category)
        return PluginCardView(
            name=name,
            version=str(row.get("version") or getattr(meta, "version", "0.0.0")),
            description=str(row.get("description") or getattr(meta, "description", "")),
            category=category,
            group=display["group"],
            tier=display["tier"],
            icon=display["icon"],
            instance=display["instance"],
            state=self._state(row, hstate),
            healthy=(hstate.get("status") == "healthy") if hstate else None,
            initialized=bool(row.get("initialized", False)),
            provides_routes=bool(getattr(disc, "provides_routes", plugin is not None)),
            router_prefix=self._router_prefix(plugin, disc),
            surfaces=self._surfaces(name, plugin, disc, static_path),
            tags=list(getattr(meta, "tags", []) or []),
        )

    def _surfaces(
        self,
        name: str,
        plugin: Any | None,
        disc: Any | None,
        static_path: Path | None,
    ) -> list[EmbedSurface]:
        tabs = self._ui_tabs(plugin, disc)
        embeddable = bool(static_path and (Path(static_path) / "index.html").exists())
        static_base = f"/plugins/{name}/static" if static_path else None

        surfaces = [
            EmbedSurface(
                tab_id=str(tab.get("id", name)),
                label=str(tab.get("label", name)),
                mount_url=tab.get("url") or (f"/{name}" if embeddable else None),
                static_base=static_base,
                embeddable=bool(tab.get("url")) or embeddable,
            )
            for tab in tabs
        ]
        if not surfaces and embeddable:  # SPA without declared ui_tabs
            surfaces.append(
                EmbedSurface(
                    tab_id=name,
                    label=name,
                    mount_url=f"/{name}",
                    static_base=static_base,
                    embeddable=True,
                )
            )
        return surfaces

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _state(row: dict, hstate: dict) -> PluginState:
        if hstate.get("status") == "unhealthy":
            return PluginState.failed
        if row.get("initialized"):
            return PluginState.active
        return PluginState.discovered

    @staticmethod
    def _ui_tabs(plugin: Any | None, disc: Any | None) -> list[dict]:
        if plugin is not None:
            try:
                return list(plugin.get_ui_tabs() or [])
            except Exception:  # noqa: BLE001 — never let one plugin break the grid
                return []
        return list(getattr(disc, "ui_tabs", []) or [])

    @staticmethod
    def _router_prefix(plugin: Any | None, disc: Any | None) -> str | None:
        if plugin is not None:
            try:
                return str(plugin.get_router_prefix())
            except Exception:  # noqa: BLE001
                return None
        return getattr(disc, "router_prefix", None)

    @staticmethod
    def _name(plugin: Any) -> str:
        return str(getattr(getattr(plugin, "metadata", None), "name", ""))

    def _discovery(self, name: str) -> Any | None:
        getter = getattr(self._registry, "get_discovered_plugin", None)
        if getter is None:
            return None
        try:
            return getter(name)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _safe(fn: Any, default: Any) -> Any:
        """Call a registry getter defensively; return ``default`` on failure."""
        try:
            return fn() if callable(fn) else default
        except Exception:  # noqa: BLE001
            return default


__all__ = ["ControlAggregator"]
