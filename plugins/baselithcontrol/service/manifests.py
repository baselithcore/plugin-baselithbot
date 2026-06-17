"""Read a plugin's manifest directly, by name, without importing the plugin.

The loader skips plugins turned off in config (``enabled: false``) entirely, so
a disabled plugin is **absent from the live registry**. The control plane still
needs to list it — as ``disabled`` — so an operator can re-enable it. Reading the
on-disk manifest is the only source of truth for a plugin that was never loaded.

Manifest ``name`` is required to equal its directory name, so a plugin resolves
by name alone (mirrors ``service/widgets.py``).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from core.observability.logging import get_logger

logger = get_logger(__name__)

# plugins/baselithcontrol/service/manifests.py → parents[2] == plugins/.
_PLUGINS_ROOT = Path(__file__).resolve().parents[2]


def list_installed_plugins() -> list[str]:
    """Return the names of every plugin dir on disk that carries a manifest.

    Independent of ``configs/plugins.yaml`` — a plugin present on disk but never
    declared in config is invisible to the live registry, yet the control plane
    must still surface it so an operator can enable it. Mirrors the loader's dir
    filter (skip ``.``/``_`` prefixes; require a ``plugin.py`` or ``__init__.py``).
    """
    if not _PLUGINS_ROOT.is_dir():
        return []
    names: list[str] = []
    for entry in _PLUGINS_ROOT.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            continue
        if entry.name.startswith((".", "_")):
            continue
        if not ((entry / "plugin.py").exists() or (entry / "__init__.py").exists()):
            continue
        if read_manifest(entry.name):  # only real, manifest-bearing plugins
            names.append(entry.name)
    return names


@lru_cache(maxsize=256)
def read_manifest(plugin_name: str) -> dict[str, Any]:
    """Return a plugin's parsed manifest (empty dict if absent/unreadable)."""
    for ext in ("yaml", "yml", "json"):
        path = _PLUGINS_ROOT / plugin_name / f"manifest.{ext}"
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text) if ext == "json" else yaml.safe_load(text)
        except Exception as exc:  # noqa: BLE001 — a bad manifest must not break the grid
            logger.debug("manifest read failed for %s: %s", plugin_name, exc)
            return {}
        return data if isinstance(data, dict) else {}
    return {}


__all__ = ["read_manifest", "list_installed_plugins"]
