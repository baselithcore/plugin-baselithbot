"""Seed an empty vault with a small interlinked starter set.

Gives a first-run user a real graph to explore (Zettelkasten atomic notes + a
LYT Map-of-Content) instead of a blank screen. Only runs when the vault has no
notes — it never overwrites user content.
"""

from __future__ import annotations

from .models import NoteCreate
from .notes import NoteService

_SEED: list[NoteCreate] = [
    NoteCreate(
        title="Welcome to BaselithBrain",
        tags=["meta", "start-here"],
        body=(
            "This is your **second brain** — local-first, Markdown, yours.\n\n"
            "Try these:\n\n"
            "- Link notes with `[[wikilinks]]`, e.g. [[Zettelkasten]].\n"
            "- Press `Cmd/Ctrl+K` for the command palette.\n"
            "- Open the graph to navigate by connection, not by folder.\n\n"
            "See the [[PKM Map of Content]] to get oriented."
        ),
    ),
    NoteCreate(
        title="PKM Map of Content",
        tags=["moc", "pkm"],
        body=(
            "A **Map of Content** (MOC) is a hub note that links a cluster.\n\n"
            "Core ideas in this vault:\n\n"
            "- [[Zettelkasten]] — atomic, linked notes.\n"
            "- [[Linking Your Thinking]] — emergent structure via MOCs.\n"
            "- [[Atomic Notes]] — one idea per note.\n"
            "- [[Bidirectional Links]] — why backlinks matter."
        ),
    ),
    NoteCreate(
        title="Zettelkasten",
        tags=["pkm", "method"],
        body=(
            "A note-taking method built on small, atomic notes connected by "
            "links. Knowledge emerges from the web of connections, not a "
            "hierarchy. Pairs naturally with [[Atomic Notes]] and "
            "[[Bidirectional Links]]."
        ),
    ),
    NoteCreate(
        title="Linking Your Thinking",
        tags=["pkm", "method"],
        body=(
            "LYT favors *emergent* structure: let [[Bidirectional Links]] and "
            "[[PKM Map of Content]] notes reveal organization over time rather "
            "than forcing folders up front."
        ),
    ),
    NoteCreate(
        title="Atomic Notes",
        tags=["pkm", "principle"],
        body=(
            "One idea per note. Atomicity makes notes reusable and linkable — "
            "the foundation of [[Zettelkasten]]."
        ),
    ),
    NoteCreate(
        title="Bidirectional Links",
        tags=["pkm", "principle"],
        body=(
            "When note A links to note B, B should know about A. Backlinks turn "
            "a pile of notes into a navigable graph and power "
            "[[Linking Your Thinking]]."
        ),
    ),
]


def seed_if_empty(notes: NoteService) -> None:
    if notes.vault.list_ids():
        return
    for payload in _SEED:
        notes.create(payload)
