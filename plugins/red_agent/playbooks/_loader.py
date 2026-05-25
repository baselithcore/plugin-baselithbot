"""Filesystem-backed playbook loader.

Reads ``*.yaml`` / ``*.yml`` files from the ``library/`` directory and
exposes them through a ``PlaybookCatalogue`` keyed by playbook ID.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from core.observability.logging import get_logger
from plugins.red_agent.models import ScanIntensity, TargetKind

logger = get_logger(__name__)


_DEFAULT_LIBRARY = Path(__file__).parent / "library"


class Playbook(BaseModel):
    """Static description of a coordinated scan recipe."""

    id: str
    name: str
    description: str = ""
    version: str = "0.1.0"
    target_kinds: list[TargetKind] = Field(default_factory=list)
    intensity: ScanIntensity = ScanIntensity.PASSIVE
    scanners: list[str] = Field(default_factory=list)
    owasp_refs: list[str] = Field(default_factory=list)
    mitre_refs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    requires_autonomy_at_least: str | None = None
    notes: str | None = None

    @field_validator("scanners")
    @classmethod
    def _scanners_unique(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("scanners must be unique")
        return v


class PlaybookNotFoundError(KeyError):
    """Raised when a requested playbook ID is not in the catalogue."""


class PlaybookCatalogue:
    """Read-only registry of playbooks indexed by ``id``."""

    def __init__(self, playbooks: list[Playbook]) -> None:
        self._by_id: dict[str, Playbook] = {p.id: p for p in playbooks}
        if len(self._by_id) != len(playbooks):
            duplicates = [p.id for p in playbooks if p.id in self._by_id]
            raise ValueError(f"duplicate playbook ids: {duplicates}")

    def all(self) -> list[Playbook]:
        return sorted(self._by_id.values(), key=lambda p: p.id)

    def get(self, playbook_id: str) -> Playbook:
        if playbook_id not in self._by_id:
            raise PlaybookNotFoundError(playbook_id)
        return self._by_id[playbook_id]

    def filter_for(
        self,
        *,
        target_kind: TargetKind | None = None,
        max_intensity: ScanIntensity | None = None,
    ) -> list[Playbook]:
        rows = self.all()
        if target_kind is not None:
            rows = [
                p for p in rows if not p.target_kinds or target_kind in p.target_kinds
            ]
        if max_intensity is not None:
            order = list(ScanIntensity)
            ceiling = order.index(max_intensity)
            rows = [p for p in rows if order.index(p.intensity) <= ceiling]
        return rows


def load_playbook_files(directory: Path | None = None) -> list[Playbook]:
    """Parse every ``*.yaml`` under ``directory`` (defaults to library/).

    Files that fail to parse are logged and skipped — a malformed YAML
    must not knock the whole library out.
    """
    target = directory or _DEFAULT_LIBRARY
    if not target.exists():
        return []
    playbooks: list[Playbook] = []
    for path in sorted(target.glob("*.y*ml")):
        try:
            data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.playbooks.parse_failed",
                extra={"path": str(path), "err": str(e)},
            )
            continue
        if not isinstance(data, dict):
            logger.warning(
                "red_agent.playbooks.invalid_root",
                extra={"path": str(path)},
            )
            continue
        try:
            playbooks.append(Playbook.model_validate(data))
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.playbooks.validation_failed",
                extra={"path": str(path), "err": str(e)},
            )
    return playbooks


def default_catalogue() -> PlaybookCatalogue:
    return PlaybookCatalogue(load_playbook_files())
