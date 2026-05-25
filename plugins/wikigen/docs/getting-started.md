# Getting Started

Tutorial end-to-end: dal `git clone` a una wiki funzionante con login, RAG attivo, e un primo PDF ingerito. Tempo stimato: **15–20 minuti** su macchina locale.

## Prerequisiti

| Componente | Versione | Note |
| ---------- | -------- | ---- |
| Python | ≥ 3.10 | `python --version` |
| Docker + Compose | ≥ 24 | Per Qdrant, Postgres, Redis |
| Node.js | ≥ 20 | Solo per frontend dev |
| `uv` (consigliato) | latest | Più veloce di `pip` |
| Ollama (locale) | ≥ 0.3 | Oppure account OpenAI compatibile |
| RAM | ≥ 16 GB | BGE-M3 + reranker + LLM 8B |
| GPU | opzionale | Senza GPU funziona, più lento |

## 1. Clone e dipendenze

```bash
git clone <repo-url> llm-wiki-general
cd llm-wiki-general

# Crea virtualenv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Installa engine + extra ingest e auth
pip install -e ".[hybrid,ingest]"

# Pre-commit (opzionale ma consigliato)
pre-commit install
```

## 2. Servizi infrastruttura

Profilo minimo (Qdrant + Postgres):

```bash
docker compose up -d qdrant postgres
```

Profili opzionali:

```bash
docker compose --profile auth up -d redis        # rate-limit distribuito
docker compose --profile graph up -d falkordb    # knowledge graph
```

Verifica:

```bash
docker compose ps
# qdrant     :6333  healthy
# postgres   :5433  healthy
```

## 3. Configurazione iniziale `.env`

Genera secret JWT (32+ byte):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Crea `.env` nella root:

```ini
# === Bootstrap minimo ===
SECRET_KEY=<incolla qui il token generato>

# Postgres viene auto-detectato se POSTGRES_HOST è definito
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=llm_wiki
POSTGRES_USER=llm_wiki
POSTGRES_PASSWORD=llm_wiki_dev

# Auth attiva (multi-utente)
AUTH_REQUIRED=true
AUTH_PUBLIC_REGISTRATION=false
AUTH_COOKIE_SECURE=false        # true in produzione (HTTPS)
AUTH_COOKIE_SAMESITE=lax        # strict in produzione

# LLM provider locale
LLM_VENDOR=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
INGEST_OLLAMA_MODEL=llama3.2:latest

# Lascia APP_DOMAIN VUOTO: il Setup Wizard lo popolerà.
APP_DOMAIN=
```

Riferimento completo: [`configuration.md`](configuration.md).

## 4. Migrazioni database

Applica lo schema multi-tenant (9 migrazioni cumulative):

```bash
alembic upgrade head
```

Verifica:

```bash
psql -h localhost -p 5433 -U llm_wiki -d llm_wiki -c "\dt"
# Vedrai: tenants, users, refresh_tokens, conversations, messages,
#         memories, audit_events, roles, permissions, role_permissions,
#         user_roles, user_domain_grants, setup_invitations
```

## 5. Pull modello LLM (se Ollama)

```bash
ollama pull llama3.1:8b
ollama pull llama3.2:latest    # ingest dedicato (più piccolo, più veloce)
```

## 6. Primo avvio del server

```bash
python -m llm_wiki serve --reload
```

Output atteso:

```txt
INFO  Postgres detected (DATABASE_URL/POSTGRES_HOST set)
WARN  APP_DOMAIN is not set - server in setup mode
INFO  Embedder warming (BAAI/bge-m3)
INFO  Reranker warming (BAAI/bge-reranker-v2-m3)
INFO  Application startup complete (uvicorn on :8000)
```

Lo stato `setup mode` è atteso: nessun Domain Pack è ancora attivo. L'admin API è raggiungibile **solo da loopback** (default `ADMIN_API_LOOPBACK_ONLY=true`).

## 7. Bootstrap utente amministratore

Due opzioni equivalenti:

### A) Via CLI (consigliato in produzione)

```bash
python -m llm_wiki create-superuser \
  --email admin@example.com \
  --password "<password forte>"
```

### B) Via endpoint loopback

```bash
curl -X POST http://127.0.0.1:8000/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"<password>"}'
```

Funziona solo finché `users` è vuota; rate-limit 1/h. Il primo utente riceve ruoli `superuser` + `admin`.

> Se ometti `ADMIN_BOOTSTRAP_PASSWORD` e abiliti `ADMIN_BOOTSTRAP_AUTOSTART=true`, al primo boot il server genera una password e la stampa una sola volta su stderr.

