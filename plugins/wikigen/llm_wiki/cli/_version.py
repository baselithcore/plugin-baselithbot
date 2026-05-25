"""Resolve the engine version for ``--version`` output.

Reads the installed distribution metadata first; falls back to the
``[project].version`` key in ``pyproject.toml`` when running from a
non-installed checkout (e.g. fresh clone before ``pip install -e .``).
"""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

_DIST_NAME = "wiki-white-label"


def resolve_version() -> str:
    try:
        return metadata.version(_DIST_NAME)
    except metadata.PackageNotFoundError:
        pass
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if pyproject.is_file():
        try:
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("version") and "=" in stripped:
                    raw = stripped.split("=", 1)[1].strip()
                    return raw.strip('"').strip("'")
        except OSError:
            pass
    return "0.0.0+unknown"
