"""Persist a plugin's ``enabled`` flag in ``configs/plugins.yaml``.

Reads use a normal YAML parse; writes are a **surgical, comment-preserving line
edit** — only the target plugin's ``enabled:`` line is rewritten, so the
extensive operator comments in ``plugins.yaml`` survive (a full
``yaml.safe_load`` + ``yaml.dump`` round-trip would strip every comment, and
``ruamel.yaml`` is not a dependency here).

The file path honors ``PLUGIN_CONFIG_PATH`` (the same env the framework reads in
``core/api/lifespan.py``), defaulting to ``configs/plugins.yaml``.
"""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path

import yaml

from core.observability.logging import get_logger

logger = get_logger(__name__)

_WRITE_LOCK = threading.Lock()
_ENABLED_RE = re.compile(r"^(?P<indent>\s+)enabled:\s*(?P<val>\S+)(?P<rest>.*)$")


def config_path() -> Path:
    return Path(os.environ.get("PLUGIN_CONFIG_PATH", "configs/plugins.yaml"))


def read_all() -> dict[str, bool]:
    """Return ``{plugin: enabled}`` for every plugin declared in the config."""
    path = config_path()
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 — a bad config must not break reads
        logger.warning("plugins.yaml parse failed: %s", exc)
        return {}
    out: dict[str, bool] = {}
    for name, block in data.items():
        if isinstance(block, dict) and "enabled" in block:
            out[str(name)] = bool(block["enabled"])
        elif isinstance(block, dict):
            out[str(name)] = True  # absent flag defaults to enabled
    return out


def read_enabled(plugin: str) -> bool | None:
    """Return the persisted ``enabled`` value, or ``None`` if not in the config."""
    return read_all().get(plugin)


def read_block(plugin: str) -> dict[str, object]:
    """Return the full config block for ``plugin`` (``{}`` if absent/unparsable).

    Used to hand a plugin its persisted settings when activating it from disk,
    so config-driven plugins initialize the same way the loader would at boot.
    """
    path = config_path()
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 — a bad config must not break reads
        logger.warning("plugins.yaml parse failed: %s", exc)
        return {}
    block = data.get(plugin)
    return dict(block) if isinstance(block, dict) else {}


def _is_top_level_key(line: str, plugin: str) -> bool:
    return bool(re.match(rf"^{re.escape(plugin)}:\s*(#.*)?$", line.rstrip("\n")))


def set_enabled(plugin: str, enabled: bool) -> bool:
    """Flip ``enabled`` for ``plugin`` in place, preserving comments/formatting.

    Returns True on success. If the plugin block is missing it is appended; if
    the block exists without an ``enabled:`` line one is inserted.
    """
    path = config_path()
    val = "true" if enabled else "false"
    with _WRITE_LOCK:
        try:
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError as exc:
            logger.error("cannot read %s: %s", path, exc)
            return False

        key_idx = next(
            (i for i, ln in enumerate(lines) if _is_top_level_key(ln, plugin)), None
        )
        if key_idx is None:  # append a fresh block
            tail = "" if not lines or lines[-1].endswith("\n") else "\n"
            lines.append(f"{tail}{plugin}:\n  enabled: {val}\n")
            return _atomic_write(path, lines)

        # Scan the block (subsequent indented/blank lines) for an enabled: line.
        for i in range(key_idx + 1, len(lines)):
            stripped = lines[i].rstrip("\n")
            if stripped and not stripped[0].isspace():
                break  # next top-level key → block ended
            m = _ENABLED_RE.match(stripped)
            if m:
                lines[i] = f"{m['indent']}enabled: {val}{m['rest']}\n"
                return _atomic_write(path, lines)
        # No enabled: line in the block → insert one right after the key.
        lines.insert(key_idx + 1, f"  enabled: {val}\n")
        return _atomic_write(path, lines)


def _atomic_write(path: Path, lines: list[str]) -> bool:
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text("".join(lines), encoding="utf-8")
        tmp.replace(path)
        return True
    except OSError as exc:
        logger.error("cannot write %s: %s", path, exc)
        return False


__all__ = ["read_all", "read_enabled", "set_enabled", "config_path"]