## 8. Frontend (sviluppo)

In una shell separata:

```bash
cd frontend
npm install
npm run dev
```

Apri `http://localhost:5173`. CORS è preconfigurato verso `:8000` da `main.py`.

## 9. Setup Wizard — primo Domain Pack

L'app rileva `setup_mode=true` e mostra il **Setup Wizard**. Step:

1. **Identità** — nome pack (`<name>` deve matchare `^[a-z_][a-z0-9_-]*$`), label, lingua, descrizione. I nomi `_template`, `default`, `active` sono riservati.
2. **Vault** — directory dove vivranno `wiki/` e `raw/`. Default `<repo>/vaults/<name>`.
3. **Provider LLM** — Ollama o OpenAI; modello, endpoint, API key.
4. **Documenti** — carica i PDF iniziali (opzionale). Vengono messi in `<vault>/raw/`.
5. **Review** — preview di `pack.yaml` + diff di `.env` (solo `APP_DOMAIN` e `WIKI_ROOT_<NAME>` sono modificati; le altre chiavi restano intatte).
6. **Done** — il backend riavvia, sintetizza prompt domain-tuned (vedi `architecture.md`), crea la collezione Qdrant e mette in coda l'ingest dei PDF caricati.

> Il flag sticky `scaffoldInFlight` mantiene il wizard montato durante restart + ingest, così vedi il progresso reale via SSE prima che `setup_mode` diventi `false`.

In alternativa via CLI:

```bash
python -m llm_wiki init --domain legal --label "Wiki Legale"
python -m llm_wiki pack activate legal
# Riavvia il server
```

## 10. Login e prima query

1. Frontend ricarica con `setup_mode=false`.
2. Schermata login: email + password dell'admin appena creato.
3. Fai una domanda nella chat; vedrai stream NDJSON, risposta, citazioni `[[folder/slug]]` cliccabili nel drawer "Sources".

## 11. Verifica salute

```bash
# Stato sistema
python -m llm_wiki status

# Pre-flight checks
python -m llm_wiki doctor --strict

# Endpoint
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/api/status
```

## 12. Ingest aggiuntivo

Da CLI (one-shot):

```bash
python -m llm_wiki ingest /path/to/document.pdf
```

Da UI: bottone "Carica PDF" nella sidebar. Lo stream eventi è visibile nella modale di upload.

Da API:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"..."}' | jq -r .access_token)

curl -X POST http://127.0.0.1:8000/api/ingest/file \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/document.pdf"
```

## 13. Invitare un secondo utente

```bash
python -m llm_wiki invite --email user@example.com --role editor
```

Output: token monouso (TTL 24h, vedi `INVITATION_TTL_HOURS`). Inviare via canale out-of-band. L'utente apre `/?invite=<token>` e completa il form.

## Errori comuni nel primo avvio

| Sintomo | Causa | Soluzione |
| ------- | ----- | --------- |
| `WIKI_ROOT_<X>` non risolto | Worker uvicorn ha ereditato env vuoto pre-wizard | `_drop_stale_empty_inheritance` interviene; se persiste, esporta `unset APP_DOMAIN WIKI_ROOT` nello shell e riavvia |
| `LLM_TIMEOUT` durante ingest | Modello non in cache + `INGEST_MAX_CONCURRENT > 1` | Tieni `INGEST_MAX_CONCURRENT=1` su Ollama; aumenta `LLM_KEEP_ALIVE` a `30m` |
| `429 Too Many Requests` su login | Rate limit anti-bruteforce | Aspetta 60s; le credenziali sono corrette? |
| Wizard si smonta durante restart | `scaffoldInFlight` non sticky | Aggiorna frontend; verifica `App.tsx` non resetti lo stato |
| Citazioni vuote | `CITATION_STRICT_GROUNDING=true` + retrieval povera | Aumenta `RETRIEVAL_TOP_K` a 12; verifica che la collezione Qdrant abbia documenti |

## Prossimi passi

- **Utenti finali** → [`user-guide.md`](user-guide.md)
- **Personalizzare il Domain Pack** → [`domain-pack-spec.md`](domain-pack-spec.md) e [`scaffolding-guide.md`](scaffolding-guide.md)
- **Deploy produzione** → [`deployment.md`](deployment.md)
- **Manutenzione** → [`operations.md`](operations.md)
- **Sicurezza** → [`auth-rbac.md`](auth-rbac.md)
