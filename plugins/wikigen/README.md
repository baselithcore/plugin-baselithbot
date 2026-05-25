# wikigen — BaselithCore plugin

White-label LLM wiki engine ported from
[`llm-wiki-grafiphy`](https://github.com/giovanni-ippolito/llm-wiki-grafiphy)
as a self-contained BaselithCore plugin. Domain-pack-driven RAG +
PDF→wiki ingest pipeline, Postgres + JWT auth, hierarchical RBAC, optional
FalkorDB knowledge graph, embedded Qdrant, React + Vite SPA.

## Status

**Port fidelity:** 1:1 with the legacy `main.py` lifespan. Source tree
copied verbatim under [llm_wiki/](llm_wiki/); imports preserved (`from
llm_wiki.* import …`) via a `sys.path` bootstrap inside
[plugin.py](plugin.py).

**No regressions intended.** Behaviour parity asserted by reusing the
original [tests/](tests/), [alembic/](alembic/) migrations, and
[domains/](domains/) packs.

## Layout

```text
plugins/wikigen/
├── plugin.py                 # WikigenPlugin (RouterPlugin) — entry point
├── __init__.py               # re-export
├── manifest.yaml             # baselithcore plugin metadata
├── .env.example              # full env reference (copy → .env)
├── llm_wiki/                 # wikigen source (UNCHANGED — 194 modules, ~38K LoC)
├── alembic/                  # 18 plugin-owned Postgres migrations
├── alembic.ini               # alembic config (path-relative)
├── domains/                  # bundled domain pack templates (hr, legal, …)
├── ui/                       # React + Vite SPA (build → ui/dist/)
├── docs/                     # ported documentation
├── tests/                    # ported pytest suite
├── scripts/                  # ops scripts (backup, audit, chaos)
├── deploy/                   # systemd + reverse-proxy + observability stack
├── main.legacy.py            # ARCHIVED original entry — not used at runtime
├── pyproject.legacy.toml     # ARCHIVED deps reference — see manifest.yaml
└── README.legacy.md          # ARCHIVED original README
```

## Quickstart

### 0. Enable the plugin

Add wikigen to [`configs/plugins.yaml`](../../configs/plugins.yaml) (already
wired in the default repository config):

```yaml
wikigen:
  enabled: true
```

The plugin loads lazily — its routes mount on the first matching request
(or eagerly when `plugin_registry.ensure_plugin_active('wikigen')` is
called from your own code). App-level middleware
(`WikigenPlugin.setup_app_middleware`) is auto-invoked by
`core.api.factory.create_app()` via the generic plugin hook, so no manual
wiring is required.

### 1. Install Python dependencies

Plugin extras are declared in [manifest.yaml](manifest.yaml) under
`python_dependencies`. Host's `pyproject.toml` already covers the
common surface (fastapi, pydantic, psycopg, httpx, prometheus-client).
Pip-install the wikigen-specific extras manually until the BaselithCore
loader auto-resolves them:

```bash
pip install \
  qdrant-client sentence-transformers openai ollama \
  langchain-text-splitters typer rich alembic \
  pyjwt email-validator python-multipart
# Optional capability extras (see pyproject.legacy.toml for the full matrix)
pip install FlagEmbedding              # hybrid retrieval
pip install falkordb redis networkx python-igraph leidenalg  # knowledge graph
pip install docling pymupdf pdfplumber                       # PDF ingest
```

### 2. Configure environment

```bash
cp plugins/wikigen/.env.example plugins/wikigen/.env
chmod 0600 plugins/wikigen/.env
# Edit: set APP_DOMAIN, POSTGRES_URL, SECRET_KEY, LLM_VENDOR, …
```

The BaselithCore plugin loader auto-loads `plugins/wikigen/.env` at
plugin init (see
[loader.py:131](../../core/plugins/loader.py#L131)).

### 3. Run migrations

```bash
cd plugins/wikigen
alembic -c alembic.ini upgrade head
```

### 4. Boot baselithcore

```bash
python backend.py
# or
baselith
```

Wikigen mounts at:

- `/api/chat`, `/api/wiki`, `/api/feedback`, `/api/ingest`, `/api/graph`,
  `/api/system`, `/api/health`, `/api/metrics`, `/api/embed/*`
- (Postgres on) `/api/auth`, `/api/conversations`, `/api/memories`,
  `/api/rbac`, `/api/rbac/groups`, `/api/rbac/lifecycle`, `/api/gdpr`,
  `/api/embeds`, `/api/admin/feedback`
- (Admin on) `/api/admin/*`
- (SPA) `/plugins/wikigen/static/*` and `/wikigen` (if `ui/dist/` built)

## Middleware (opt-in)

The original `main.py` registers app-level middleware (RequestId, CORS,
EmbedCORS, TenantMiddleware, SecurityHeaders, HttpMetrics, AdminGate).
BaselithCore's plugin contract exposes no app-middleware hook, so
**wikigen-specific middleware is NOT auto-applied**.

For full parity, invoke the helper once during app construction:

```python
# baselithcore-host/your_app.py
from core.api.factory import create_app
from plugins.wikigen import WikigenPlugin

app = create_app()
WikigenPlugin.apply_app_middleware(app)
```

This preserves the exact ordering from the legacy `main.py`:

```text
request → RequestId → CORS → SecurityHeaders → TenantMiddleware
                                              → HttpMetrics → routes
```

When `POSTGRES_ENABLED=true` it adds `EmbedCORSMiddleware` (path-scoped
preflight for `/api/embed/*`) and `TenantMiddleware`. When
`ADMIN_API_ENABLED=true` it mounts the loopback/bearer admin gate over
`/api/admin/*`.

## Frontend

```bash
cd plugins/wikigen/ui
npm install
npm run build       # outputs to ui/dist/
```

The plugin auto-serves `ui/dist/` via
[`get_static_assets_path`](plugin.py) — the BaselithCore lifespan mounts
it at `/plugins/wikigen/static` and (if `index.html` exists) also at
`/wikigen` as an SPA.

## CLI

The legacy CLI entrypoint `wiki-wl` is preserved at
[llm_wiki/cli/](llm_wiki/cli/). To invoke it from the plugin tree:

```bash
cd plugins/wikigen
python -m llm_wiki <command>     # e.g. init, ingest, doctor, status
```

## Architecture notes

- **Imports preserved verbatim** (650+ `from llm_wiki...` references). The
  plugin directory is injected into `sys.path` at module load so the
  nested `llm_wiki/` package resolves as a top-level import. See
  [plugin.py](plugin.py) header.
- **Lifespan parity** — `WikigenPlugin.initialize()` mirrors `main.py`'s
  `lifespan` 1:1: pack load → SECRET_KEY guard → DB bootstrap →
  embedder/collection warmup (blocking) → LLM + reranker + examples
  warmup (background) → autostart pending ingest.
- **Plugin-owned migrations.** Wikigen's 18 alembic revisions live under
  [alembic/versions/](alembic/versions/) and are NOT merged into core's
  `/migrations/`. Sacred Core rule preserved.
- **Domain packs bundled.** [domains/](domains/) carries the canonical
  pack templates (`hr`, `legal`, `medical`, `technical`, `insurance`,
  `it_support`, `_template`). Custom packs live under
  `vaults/<domain>/` at runtime — selectable via `DOMAIN_PACK_DIR`.
- **No `core/` touched.** All wikigen logic, including auth and tenant
  middleware, lives inside `plugins/wikigen/` per the Sacred Core
  invariant.

## Known deviations from legacy

| Area | Legacy | Plugin |
|------|--------|--------|
| Entry point | `main.py:app` (uvicorn) | mounted by baselithcore `create_app()` |
| Middleware | auto-registered at app boot | opt-in via `WikigenPlugin.apply_app_middleware(app)` |
| Migrations | `alembic upgrade head` at repo root | `alembic -c plugins/wikigen/alembic.ini upgrade head` |
| Frontend dev | `cd frontend && vite` | `cd plugins/wikigen/ui && vite` |
| CLI | `wiki-wl <cmd>` | `python -m llm_wiki <cmd>` (until baselith CLI wires the entry point) |

## See also

- Original architecture brief: [docs/architecture.md](docs/architecture.md)
- Domain-pack spec: [docs/domain-pack-spec.md](docs/domain-pack-spec.md)
- Auth + RBAC: [docs/auth-rbac.md](docs/auth-rbac.md)
- Quickstart 5min: [docs/quickstart-5min.md](docs/quickstart-5min.md)
- Migration from rag-wiki: [docs/migration-from-rag-wiki.md](docs/migration-from-rag-wiki.md)
