# CLI Reference

Comandi e script disponibili.

## Engine

### `python -m docheck.main`

Entry point engine. Avvia FastAPI su Unix socket (default) o TCP loopback (se `DOCHECK_BIND_TCP` settato).

```bash
cd docheck-engine
uv run python -m docheck.main
```

Lifespan startup: setup logging → mkdir storage → setup tracing → migrate DB → install RLS hook → reindex policy index → log startup.

### Alembic migrations

```bash
cd docheck-engine
uv run alembic upgrade head                    # apply all
uv run alembic current                         # version corrente
uv run alembic history                         # log migrations
uv run alembic revision -m "<msg>" --autogenerate
```

Migrations in [docheck-engine/alembic/versions/](../../docheck-engine/alembic/).

## Scripts

In [scripts/](../../scripts/).

### `seed_admin.py`

Crea utente admin locale (argon2id password hash, ruolo `admin`).

```bash
uv run --project docheck-engine python scripts/seed_admin.py
# Stdout: admin created — email: admin@local | password: <generated>
```

Edit per cambiare credenziali default. Esegui una sola volta per ambiente.

### `seed_policies.py`

Carica policy di esempio (IT/EU baseline) nel DB del tenant `default`.

```bash
uv run --project docheck-engine python scripts/seed_policies.py
```

### `seed_tenant.py`

Crea un tenant nuovo (multi-tenant only).

```bash
uv run --project docheck-engine python scripts/seed_tenant.py --id acme --title "Acme Corp"
```

### `mock_llm.py`

Server LLM stub OpenAI-compatible per dev offline / test E2E.

```bash
uv run --project docheck-engine python scripts/mock_llm.py
# → listening on http://127.0.0.1:8001
```

In `.env`: `DOCHECK_LLM_BASE_URL=http://127.0.0.1:8001/v1`.

### `kpi.py`

Esegue valutazione precision/recall su test set annotato.

```bash
uv run --project docheck-engine python scripts/kpi.py \
  --dataset path/to/annotated/ \
  --policies EU_GDPR_2018,DocCheck_Builtin \
  --output-dir reports/kpi
```

Output: precision/recall/F1 per severity + per rule_id + confusion matrix. Vedi [runbooks/kpi-evaluation.md](../runbooks/kpi-evaluation.md).

### `check_file_loc.sh`

Validation gate: ogni file source ≤ 500 LOC ([CLAUDE.md §1.1](../../CLAUDE.md)).

```bash
./scripts/check_file_loc.sh
# Exit 1 se almeno un file > 500 LOC senza eccezione
```

CI esegue questo gate.

### `run_eslint.sh`

Wrapper ESLint per UI con flag standard.

```bash
./scripts/run_eslint.sh
```

## UI

In [docheck-ui/](../../docheck-ui/), via pnpm:

```bash
pnpm dev                           # Next.js dev server (http://localhost:3000)
pnpm build                         # static export
pnpm start                         # serve build
pnpm lint                          # eslint
pnpm typecheck                     # tsc --noEmit
pnpm test                          # vitest

pnpm electron:dev                  # Electron shell + Next dev
pnpm electron:build                # build installer (firmato/notarized in CI)
```

## Docker

```bash
# Single-tenant DGX
docker compose -f docker/compose.yml up -d
docker compose -f docker/compose.yml logs -f engine

# Multi-tenant (Postgres + Qdrant)
docker compose -f docker/compose.postgres.yml up -d

# Build solo engine image
docker build -f docheck-engine/Dockerfile -t docheck-engine:0.1.0 .
```

## Helm

```bash
helm install docheck ./docker/helm/docheck \
  --namespace docheck --create-namespace \
  --set multiTenant.enabled=true \
  -f my-values.yaml

helm upgrade docheck ./docker/helm/docheck -f my-values.yaml
helm rollback docheck 1
helm uninstall docheck -n docheck
```

Values reference: [docker/helm/docheck/values.yaml](../../docker/helm/docheck/values.yaml).

## API CLI client

Engine espone HTTP/WS standard. Esempi `curl`:

```bash
# Health
curl http://localhost:8765/api/v1/health

# Login
curl -X POST http://localhost:8765/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@local","password":"<password>"}'
# → {"user_id":"u-...","token":"<jwt>"}

# Upload
curl -X POST http://localhost:8765/api/v1/documents \
  -H "Authorization: Bearer <jwt>" \
  -F "file=@contract.pdf"

# Analyze
curl -X POST http://localhost:8765/api/v1/documents/<doc_id>/analyze \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"policies": ["EU_GDPR_2018"]}'

# Audit verify
curl http://localhost:8765/api/v1/audit/verify \
  -H "Authorization: Bearer <jwt>"
```

Vedi [api/endpoints.md](../api/endpoints.md) per reference completa.

## Telemetry

OpenTelemetry locale, file exporter:

```bash
# trace file: storage/otel-traces.jsonl
tail -f storage/otel-traces.jsonl | jq .
```

Nessun exporter cloud. Per Grafana opzionale: `docker compose --profile observability up`.
