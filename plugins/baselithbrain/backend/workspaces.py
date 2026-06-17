"""WorkspaceService — the registry of logical note groupings.

A *workspace* is a named namespace over the flat vault: every note carries a
``workspace`` scalar in its frontmatter and belongs to exactly one. This service
owns only the registry *metadata* (name, color, icon, …), persisted as a single
``.brain/workspaces.json`` file beside the notes. The hidden ``.brain`` dir is
never globbed as a note, so the vault stays a clean, portable pile of Markdown.

The note↔workspace membership itself lives in each note's frontmatter (owned by
:mod:`notes`), keeping this layer free of any per-note bookkeeping.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Workspace, WorkspaceCreate, WorkspaceUpdate
from .vault import slugify

#: Every note with no explicit ``workspace`` belongs here. Always present.
DEFAULT_WORKSPACE_ID = "default"
_DEFAULT_NAME = "My Brain"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class WorkspaceService:
    """CRUD over the JSON workspace registry (one file, no DB)."""

    def __init__(self, vault_root: Path) -> None:
        self._dir = vault_root / ".brain"
        self._path = self._dir / "workspaces.json"

    # ---- persistence -----------------------------------------------------
    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    def _save(self, items: list[dict]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ---- reads -----------------------------------------------------------
    def list(self) -> list[Workspace]:
        self.ensure_default()
        items = [Workspace(**raw) for raw in self._load()]
        items.sort(
            key=lambda w: (w.order if w.order is not None else 1_000, w.name.lower())
        )
        return items

    def get(self, ws_id: str) -> Workspace | None:
        return next((w for w in self.list() if w.id == ws_id), None)

    def exists(self, ws_id: str) -> bool:
        return any(w.id == ws_id for w in self.list())

    def ensure_default(self) -> None:
        """Guarantee the default workspace exists (idempotent, first-run safe)."""
        items = self._load()
        if any(raw.get("id") == DEFAULT_WORKSPACE_ID for raw in items):
            return
        ts = _now()
        items.insert(
            0,
            Workspace(
                id=DEFAULT_WORKSPACE_ID,
                name=_DEFAULT_NAME,
                icon="brain",
                order=0,
                created=ts,
                updated=ts,
            ).model_dump(),
        )
        self._save(items)

    # ---- writes ----------------------------------------------------------
    def _unique_id(self, base: str, taken: set[str]) -> str:
        slug = slugify(base)
        candidate, n = slug, 2
        while candidate in taken:
            candidate = f"{slug}-{n}"
            n += 1
        return candidate

    def create(self, payload: WorkspaceCreate) -> Workspace:
        items = self._load()
        ws_id = self._unique_id(payload.name, {raw.get("id", "") for raw in items})
        ts = _now()
        ws = Workspace(
            id=ws_id,
            name=payload.name or ws_id,
            color=payload.color,
            icon=payload.icon,
            description=payload.description,
            order=len(items),
            created=ts,
            updated=ts,
        )
        items.append(ws.model_dump())
        self._save(items)
        return ws

    def update(self, ws_id: str, patch: WorkspaceUpdate) -> Workspace | None:
        items = self._load()
        for raw in items:
            if raw.get("id") != ws_id:
                continue
            data = patch.model_dump(exclude_none=True)
            raw.update(data)
            raw["updated"] = _now()
            self._save(items)
            return Workspace(**raw)
        return None

    def delete(self, ws_id: str) -> bool:
        """Remove a workspace. The default workspace can never be deleted.

        Membership cleanup (re-homing the workspace's notes) is the caller's job
        — this layer only owns the registry.
        """
        if ws_id == DEFAULT_WORKSPACE_ID:
            return False
        items = self._load()
        kept = [raw for raw in items if raw.get("id") != ws_id]
        if len(kept) == len(items):
            return False
        self._save(kept)
        return True
