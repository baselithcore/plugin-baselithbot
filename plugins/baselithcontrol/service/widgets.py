"""Declarative display metadata + zero-code status widgets from plugin manifests.

A plugin opts into richer control-plane presentation by adding an optional
``control`` block to its ``manifest.yaml`` — no frontend code, no coupling::

    control:
      group: Operations
      icon: gauge
      instance: prod
      widget:
        title: Twin queue
        endpoint: /api/baselithtwin/stats   # relative, same-origin
        display: list
        fields:
          - { path: queue.depth, label: Queue, format: number,
              highlight: { gte: 50, tone: warning } }
          - { path: replies.today, label: Replies, format: number }

The dashboard resolves the spec here (server-side); the browser fetches the
same-origin ``endpoint`` directly (already cookie-authed) and renders it with a
single generic renderer. Because plugins live in the same process, there is no
external fetch and therefore no SSRF surface: only relative paths are accepted.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from core.observability.logging import get_logger

from ..api_models import WidgetFieldSpec, WidgetSpec

logger = get_logger(__name__)

# plugins/baselithcontrol/service/widgets.py → parents[2] == plugins/.
# Manifest ``name`` is required to equal its directory name, so we resolve a
# plugin's manifest by name without importing it.
_PLUGINS_ROOT = Path(__file__).resolve().parents[2]


def _manifest_dir(plugin_name: str) -> Path | None:
    """Resolve a plugin's on-disk directory from its (possibly registry) name.

    Most plugins use the same string for their manifest ``name`` and their
    directory, but a few legacy plugins declare a hyphenated ``name``
    (``coding-agent``) while living in an underscored directory
    (``coding_agent``). The registry serves the manifest ``name``, so resolve
    by trying the literal name first, then the hyphen/underscore variants.
    Returns the first directory that actually holds a ``manifest.yaml``.
    """
    candidates = (
        plugin_name,
        plugin_name.replace("-", "_"),
        plugin_name.replace("_", "-"),
    )
    seen: set[str] = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        if (_PLUGINS_ROOT / cand / "manifest.yaml").is_file():
            return _PLUGINS_ROOT / cand
    return None


@lru_cache(maxsize=256)
def load_control_meta(plugin_name: str) -> dict[str, Any]:
    """Return the ``control`` block of a plugin's manifest (empty if absent)."""
    plugin_dir = _manifest_dir(plugin_name)
    if plugin_dir is None:
        return {}
    manifest = plugin_dir / "manifest.yaml"
    try:
        import yaml

        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 — a bad manifest must not break the grid
        logger.debug("control meta load failed for %s: %s", plugin_name, exc)
        return {}
    control = data.get("control")
    return control if isinstance(control, dict) else {}


def display_meta(plugin_name: str, *, category: str) -> dict[str, Any]:
    """Derive display metadata (group/icon/instance/tier) with sensible fallbacks.

    ``tier`` separates framework/infrastructure plugins (``system``) from custom
    feature plugins (``application``, the default). A plugin opts into the system
    bucket by declaring ``control.tier: system`` in its manifest; any other value
    falls back to ``application`` so the control plane never hides a feature
    plugin by accident.
    """
    control = load_control_meta(plugin_name)
    group = control.get("group")
    tier = (
        "system"
        if str(control.get("tier", "")).strip().lower() == "system"
        else "application"
    )
    return {
        "group": str(group) if group else (category or "uncategorized"),
        "icon": str(control.get("icon", "")),
        "instance": (str(control["instance"]) if control.get("instance") else None),
        "tier": tier,
    }


def _coerce_fields(raw: Any) -> list[WidgetFieldSpec]:
    """Validate the declared field mappings, dropping malformed entries."""
    fields: list[WidgetFieldSpec] = []
    for entry in raw or []:
        if not isinstance(entry, dict) or "path" not in entry:
            continue
        highlight = entry.get("highlight")
        fields.append(
            WidgetFieldSpec(
                path=str(entry["path"]),
                label=(str(entry["label"]) if entry.get("label") else None),
                format=str(entry.get("format", "number")),
                highlight=highlight if isinstance(highlight, dict) else None,
            )
        )
    return fields


def resolve_widget(plugin_name: str) -> WidgetSpec | None:
    """Build a :class:`WidgetSpec` from a plugin's ``control.widget`` block.

    Only relative, same-origin endpoints are honored — an absolute or
    scheme-bearing ``endpoint`` is rejected (the control plane never fetches
    arbitrary external URLs server-side).
    """
    widget = load_control_meta(plugin_name).get("widget")
    if not isinstance(widget, dict):
        return None
    endpoint = str(widget.get("endpoint", "")).strip()
    if not endpoint.startswith("/") or endpoint.startswith("//"):
        logger.debug("widget for %s rejected: endpoint must be relative", plugin_name)
        return None
    return WidgetSpec(
        plugin=plugin_name,
        title=str(widget.get("title", plugin_name)),
        endpoint=endpoint,
        display=str(widget.get("display", "list")),
        fields=_coerce_fields(widget.get("fields")),
    )


def resolve_widgets(plugin_names: list[str]) -> list[WidgetSpec]:
    """Resolve declarative widgets for the given plugins (those that declare one)."""
    out: list[WidgetSpec] = []
    for name in plugin_names:
        spec = resolve_widget(name)
        if spec is not None:
            out.append(spec)
    return out


__all__ = ["load_control_meta", "display_meta", "resolve_widget", "resolve_widgets"]
