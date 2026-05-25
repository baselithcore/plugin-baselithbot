# docheck — BaselithCore plugin

doCheck — Document Compliance Checker — ported as a self-contained
BaselithCore plugin. Local-first, glass-box, multi-agent compliance checker
for enterprise documents (PDF, DOCX, XLSX, MD). Every finding ships with
verbatim policy excerpt, page-level bbox, and step-by-step agent reasoning.
On-prem LLM via Ollama/vLLM, Ed25519-signed audit chain, BGE-M3 multilingual
embeddings (IT + EN native).

## Status

**Port fidelity:** 1:1 with the legacy `docheck-engine/src/docheck/main.py`
lifespan. Source tree copied verbatim under [docheck/](docheck/); imports
preserved (`from docheck.* import …`) via a `sys.path` bootstrap inside
[plugin.py](plugin.py). 84 modules, 9 Alembic migrations, full LangGraph
agent pipeline.

**No regressions intended.** Behaviour parity asserted by reusing the
original [tests/](tests/), [alembic/](alembic/) migrations, and shared
[docs/shared-schemas/](docs/shared-schemas/) finding schema.

## Layout

```text
plugins/docheck/
├── plugin.py                 # DoCheckPlugin (RouterPlugin) — entry point
├── __init__.py               # re-export
├── manifest.yaml             # baselithcore plugin metadata
├── docheck/                  # docheck-engine source (UNCHANGED — 84 modules)
│   ├── main.py               # original FastAPI entry — kept for parity, not used at runtime
│   ├── api/                  # 10 routers (auth, documents, policies, findings, …)
│   ├── agents/               # LangGraph: Classifier → Structurer → [Legal | Technical | PII] → Synthesizer
│   ├── core/                 # config, security, jwt, oidc, logging, telemetry, doc taxonomy, tenant
│   ├── db/                   # SQLAlchemy models, session, RLS hook, migrate
│   ├── schemas/              # Pydantic models (Finding, CheckState)
│   └── services/             # parsers (PDF/DOCX/XLSX/MD), embedding, llm, policy index, audit, eval
├── alembic/                  # 9 plugin-owned DB migrations
├── alembic.ini               # alembic config (path-relative)
├── ui/                       # Next.js 15 + React 19 + Electron 33 SPA (build → .next/ or out/)
├── docs/                     # ported documentation
│   ├── blueprint/            # product blueprint (00 overview … 09 wireframes)
│   ├── shared-schemas/       # finding.schema.json (JSON Schema for Finding model)
│   └── *.original            # archived top-level docs from docheck repo
├── deploy/                   # docker compose + helm skeleton
├── scripts/                  # seed_admin, seed_policies, mock_llm, kpi
└── tests/                    # ported pytest suite
```

## Quickstart

### 0. Enable the plugin

Add `docheck` to `configs/plugins.yaml`:

```yaml
docheck:
  enabled: true
```

The plugin loads lazily — routes mount on the first matching request (or
eagerly via `plugin_registry.ensure_plugin_active('docheck')`). App-level
middleware (`DoCheckPlugin.setup_app_middleware`) is auto-invoked by
`core.api.factory.create_app()` via the generic plugin hook.

### 1. Install Python dependencies

Plugin extras are declared in [manifest.yaml](manifest.yaml) under
`python_dependencies`. The host's `pyproject.toml` already covers the
common surface (fastapi, uvicorn, pydantic, sqlalchemy, alembic,
structlog, opentelemetry). Pip-install the docheck-specific extras until
the BaselithCore loader auto-resolves them:

```bash
pip install \
  "pydantic[email]" pydantic-settings \
  argon2-cffi cryptography pynacl "python-jose[cryptography]" \
  python-multipart aiofiles \
  langgraph langchain langchain-community llama-index \
  chromadb qdrant-client FlagEmbedding \
  pdfplumber python-docx openpyxl markdown-it-py \
  paddlepaddle paddleocr pdf2image numpy \
  openai lingua-language-detector keyring
```

Optional SQLCipher extras (requires `brew install sqlcipher` or
`apt-get install libsqlcipher-dev`):

```bash
pip install sqlcipher3
```

### 2. Configure environment

DoCheck uses Pydantic-settings with the `DOCHECK_` prefix. Minimal local
dev configuration:

```bash
export DOCHECK_STORAGE_ROOT=./storage
export DOCHECK_LLM_PROVIDER=ollama
export DOCHECK_LLM_BASE_URL=http://127.0.0.1:11434/v1
export DOCHECK_LLM_PRIMARY_MODEL=llama3.1:8b
export DOCHECK_VECTOR_BACKEND=chroma
export DOCHECK_DB_BACKEND=sqlite
```

The full env surface (Postgres multi-tenant, OIDC, SQLCipher, retention,
builtin rule overrides) is documented in [manifest.yaml](manifest.yaml)
and [docs/blueprint/01_core_architecture.md](docs/blueprint/01_core_architecture.md).

### 3. Seed admin + policies

```bash
python plugins/docheck/scripts/seed_admin.py
python plugins/docheck/scripts/seed_policies.py
```

### 4. Run

The plugin's `initialize()` hook auto-runs Alembic `upgrade head`,
installs the RLS session hook, and reindexes policies into the vector
store. Just start the BaselithCore backend:

```bash
python backend.py
```

Routes mount under `/api/v1/*` (preserves the original docheck URL surface).

### 5. Build the UI

```bash
cd plugins/docheck/ui
pnpm install
pnpm build
```

`next build` populates `.next/` (or `out/` after `next export`); the
plugin's `get_static_assets_path()` picks the first available output.
Electron desktop bundle: `pnpm electron:build`.

## Security & Hardening

- **Zero cloud leak.** All LLM/embedding/OCR/vector compute is on-prem
  (Ollama, vLLM, ChromaDB embedded, BGE-M3 local). CI gates assert zero
  outbound packets via tcpdump during E2E.
- **Glass-box audit.** Every Finding cites its source chunk (page, line
  range, bbox) and policy excerpt verbatim. Hash-chained audit log
  (SHA-256 `prev_hash → entry_hash`) with Ed25519 signature on canonical
  JSON ensures non-repudiation.
- **Master-key custody.** SQLCipher key + audit signing key live in the
  OS keychain (macOS Keychain / Windows DPAPI / Linux secret-service)
  via the `keyring` package — never on disk in plaintext, never in
  environment variables. Wrap any in-memory key bytes in
  `pydantic.SecretStr` at the code boundary per CLAUDE.md.
- **Unix-domain socket by default.** No TCP exposure unless
  `DOCHECK_BIND_TCP` is set explicitly.
- **RBAC** via `@require("resource", "action")` decorator;
  argon2id local passwords; OIDC-ready (`docheck/core/oidc.py`).

## Migration from `docheck-engine` standalone repo

The legacy entry at `docheck-engine/src/docheck/main.py` is preserved
under [docheck/main.py](docheck/main.py) for reference but **is not used
at runtime** — its lifespan logic moved into `DoCheckPlugin.initialize`.
The middleware stack moved into `DoCheckPlugin.apply_app_middleware`.

The Unix-socket / TCP uvicorn boot in `main.main()` belongs to the host
process now (BaselithCore's `backend.py`), not to the plugin.

## Conventions

- File size cap: 500 LoC (CLAUDE.md). All modules respect this.
- All secrets wrapped in `pydantic.SecretStr` at code boundaries.
- New HTTP middleware is **pure ASGI** (no `BaseHTTPMiddleware`).
- No `core → plugins` imports. All integrations live inside the plugin.

## License

Proprietary — see source headers and `docs/SECURITY.md.original` for
disclosure policy.
