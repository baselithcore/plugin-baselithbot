"""Daily notes — one dated journal entry per day, created on demand.

A daily note has a *stable* id (``daily-YYYY-MM-DD``) so "open today" is
idempotent: it returns the existing entry or creates it once. Lives in the
default workspace (a journal is vault-global). Optionally seeded from a template.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import Note, NoteCreate
from .notes import NoteService
from .templates import TemplateStore, expand_placeholders

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def resolve_date(date: str | None) -> str:
    """Validate a ``YYYY-MM-DD`` string, defaulting to today (UTC)."""
    if not date:
        return _today()
    if not _DATE_RE.match(date):
        raise ValueError(f"invalid date: {date!r}")
    return date


def daily_id(date: str) -> str:
    return f"daily-{date}"


def ensure_daily(
    notes: NoteService,
    templates: TemplateStore,
    date: str | None = None,
    template_id: str | None = None,
) -> tuple[Note, bool]:
    """Return ``(note, created)`` for the daily entry of ``date`` (today if null)."""
    day = resolve_date(date)
    note_id = daily_id(day)
    if notes.exists(note_id):
        return notes.get(note_id), False

    body = f"# {day}\n\n"
    if template_id:
        tpl = templates.get(template_id)
        if tpl:
            body = expand_placeholders(tpl.body, title=day, date=day)
    note = notes.create(NoteCreate(title=day, body=body), note_id=note_id)
    return note, True
