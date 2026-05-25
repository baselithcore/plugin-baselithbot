# Wiki White-Label

Motore white-label che trasforma il [pattern Karpathy LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) in un prodotto multi-verticale. Singola base di codice Python, singolo frontend React — basta cambiare `APP_DOMAIN` per istanziare una wiki Legale, Medica, Tecnica, Assicurativa (o qualsiasi altra) senza toccare il motore core.

Il core non legge mai stringhe specifiche del dominio. Prompt, regole di frontmatter, tassonomie delle pagine, etichette UI e strategie di ingest vivono tutte sotto `domains/<APP_DOMAIN>/` come un **Domain Pack** auto-contenuto.

> **Solo valutare il motore?** Vai a [`docs/quickstart-5min.md`](docs/quickstart-5min.md): tre comandi, fork di un seed, prima risposta in 5 minuti. Per la guida completa: [`docs/getting-started.md`](docs/getting-started.md).

## Panoramica

```text
wiki-white-label/
├── llm_wiki/                 # motore agnostico rispetto al dominio
│   ├── domain/               #   contratto del pack + prompt Jinja2 + schema + strategie
│   ├── agents/               #   agente RAG (renderizza i prompt via PromptRegistry)
│   ├── ingest_raw/           #   pipeline PDF → wiki, smistata via PageTypeStrategy
│   ├── vectorstore/          #   embedder/qdrant/hybrid/reranker (agnostico)
│   ├── wiki/                 #   parser + gruppi (guidati dal pack)
│   ├── graphdb/  utils/      #   helper agnostici
│   ├── config.py             #   APP_DOMAIN + COLLECTION_NAME=<domain>-wiki
│   └── cli.py                #   `wiki-wl init/serve/ingest/pack list`
├── domains/
│   ├── _template/            # scaffold copiato da `init --domain <name>`
│   └── insurance/            # porting completo dell'MVP rag-wiki
├── frontend/                 # React 19 + Vite + Tailwind v4
├── main.py                   # server FastAPI
├── pyproject.toml
└── .env.example
```

## Nuovo verticale in cinque minuti

Due strade equivalenti — il wizard UI e il CLI condividono lo stesso modulo `llm_wiki.admin.scaffold`, quindi producono lo stesso pack.

### A. Wizard UI (consigliato)

```bash
pip install -e ".[hybrid,ingest]"
docker compose up -d qdrant
python -m llm_wiki serve --reload      # APP_DOMAIN può rimanere unset
cd frontend && npm install && npm run dev
```

Apri `http://localhost:5173`. Quando `APP_DOMAIN` è unset il backend risponde con `setup_mode: true` su `/api/branding` e il frontend apre automaticamente il **Setup Wizard** in modalità bloccante. Compila identità → vault → provider (opzionale) → revisione, applica, riavvia il backend con il comando suggerito.

A wiki esistenti il wizard si raggiunge via:

- bottone ✨ in header
- command palette `⌘/` → "Crea nuova wiki…"
- scorciatoia `⌘⇧N`

Multi-tenant: la lista mostra tutti i pack sotto `domains/` e permette di switch-are l'`APP_DOMAIN` (richiede riavvio — runtime single-active in fase 1).

### B. CLI

```bash
pip install -e ".[hybrid,ingest]"      # aggiungi `graph` se usi FalkorDB
python -m llm_wiki init --domain legal --label "Wiki Legale"
$EDITOR domains/legal/pack.yaml
$EDITOR domains/legal/prompts/system.j2
docker compose up -d qdrant
python -m llm_wiki serve --reload
cd frontend && npm install && npm run dev
```

Il frontend idrata le etichette da `GET /api/branding` all'avvio. Cambiare il pack = riavviare il backend; il bundle React viene riutilizzato così com'è.

### Sicurezza degli endpoint admin

Gli endpoint `/api/admin/*` (scaffold + tenant management) **scrivono** su `domains/` e `.env`. Sono attivi solo se `ADMIN_API_ENABLED=true` (default `true`) e di default rifiutano client non-loopback (`ADMIN_API_LOOPBACK_ONLY=true`). In produzione, dietro reverse proxy, valutare `ADMIN_API_ENABLED=false` e usare il CLI sull'host.

## Contratto del Domain Pack

Un pack è una directory con questo layout:

```text
domains/<name>/
├── pack.yaml          # schema pydantic DomainPack (vedi llm_wiki/domain/pack.py)
├── schema.yaml        # regole di frontmatter per page_type (validate da FrontmatterSchema)
├── prompts/
│   ├── system.j2      # prompt di sistema dell'agente RAG
│   ├── user.j2        # template utente RAG (variabili: context, question)
│   ├── no_hits.j2     # fallback quando la ricerca è vuota
│   └── ingest/        # template della pipeline di ingest (classify/plan/source/entity/refine/...)
├── examples/          # pagine wiki di esempio few-shot usate dal generatore
└── strategies.py      # opzionale: hook PageTypeStrategy + frontmatter_defaults
```

`pack.yaml` dichiara:

- `page_types[]` — la tassonomia. Gli ID viaggiano attraverso il frontmatter, gli enum JSON-Schema e i nomi delle cartelle.
- `subtypes` — sottoclassificazione opzionale per tipo di pagina (usata dal JSON-Schema del planner).
- `grouping[]` — gruppi dichiarativi serviti da `GET /api/groups?rule=<key>`. Sostituisce l'endpoint `/api/editions` codificato dell'MVP di riferimento.
- `ui` — etichette passate al frontend da `/api/branding`.

## Contratto del Runtime

| Endpoint | Scopo |
| -------- | ----- |

