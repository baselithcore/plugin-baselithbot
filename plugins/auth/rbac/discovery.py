"""Discover UI tabs exposed by every plugin on disk.

Coverage combines two sources so the access matrix lists *all* plugins, not
just the ones currently active:

1. **Static scan** of every plugin directory via ``ResourceAnalyzer`` — catches
   plugins that are disabled or only lazily discovered (tabs read from the
   ``get_ui_tabs`` literal by AST).
2. **Runtime scan** of active plugins via the live registry — catches tabs that
   are computed dynamically and so are invisible to the static pass.

Results are merged and de-duplicated by ``(plugin, tab_id)``.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from core.observability.logging import get_logger

logger = get_logger(__name__)

# plugins/auth/rbac/discovery.py -> parents[2] == the plugins/ root.
_PLUGINS_DIR = Path(__file__).resolve().parents[2]
_MANIFEST_NAMES = ("manifest.yaml", "manifest.yml", "manifest.json")
_SOURCE_NAMES = ("plugin.py", "__init__.py")


def _manifest_name(plugin_dir: Path) -> Optional[str]:
    """Logical plugin name from the manifest (falls back to directory name)."""
    for fname in _MANIFEST_NAMES:
        path = plugin_dir / fname
        if not path.exists():
            continue
        try:
            if path.suffix == ".json":
                import json

                data = json.loads(path.read_text(encoding="utf-8"))
            else:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
            name = (data or {}).get("name")
            if isinstance(name, str) and name:
                return name
        except Exception:  # noqa: BLE001
            return plugin_dir.name
    return None


def _tabs_from_source(source: str, plugin: str) -> List[Dict[str, str]]:
    """Leniently extract ``get_ui_tabs`` list-of-dict literals via AST.

    Unlike a strict evaluator, this keeps a tab as long as ``id`` is a string
    literal — non-literal values (e.g. ``"url": MOUNT_PATH``) are simply
    ignored, so dynamic URLs no longer drop the whole entry.
    """
    out: List[Dict[str, str]] = []
    try:
        tree = ast.parse(source)
    except Exception:  # noqa: BLE001
        return out
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "get_ui_tabs"):
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Dict):
                continue
            entry: Dict[str, str] = {}
            for key, val in zip(sub.keys, sub.values):
                if not isinstance(key, ast.Constant):
                    continue
                k = str(key.value)
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    entry[k] = val.value
                elif (
                    k == "id" and isinstance(val, ast.Attribute) and val.attr == "name"
                ):
                    # Common pattern: "id": self.metadata.name -> the plugin name.
                    entry[k] = plugin
            tab_id = entry.get("id")
            if tab_id:
                out.append(
                    {
                        "plugin": plugin,
                        "tab_id": tab_id,
                        "label": entry.get("label", tab_id),
                    }
                )
    return out


def _static_tabs() -> List[Dict[str, str]]:
    """Tabs from a lenient AST scan of every plugin directory on disk."""
    tabs: List[Dict[str, str]] = []
    if not _PLUGINS_DIR.exists():
        return tabs
    for plugin_dir in _PLUGINS_DIR.iterdir():
        if not plugin_dir.is_dir() or plugin_dir.name.startswith((".", "_")):
            continue
        name = _manifest_name(plugin_dir)
        if not name:
            continue
        for src_name in _SOURCE_NAMES:
            src = plugin_dir / src_name
            if not src.exists():
                continue
            try:
                tabs.extend(_tabs_from_source(src.read_text(encoding="utf-8"), name))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Tab scan failed for %s/%s: %s", name, src_name, exc)
    return tabs


def _runtime_tabs(registry: Optional[Any]) -> List[Dict[str, str]]:
    """Tabs from active plugins in the live registry (covers dynamic tabs)."""
    reg = registry
    if reg is None:
        try:
            from core.plugins.api import get_controller

            reg = get_controller().registry
        except Exception:  # noqa: BLE001 - controller may be uninitialised
            return []
    tabs: List[Dict[str, str]] = []
    try:
        plugins = reg.get_all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Runtime plugin enumeration failed: %s", exc)
        return []
    for plugin in plugins:
        name = getattr(getattr(plugin, "metadata", None), "name", None)
        if not name or not hasattr(plugin, "get_ui_tabs"):
            continue
        try:
            for tab in plugin.get_ui_tabs() or []:
                tab_id = tab.get("id")
                if tab_id:
                    tabs.append(
                        {
                            "plugin": name,
                            "tab_id": tab_id,
                            "label": tab.get("label", tab_id),
                        }
                    )
        except Exception as exc:  # noqa: BLE001 - never block on one plugin
            logger.warning("Failed to read tabs for plugin %s: %s", name, exc)
    return tabs


def discover_plugin_tabs(registry: Optional[Any] = None) -> List[Dict[str, str]]:
    """Return de-duplicated ``[{plugin, tab_id, label}, ...]`` for all plugins."""
    merged: Dict[Tuple[str, str], Dict[str, str]] = {}
    # Static first (complete), then runtime overrides labels where present.
    for tab in _static_tabs() + _runtime_tabs(registry):
        merged[(tab["plugin"], tab["tab_id"])] = tab
    return list(merged.values())


__all__ = ["discover_plugin_tabs"]
