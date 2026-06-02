# BaselithWiki

White-label **LLM wiki engine** embedded as a BaselithCore plugin: domain-agnostic
RAG chat, PDF→wiki ingestion, hybrid Qdrant retrieval, an optional knowledge graph,
and multi-tenant auth — served together with its React/Vite single-page app.

The upstream *Wiki White-Label* engine is vendored **verbatim** under
[`llm_wiki/`](llm_wiki/), [`domains/`](domains/), [`alembic/`](alembic/) and
[`_wiki_main.py`](_wiki_main.py). All integration logic lives in the thin wrapper —
the engine source is byte-identical to upstream.

## How it integrates

| Concern | Mechanism |
|---|---|
| **Mount** | The engine app (`_wiki_main.app`, all routers at their canonical `/api/*`, `/auth/*`, `/health/*`, `/metrics` paths) is mounted as a Starlette sub-application at `/baselithwiki` via [`plugin.py`](plugin.py)'s `setup_app_middleware` hook. Starlette strips the mount prefix, so the engine keeps seeing its own paths — zero route rewrites. |
| **SPA** | [`app_factory.py`](app_factory.py) grafts a trailing `{path:path}` catch-all that serves built assets from `frontend/dist` and falls back to `index.html` for client-side deep links. Registered last → every engine route still wins. |
| **Lifespan** | A mounted sub-app gets no ASGI lifespan events, so `initialize()` enters the engine's own `lifespan` context (verbatim: pack load, optional Postgres bootstrap, embedder + Qdrant warmup, autostart ingest) in a **background task** so a cold model download never blocks core boot. |
| **Config isolation** | [`_bootstrap.py`](_bootstrap.py) stops the host `.env` (which ships generic keys like `POSTGRES_ENABLED`, `APP_DOMAIN`) from bleeding into the engine. It pins safe **setup-mode** defaults and exposes a `BASELITHWIKI_<KEY>` override channel. |

## Configuration

Boots in self-contained **setup mode** (no Postgres, no auth, all endpoints public).
Open `/baselithwiki` and run the setup wizard, or opt into a vertical / external
services with scoped env vars (promoted to the bare key the engine reads):

```bash
export BASELITHWIKI_APP_DOMAIN=insurance        # activate a domain pack
export BASELITHWIKI_POSTGRES_ENABLED=true       # enable auth/conversations/memories
export BASELITHWIKI_AUTH_REQUIRED=true
export BASELITHWIKI_SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))")
export BASELITHWIKI_OLLAMA_URL=http://localhost:11434
export BASELITHWIKI_OLLAMA_MODEL=llama3.1:8b
```

Bundled domain packs: `insurance`, `legal`, `medical`, `technical`, `hr`,
`it_support`, `technical_custom` (+ `_template`).

## Runtime dependencies

The vendored engine imports its deps eagerly — install them in the host env
(see `manifest.yaml → python_dependencies`). Optional verticals add extras:
`FlagEmbedding` (hybrid sparse retrieval), `falkordb`+`networkx` (graph),
`docling`+`pymupdf` (PDF ingestion). With `POSTGRES_ENABLED=true`, run the
bundled Alembic migrations against the target database.

## Rebuilding the SPA

Only the compiled `frontend/dist/**` ships in the wheel. To rebuild after
editing the UI:

```bash
cd plugins/baselithwiki/frontend
npm install
VITE_BASE_PATH=/baselithwiki/ VITE_API_URL=/baselithwiki/api npm run build
```

`VITE_BASE_PATH`/`VITE_API_URL` default to upstream standalone values when unset,
so the source stays drop-in compatible with the original project.