| `GET /api/status`       | Pack + provider + Qdrant + snapshot del vault |
| `GET /api/branding`     | Etichette UI + tipi di pagina + regole di raggruppamento |
| `GET /api/groups`       | Lista delle regole di raggruppamento dichiarate dal pack |
| `GET /api/groups/{key}` | Materializza una regola di raggruppamento contro il vault |
| `POST /api/chat`        | RAG one-shot con citazioni |
| `POST /api/chat/stream` | Stream di eventi NDJSON dell'agente RAG |
| `POST /api/ingest/raw`  | Carica un PDF, avvia il job di ingest in background |
| `GET  /api/ingest/raw/jobs/{id}/stream` | Segui un job di ingest |
| `POST /api/feedback`    | Appende pollici su/giù al log JSONL |

## Regole White-label imposte dal motore

1. **I prompt non vivono mai nel sorgente Python.** `llm_wiki/agents/rag_agent.py` e `llm_wiki/ingest_raw/prompts.py` risolvono ogni stringa via `PromptRegistry.render(name, **vars)`.
2. **La tassonomia delle pagine è basata sui dati.** Il rilevamento del tipo di pagina del parser usa `pack.page_types[*].folder`; i default del frontmatter dell'orchestratore compongono le chiavi fornite dal pack.
3. **Nessun percorso relativo sparso in giro.** Tutti gli I/O del filesystem derivano da `config.WIKI_ROOT`, `config.RAW_DIR`, o `pack.root`.
4. **Le chiavi API rimangono in `.env`.** Mai lette da `pack.yaml` o da qualsiasi file sotto `domains/`.
5. **Single-tenant per design.** Un processo = un `APP_DOMAIN`. Per cambiare = riavviare.

## Multi-tenancy a livello sessione utente (in corso)

Il rifacimento attivo (branch `wizard-ui`) sposta la multi-tenancy dal livello "Domain Pack" (vertical) al livello "sessione utente". Wiki, vector store, raw PDF restano risorse **condivise** fra tutti gli utenti. Chat, memorie utente (RAG personale), feedback diventano isolati per `tenant_id` con 1:1 user↔tenant — pattern allineato a `agent-jira`.

**Stack:** Postgres 16 + pgvector, JWT HS256 access + refresh opaco rotato, RLS Postgres, PBKDF2-SHA256, rate limit Redis sliding-window.

**Variabili d'ambiente nuove (Fase 0):** aggiungi a `.env`:

```bash
# --- DB Postgres (obbligatorio con auth) -----------------------------------
DATABASE_URL=                       # opzionale, override completo
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=llm_wiki
POSTGRES_USER=llm_wiki
POSTGRES_PASSWORD=llm_wiki_dev      # cambiare in prod
# Ruolo runtime non-superuser per RLS effettivo (creato da migration 006).
# Lascia DB_USER=postgres iniziale; switcha a app_runtime in prod dopo verifica.

# --- Auth (Fase 2) ---------------------------------------------------------
SECRET_KEY=                         # min 32 byte random per JWT HS256
AUTH_REQUIRED=true                  # rotte chat/conversations/memories chiuse
AUTH_PUBLIC_REGISTRATION=false      # default: solo admin invita
AUTH_COOKIE_SECURE=true             # false in dev su http://localhost
AUTH_COOKIE_SAMESITE=strict
ACCESS_TOKEN_TTL_MINUTES=1440       # 24h
REFRESH_TOKEN_TTL_DAYS=30
MULTI_TENANT_REQUIRED=true

# --- Bootstrap admin (primo boot) ------------------------------------------
ADMIN_BOOTSTRAP_EMAIL=admin@example.com
ADMIN_BOOTSTRAP_PASSWORD=           # se vuota, generata random e stampata UNA volta su stderr

# --- Rate limit / cache (opzionali) ----------------------------------------
CACHE_BACKEND=memory                # memory | redis
CACHE_REDIS_URL=redis://localhost:6380/0
RATE_LIMIT_USER_PER_MINUTE=120
RATE_LIMIT_ADMIN_PER_MINUTE=60
RATE_LIMIT_WINDOW_SECONDS=60
```

**Bring-up Fase 0:**

```bash
pip install -e ".[hybrid,ingest,auth]"
docker compose up -d qdrant postgres                # minimo
docker compose --profile auth up -d                 # + redis opzionale
alembic upgrade head                                # crea schema (Fase 1)
```

Le migrations Alembic e il pacchetto `llm_wiki.db` sono predisposti in Fase 0; logica auth + endpoint conversations/memories arrivano nelle fasi 1–6 (vedi `alembic/README.md` per il piano migrations).

## Domain Pack: il riferimento assicurativo

`domains/insurance/` è il porting completo dell'MVP `rag-wiki`:

- 4 template RAG + 13 template di ingest sotto `prompts/`
- `pack.yaml` dichiara il raggruppamento `editions` (sostituisce `/api/editions`)
- `schema.yaml` contiene il frontmatter contrattuale (`edizione-iso`, `codice-prodotto`, `rango`, `stato`)
- `strategies.py` registra tre istanze di `PageTypeStrategy` (source, garanzia, entity) e un hook `frontmatter_defaults` per la propedeuticità

Usalo come esempio concreto quando scrivi un nuovo verticale.

## Test

```bash
pytest tests/                 # smoke test per caricatore pack, registro prompt, schema, gruppi
ruff check .                  # lint
mypy llm_wiki                 # tipi
```

## Ringraziamenti

Costruito sull'idea di [rag-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (Andrej Karpathy) e sull'MVP originale delle assicurazioni italiane. Il recupero ibrido usa Qdrant + BGE-M3; l'estrazione PDF usa IBM Docling. Il frontend è React 19 + Vite + Tailwind v4 + framer-motion.
