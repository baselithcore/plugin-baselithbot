# BaselithBrain — Second Brain (PKM) plugin

Local-first personal knowledge management, mounted at **`/baselithbrain`** as a
self-contained sub-app + React/Vite SPA.

## What it is

- **Local-first, open format.** Every note is a plain `<id>.md` file with YAML
  frontmatter in a vault on disk — the single source of truth. No proprietary
  or binary editor state. Portable to Obsidian or any Markdown tool.
- **Block-based editor** (TipTap/ProseMirror) with Markdown round-trip, a `/`
  slash menu (≤5 blocks), `[[` wikilink autocomplete, an outline/TOC panel and a
  word-count / reading-time status bar.
- **Zettelkasten + LYT.** `[[wikilinks]]` drive backlinks (with surrounding
  context), an interactive knowledge graph (filter by tags / similar edges),
  MOC suggestions and unlinked-mention hints.
- **Daily notes, templates, tag browser.** One dated journal entry per day,
  reusable note templates with `{{date}}`/`{{title}}` placeholders, and a
  sidebar tag index. Pin & recent notes for fast re-access; focus mode hides the
  chrome for distraction-free writing.
- **Data safety.** Every save snapshots a recoverable **version history**;
  delete is a soft delete to a **trash** (restore or purge). Export a single
  note (`.md`) or the whole workspace (`.zip`).
- **Fast, keyboard-first.** `⌘/Ctrl+K` command palette (full-text search +
  actions), `⌘/Ctrl+G` graph, `⌘/Ctrl+J` assistant. KBD hints everywhere.
- **Calm, professional UI.** Neutral "Slate" design system (Obsidian/Linear-like
  — flat panels, single accent, minimal motion), light + dark themes.
- **Internationalized.** English + Italian out of the box (react-i18next), with
  an in-app language switcher; locale persists across sessions.
- **Zero infrastructure.** Keyword search (BM25) and the link graph are derived
  in-memory from the vault — no DB required. Semantic search/edges are opt-in.

## Architecture (UI decoupled from indexing)

```
plugin.py / app_factory.py   host wrapper: mount sub-app + serve SPA
backend/                     FastAPI API (persistence vs. derived index)
  vault.py  frontmatter.py   local Markdown IO (source of truth)
  notes.py                   CRUD service
  links.py                   [[wikilink]] parsing + backlinks
  search_service.py          BM25 (+ optional semantic) over note bodies
  graph_service.py           explicit/tag/derived edges, neighborhoods, MOCs
  semantic.py                optional embeddings (degrades gracefully)
  index_state.py             in-memory derived read model (rebuildable)
  routers/                   notes / search / graph / health
ui/                          React + Vite + Tailwind v4 + TipTap SPA
```

The derived index is disposable and never written back to the user's files.

## Develop

```bash
# Build the SPA (required before the wheel / serving in prod)
VITE_BASE_PATH=/baselithbrain/ npm --prefix plugins/baselithbrain/ui install
VITE_BASE_PATH=/baselithbrain/ npm --prefix plugins/baselithbrain/ui run build

# Run the host; open http://localhost:8000/baselithbrain
python backend.py
```

### Config (env, all optional)

| Var | Default | Effect |
| --- | --- | --- |
| `BASELITHBRAIN_VAULT_ROOT` | `plugins/baselithbrain/vault` | Where notes live |
| `BASELITHBRAIN_SEMANTIC_ENABLED` | `false` | Embedding search + derived graph edges |
| `BASELITHBRAIN_WATCH_ENABLED` | `false` | Reserved for filesystem watching |

After editing any `.py`, recompute `integrity_sha256` in `manifest.yaml` via
`core.plugins.integrity.compute_plugin_hash`.
