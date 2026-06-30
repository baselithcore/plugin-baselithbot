"""Note templates — reusable skeletons inserted into new notes.

Stored as Markdown files under ``.brain/templates`` (frontmatter ``name`` +
body). Bodies may carry ``{{date}}``, ``{{time}}``, ``{{datetime}}`` and
``{{title}}`` placeholders, expanded at apply time. Open-format like notes, so
templates are portable and human-editable.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from . import frontmatter
from .models import Template, TemplateCreate, TemplateMeta
from .vault import slugify

_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def expand_placeholders(body: str, title: str = "", date: str | None = None) -> str:
    """Substitute ``{{date}}`` / ``{{time}}`` / ``{{datetime}}`` / ``{{title}}``.

    ``date`` overrides the ``{{date}}`` value (used by daily notes so the
    placeholder is the entry's day, not today); it defaults to today (UTC).
    """
    now = datetime.now(timezone.utc)
    day = date or now.strftime("%Y-%m-%d")
    return (
        body.replace("{{date}}", day)
        .replace("{{time}}", now.strftime("%H:%M"))
        .replace("{{datetime}}", f"{day} {now.strftime('%H:%M')}")
        .replace("{{title}}", title)
    )


class TemplateStore:
    """CRUD over note templates under the vault's ``.brain/templates``."""

    def __init__(self, vault_root: Path) -> None:
        self._dir = vault_root.resolve() / ".brain" / "templates"

    def _path(self, template_id: str) -> Path:
        if not _ID_RE.match(template_id):
            raise ValueError(f"invalid template id: {template_id!r}")
        return self._dir / f"{template_id}.md"

    def _unique_id(self, name: str) -> str:
        base = slugify(name)
        candidate, n = base, 2
        while self._path(candidate).exists():
            candidate, n = f"{base}-{n}", n + 1
        return candidate

    def list(self) -> list[TemplateMeta]:
        if not self._dir.exists():
            return []
        out: list[TemplateMeta] = []
        for p in sorted(self._dir.glob("*.md")):
            meta, _ = frontmatter.parse(p.read_text(encoding="utf-8"))
            out.append(
                TemplateMeta(
                    id=p.stem,
                    name=str(meta.get("name") or p.stem),
                    updated=meta.get("updated"),
                )
            )
        out.sort(key=lambda t: t.name.lower())
        return out

    def get(self, template_id: str) -> Template | None:
        path = self._path(template_id)
        if not path.exists():
            return None
        meta, body = frontmatter.parse(path.read_text(encoding="utf-8"))
        return Template(
            id=template_id,
            name=str(meta.get("name") or template_id),
            updated=meta.get("updated"),
            body=body,
        )

    def create(self, payload: TemplateCreate) -> Template:
        template_id = self._unique_id(payload.name or "template")
        self._dir.mkdir(parents=True, exist_ok=True)
        meta = {"name": payload.name or template_id, "updated": _now()}
        self._path(template_id).write_text(
            frontmatter.serialize(meta, payload.body), encoding="utf-8"
        )
        return Template(id=template_id, name=meta["name"], updated=meta["updated"], body=payload.body)

    def delete(self, template_id: str) -> bool:
        path = self._path(template_id)
        if path.exists():
            path.unlink()
            return True
        return False
