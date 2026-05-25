# Documentazione `wiki-white-label`

Riferimento tecnico e operativo del motore LLM Wiki white-label (FastAPI + React 19 + Postgres).

## Indice

Documenti organizzati secondo il framework [Diátaxis](https://diataxis.fr/) (tutorial / how-to / reference / explanation).

### Tutorial — primo avvio

| Documento | Scopo |
|-----------|-------|
| [`getting-started.md`](getting-started.md) | Da `git clone` a wiki funzionante con login: installazione, wizard, primo utente, primo ingest |
| [`user-guide.md`](user-guide.md) | Guida utente finale: chat, conversazioni, memorie personali, feedback, scorciatoie |

### How-to — operatività

| Documento | Scopo |
|-----------|-------|
| [`scaffolding-guide.md`](scaffolding-guide.md) | Workflow scaffolding di un nuovo Domain Pack (CLI + UI Wizard) |
| [`deployment.md`](deployment.md) | Deploy produzione: Docker Compose, hardening, secrets, reverse proxy, TLS |
| [`operations.md`](operations.md) | Manutenzione corrente: backup, restore, upgrade, doctor, troubleshooting |
| [`security-scanning.md`](security-scanning.md) | Pipeline scanner (bandit, pip-audit, npm audit, Trivy) + SBOM CycloneDX |
| [`load-testing.md`](load-testing.md) | Profili k6 + SLO baseline + capacity planning + bottleneck mapping |
| [`gdpr.md`](gdpr.md) | DSAR Art. 15/17 endpoints + audit log immutabile + retention compliance |
| [`chaos-engineering.md`](chaos-engineering.md) | Fault injection drills (DB/Qdrant/Ollama/disk/memory) + cadenza |

### Reference — contratti formali

| Documento | Scopo |
|-----------|-------|
| [`architecture.md`](architecture.md) | Architettura: layer engine vs Domain Pack, contratti, flussi dati |
| [`domain-pack-spec.md`](domain-pack-spec.md) | Contratto del Domain Pack: `pack.yaml`, `schema.yaml`, `strategies.py` |
| [`api-reference.md`](api-reference.md) | Riferimento HTTP completo: tutti i router, auth/RBAC richiesta, esempi |
| [`configuration.md`](configuration.md) | Catalogo variabili d'ambiente con default e implicazioni |
| [`database.md`](database.md) | Schema Postgres, migrazioni Alembic, pgvector, RLS |
| [`code-snippets.md`](code-snippets.md) | Snippet pronti per file core (custom strategy, extractor, prompt override) |

### Explanation — modelli concettuali

| Documento | Scopo |
|-----------|-------|
| [`auth-rbac.md`](auth-rbac.md) | Modello di sicurezza: JWT + refresh, RBAC gerarchico, RLS, inviti, audit |
| [`observability.md`](observability.md) | Stack OpenTelemetry: metriche Prometheus, log Loki, trace Tempo, dashboard Grafana |
| [`compliance-matrix.md`](compliance-matrix.md) | Tracciabilità requisiti iniziali → implementazione |
| [`migration-from-rag-wiki.md`](migration-from-rag-wiki.md) | Mappatura cosa cambia rispetto al progetto di riferimento |

## Convenzioni

- Path partono dalla repo root.
- Snippet Python / YAML / shell incollabili senza preambolo.
- Esempi `curl` assumono server su `127.0.0.1:8000`.
- Lingua UI/strings: italiana. Identificatori codice: inglesi.
- Budget 500 LOC per file (Python e TS/TSX).

## Flusso di lettura suggerito

**Nuovo utente**: `getting-started.md` → `user-guide.md`.
**Operatore/SRE**: `getting-started.md` → `deployment.md` → `operations.md` → `observability.md`.
**Sviluppatore engine**: `architecture.md` → `domain-pack-spec.md` → `database.md` → `auth-rbac.md` → `code-snippets.md`.
**Integratore API**: `api-reference.md` → `auth-rbac.md` → `configuration.md`.
