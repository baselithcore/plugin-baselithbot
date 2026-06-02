"""Per-vault Obsidian initialisation.

Two-key gate for the ``obsidian://`` open links surfaced by the chat
sidebar:

1. **Per-tenant**: an admin must explicitly call
   ``POST /api/admin/tenants/{name}/obsidian/init`` (this module). The
   call seeds ``<vault_root>/.obsidian/`` with read-only-friendly
   defaults and writes a marker file ``.obsidian-init.json`` recording
   *who* enabled the integration and *when*.

2. **Per-user**: the caller must hold the ``obsidian.open`` permission
   (granted by mig 012 to all system roles).

Both keys must be true for ``GET /api/wiki/page/{id}`` to include the
``obsidian_uri`` field. Either side can be revoked independently:
``POST .../obsidian/disable`` flips the marker without touching the
``.obsidian/`` config (so user-customised settings survive a reactivate).

Read-only convention
====================

Obsidian itself has no first-class "read-only" toggle, but the seeded
config nudges visitors toward consumption rather than authoring:

- ``defaultViewMode: preview`` — opens pages rendered, not in source.
- ``readableLineLength: true`` + ``showLineNumber: false`` — reading UX.
- ``promptDelete: true`` — stops accidental deletes.
- ``communityPlugins: []`` — restricted mode by default; users can opt
  in but the seed is conservative.
- A ``CLAUDE.md`` addendum at the vault root states the convention so
  agents and humans alike know the wiki is owned by the LLM pipeline.

True OS-level read-only enforcement (chmod / network share ACL) is
out of scope here — host-dependent and would block the ingest pipeline
that legitimately writes to the vault.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MARKER_FILE = ".obsidian-init.json"
OBSIDIAN_DIR = ".obsidian"

_APP_JSON = {
    "defaultViewMode": "preview",
    "livePreview": False,
    "readableLineLength": True,
    "showLineNumber": False,
    "promptDelete": True,
    "useTab": True,
    "tabSize": 2,
    "spellcheck": False,
}

_COMMUNITY_PLUGINS_JSON: list[str] = []

_CORE_PLUGINS_JSON = [
    "file-explorer",
    "global-search",
    "outline",
    "graph",
    "backlink",
    "page-preview",
    "tag-pane",
]

_README_BODY = """# Obsidian read-only convention

Questo vault è gestito dal motore `llm-wiki`. Le pagine sotto `wiki/`
sono scritte e mantenute dalla pipeline di ingest LLM:

- `raw/`  — fonti documentali (PDF + asset). **Solo lettura**.
- `wiki/` — pagine generate dall'agente. Modificabili solo dal motore.

Apri Obsidian per leggere e navigare il grafo della conoscenza
(graph view, backlink, outline). Evita modifiche manuali ai file:
verranno sovrascritte al prossimo ingest. Per richiedere correzioni
usa il flusso di feedback dell'app o un commit nel repo del Domain Pack.
"""


class ObsidianState:
    """In-memory representation of ``.obsidian-init.json``."""

    __slots__ = ("enabled", "initialized_at", "initialized_by")

    def __init__(
        self,
        enabled: bool = False,
        initialized_at: str | None = None,
        initialized_by: str | None = None,
    ) -> None:
        self.enabled = enabled
        self.initialized_at = initialized_at
        self.initialized_by = initialized_by

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "initialized_at": self.initialized_at,
            "initialized_by": self.initialized_by,
        }


def read_state(vault_root: Path) -> ObsidianState:
    """Load the per-vault Obsidian flag. Missing/corrupt = disabled."""
    marker = vault_root / MARKER_FILE
    if not marker.is_file():
        return ObsidianState(enabled=False)
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("[obsidian] marker unreadable at %s: %s", marker, exc)
        return ObsidianState(enabled=False)
    if not isinstance(data, dict):
        return ObsidianState(enabled=False)
    return ObsidianState(
        enabled=bool(data.get("enabled", False)),
        initialized_at=data.get("initialized_at"),
        initialized_by=data.get("initialized_by"),
    )


def _write_marker(vault_root: Path, state: ObsidianState) -> None:
    marker = vault_root / MARKER_FILE
    marker.write_text(
        json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _seed_obsidian_dir(vault_root: Path) -> None:
    """Create `.obsidian/` skeleton if missing.

    Idempotent on every key file: if a user has already opened the
    vault and Obsidian wrote its own `app.json`, we leave it alone —
    the user's preferences win over the seed defaults.
    """
    obs = vault_root / OBSIDIAN_DIR
    obs.mkdir(parents=True, exist_ok=True)
    seeds = (
        ("app.json", _APP_JSON),
        ("community-plugins.json", _COMMUNITY_PLUGINS_JSON),
        ("core-plugins.json", _CORE_PLUGINS_JSON),
    )
    for name, payload in seeds:
        target = obs / name
        if target.exists():
            continue
        target.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    readme = vault_root / "OBSIDIAN.md"
    if not readme.exists():
        readme.write_text(_README_BODY, encoding="utf-8")


def initialize(vault_root: Path, *, by_user: str | None) -> ObsidianState:
    """Idempotent: enable + seed `.obsidian/`. Safe to call repeatedly."""
    if not vault_root.is_dir():
        raise FileNotFoundError(f"vault root missing: {vault_root}")
    _seed_obsidian_dir(vault_root)
    state = ObsidianState(
        enabled=True,
        initialized_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        initialized_by=by_user,
    )
    _write_marker(vault_root, state)
    logger.info(
        "[obsidian] initialized vault=%s by=%s",
        vault_root,
        by_user or "(anon)",
    )
    return state


def disable(vault_root: Path) -> ObsidianState:
    """Flip the flag off. Leaves `.obsidian/` intact so re-enabling
    preserves user customisations."""
    if not vault_root.is_dir():
        raise FileNotFoundError(f"vault root missing: {vault_root}")
    current = read_state(vault_root)
    state = ObsidianState(
        enabled=False,
        initialized_at=current.initialized_at,
        initialized_by=current.initialized_by,
    )
    _write_marker(vault_root, state)
    logger.info("[obsidian] disabled vault=%s", vault_root)
    return state


__all__ = ["ObsidianState", "read_state", "initialize", "disable"]
