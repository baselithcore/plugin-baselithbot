# agent-jira (BaselithCore plugin)

Full, verbatim port of the [agent-jira](https://github.com/giovanni-ippolito/agent-jira)
Agile Project Manager + Jira automation engine into the BaselithCore plugin
ecosystem.

The plugin preserves the original FastAPI surface 1:1 — same URL paths, same
behavior, same env knobs — wrapped in the BaselithCore `RouterPlugin`
contract so it loads alongside other plugins (`wikigen`, `docheck`,
`baselithbot`, …) via the standard plugin loader.

## What you get

- **Multi-agent runtime** — Orchestrator + RAG + Jira + Graph + Audit +
  Metadata agents (LangGraph), with cost-control guardrails.
- **Hybrid retrieval** — Sentence Transformers embeddings on Qdrant
  (embedded by default; server-mode opt-in), CrossEncoder reranker with
  feedback-driven boosts.
- **Document ingest** — Markdown, PDF (native + EasyOCR fallback), DOCX,
  XLSX, PPTX, images, plus optional web crawler (Playwright).
- **Knowledge graph** — FalkorDB / RedisGraph, with `GRAPH_RAG_ENABLED`
  GraphRAG SDK integration for graph-aware retrieval.
- **Jira automation** — Creates / updates Stories (and Test Cases) from
  generated user stories. Manual-approval mode opt-in.
- **Project planner** — Generates project plans, BDD scenarios
  (Given/When/Then) and QA test cases (toggle via
  `PROJECT_PLANNER_ENABLE_TEST_CASES`).
- **Multi-tenant SaaS** — Postgres row-level security, per-tenant Qdrant
  collections, Redis-scoped quotas, plan-based rate limiting.
- **Console UI** — React/Vite SPA under [ui/](ui/) with tabs Home,
  Conversation, Analysis, KB, plus the 4-step Jira Setup Wizard.
- **Widget** — Lightweight CSS/JS chatbot snippet for intranet embedding,
  served from `/static/chatbot/`.
- **Observability** — Prometheus `/metrics`, structlog JSON formatter
  opt-in, OpenTelemetry instrumentation (FastAPI + httpx + psycopg + redis).
- **Audit + Cost Control** — Ed25519-style append-only event log with
  optional block-on-risk; per-request token budgets via
  `CostControlMiddleware`.

## Layout

```
plugins/agent-jira/
├── plugin.py             # AgentJiraPlugin (RouterPlugin entrypoint)
├── manifest.yaml         # BaselithCore plugin metadata + deps + env vars
├── __init__.py           # exposes AgentJiraPlugin
├── README.md
├── alembic/
│   ├── env.py            # patched to import agent_jira.config
│   └── versions/         # 001..008 (feedback → audit → refresh tokens)
├── alembic.ini
├── agent_jira/           # renamed from agent-jira/app/ (1:1 port)
│   ├── config.py         # merged from agent-jira/config.py
│   ├── agents/           # Orchestrator, RAG, Jira, Graph, Audit, Metadata
│   ├── chat/             # ChatService, agent_workflow, retrieval, planner
│   ├── db/               # documents, feedback, tenants, users, schema
│   ├── doc_sources/      # filesystem, web crawler, OCR backends
│   ├── graphdb/          # FalkorDB core + retrieval + linking + reasoning
│   ├── integrations/jira # Jira REST client + tenant resolver
│   ├── project_manager/  # planner, story counter, models
│   ├── routers/          # auth, chat, index, metrics, status, console, …
│   ├── static/           # admin dashboard, chatbot widget, React build
│   ├── vectorstore/      # Qdrant ops, chunking, indexing, graph sync
│   └── …
└── ui/                   # React/Vite console (renamed from frontend/)
```

## Source-tree invariants

The port preserves the original codebase byte-for-byte except for two
mechanical rewrites:

1. **`from app.*` → `from agent_jira.*`** — the original `app/` package was
   renamed to `agent_jira/` so the plugin's top-level namespace is unique
   inside `plugins/` (BaselithCore convention).
2. **`from config import …` → `from agent_jira.config import …`** — the
   original top-level `config.py` was merged into the package as
   `agent_jira/config.py`.

No logic was changed. No fallbacks added. No code deleted. The original
[backend.py](https://github.com/giovanni-ippolito/agent-jira/blob/main/backend.py)
lifecycle — logging setup, Postgres init, tenant/users schema
provisioning, Qdrant collection creation, FalkorDB ping, document index
bootstrap — is reproduced exactly inside `AgentJiraPlugin.initialize()`,
and the seven app-level middlewares + two static mounts move to
`AgentJiraPlugin.apply_app_middleware()`.

## Loading

The BaselithCore plugin loader discovers the plugin via `manifest.yaml`
and `plugin.py`. Use the standard loader from your app factory:

```python
# Inside core.api.factory.create_app or equivalent
from core.plugins import PluginLoader

loader = PluginLoader()
await loader.load("plugins/agent-jira")
```

`core.api.factory.create_app` also invokes the
`setup_app_middleware` classmethod automatically, so the full middleware
stack + legacy `/static` and `/assets` mounts are wired without extra
glue.

## Routes (verbatim from upstream)

| Path | Source router |
| ---- | -------------- |
| `/auth/*` | `agent_jira/routers/auth.py` |
| `/chat`, `/chat/stream` | `agent_jira/routers/chat.py` |
| `/index/*` | `agent_jira/routers/index.py` |
| `/metrics` | `agent_jira/routers/metrics.py` |
| `/status`, `/health/ready` | `agent_jira/routers/status.py` |
| `/console/*` | `agent_jira/routers/console/__init__.py` |
| `/chatbot/*` | `agent_jira/routers/console/frontend.py` (`public_router`) |
| `/feedback`, `/admin/*` | gated on `ENABLE_FEEDBACK=true` |
| `/` → `/console/` | redirect |
| `/favicon.svg` | React favicon |

## Env knobs

The full surface is documented in `manifest.yaml` and the upstream
`.env.example`. Load-bearing keys:

- `POSTGRES_ENABLED`, `MULTI_TENANT_ENABLED`, `AUTH_REQUIRED`,
  `SECRET_KEY`
- `QDRANT_MODE` (`embedded` | `server`), `QDRANT_PATH`, `QDRANT_URL`,
  `COLLECTION_NAME`
- `GRAPH_DB_ENABLED`, `GRAPH_DB_URL`, `GRAPH_DB_NAME`,
  `GRAPH_RAG_ENABLED`
- `ENABLE_JIRA_AUTOMATION`, `JIRA_REQUIRE_MANUAL_APPROVAL`,
  `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`
- `OLLAMA_API_BASE`, `OLLAMA_MODEL`, `OPENAI`, `OPENAI_API_KEY`,
  `OPENAI_MODEL`, `EMBEDDER_MODEL`, `RERANKER_MODEL`
- `DOCUMENTS_PATH`, `INDEX_BOOTSTRAP_BACKGROUND`
- `COST_CONTROL_ENABLED`, `AGENT_MAX_TOKENS`

## Migrations

Run alembic from the plugin directory (the patched `env.py` adds the
plugin root to `sys.path` so `agent_jira.config` resolves):

```bash
cd plugins/agent-jira
alembic upgrade head
```

Migration chain (8 revisions):

```
001_baseline_feedback_table
002_add_tenants_and_tenant_id
003_add_users_table
004_drop_tenant_name_unique
005_strict_one_user_per_tenant
006_row_level_security
007_audit_events_table
008_refresh_tokens
```

## UI build

```bash
cd plugins/agent-jira/ui
npm install
npm run build       # outputs the React SPA used by /console/*
```

The build is consumed by `agent_jira/routers/console/frontend.py` and the
`/static`, `/assets` mounts registered in `apply_app_middleware`.

## Status

- All 174 Python files in the plugin tree compile (`py_compile`).
- Original URL surface preserved verbatim.
- Original env knobs preserved verbatim.
- Multi-tenant Postgres + row-level security migrations carried over.
- React/Vite frontend + chatbot widget + admin dashboard carried over.
