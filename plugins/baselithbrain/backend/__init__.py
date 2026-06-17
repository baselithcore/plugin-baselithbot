"""BaselithBrain backend — local-first second-brain API.

Layered, decoupled by responsibility (each module < 500 LOC):

- :mod:`models`         — DTOs (Note, GraphNode/Edge, SearchHit)
- :mod:`frontmatter`    — YAML frontmatter parse/serialize (open format)
- :mod:`vault`          — local Markdown file IO (source of truth)
- :mod:`notes`          — NoteService CRUD over the vault
- :mod:`links`          — ``[[wikilink]]`` parsing + backlink index
- :mod:`search_service` — BM25 (+ optional semantic) over note bodies
- :mod:`graph_service`  — explicit + derived edges, neighborhoods, clusters
- :mod:`index_state`    — in-memory derived index (rebuildable from disk)
- :mod:`app`            — FastAPI app + lifespan + routers

The UI (indexing logic) is fully separated from the API surface; the derived
index is disposable and never written back into the user's files.
"""
