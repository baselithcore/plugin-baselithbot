# Migrazione `rag-wiki` → `wiki-white-label`

Mappatura puntuale di cosa cambia rispetto al progetto di riferimento `/Users/giovanni/dev/lavoro/rag-wiki/`.

## 1. Vista d'insieme

| Aspetto | rag-wiki | wiki-white-label |
 | --- | --- | --- |
| Dominio | Hardcoded (polizze assicurative italiane) | Selezionato a init via `APP_DOMAIN` |
| Prompt RAG | `SYSTEM_PROMPT = "..."` in `agents/rag_agent.py` (~80 righe) | `domains/<pack>/prompts/system.j2` |
| Prompt ingest | 6 `*_SYSTEM` constants in `ingest_raw/prompts.py` (522 righe) | 13 file Jinja2 sotto `domains/<pack>/prompts/ingest/` |
| Schema frontmatter | Pydantic `Literal[...]` enum hardcoded in `ingest_raw/schemas.py` | `domains/<pack>/schema.yaml` |
| Page-type dispatch | `if subtype in {"garanzia-assicurativa", ...}` in `generator.py` | `select_page_type_strategy(page_type, subtype)` |
| Grouping API | `GET /api/editions` (codice cablato in `main.py`) | `GET /api/groups/{key}` driven da `pack.grouping[]` |
| Frontend labels | Hardcoded in componenti React | `DomainContext` fetcha `/api/branding` |
| Vault path | `WIKI_ROOT` da env | `WIKI_ROOT` + `pack.root` (per esempi/strategie) |
| Qdrant collection | `COLLECTION_NAME=llm-wiki` | `COLLECTION_NAME=<APP_DOMAIN>-wiki` (default) |

## 2. Mappatura file-by-file

### 2.1 Engine (rinominato `llm_wiki/`, struttura conservata)

| rag-wiki | wiki-white-label | Modifica |
 | --- | --- | --- |
| `llm_wiki/config.py` | `llm_wiki/config.py` | + `APP_DOMAIN`, + `DOMAIN_PACK_DIR`, default `COLLECTION_NAME=<domain>-wiki` |
| `llm_wiki/cli.py` | `llm_wiki/cli.py` | Riscritto: `init/status/serve/ingest/pack list` |
| `llm_wiki/agents/rag_agent.py` | `llm_wiki/agents/rag_agent.py` | Sostituito `SYSTEM_PROMPT`/`USER_TEMPLATE` constants con `render(name, **vars)` |
| `llm_wiki/ingest_raw/prompts.py` | `llm_wiki/ingest_raw/prompts.py` | Da 522 righe → 161 righe. Funzioni ritornano `PromptBundle` rendered da Jinja2 |
| `llm_wiki/ingest_raw/schemas.py` | `llm_wiki/ingest_raw/schemas.py` | Rimosse `Literal[...]` enum hardcoded. Aggiunti `build_classification_schema(pack)` + `build_plan_schema(pack)` |
| `llm_wiki/ingest_raw/planner.py` | `llm_wiki/ingest_raw/planner.py` | `classify_document` + `plan_document` usano schema dinamici dal pack. `_normalize_plan` legge `pack.page_type("source").folder` |
| `llm_wiki/ingest_raw/generator.py` | `llm_wiki/ingest_raw/generator.py` | Da 310 → 50 righe. Tutta la logica `if/elif page_type/subtype` spostata in strategies |
| `llm_wiki/ingest_raw/orchestrator.py` | `llm_wiki/ingest_raw/orchestrator.py` | `_frontmatter_defaults` chiama `pack.frontmatter_defaults()` hook |
| `llm_wiki/ingest_raw/critic.py` | `llm_wiki/ingest_raw/critic.py` | Usa `refine_bundle()` invece di `REFINE_SYSTEM` constant |
| `llm_wiki/ingest_raw/extractor.py` | `llm_wiki/ingest_raw/extractor.py` | Invariato (PDF extraction è generico) |
| `llm_wiki/ingest_raw/linter.py` | `llm_wiki/ingest_raw/linter.py` | Portato AS-IS. Le regole insurance-specific restano default — pack future possono estendere |
| `llm_wiki/ingest_raw/runner.py` | `llm_wiki/ingest_raw/runner.py` | Invariato |
| `llm_wiki/ingest_raw/jobs.py` | `llm_wiki/ingest_raw/jobs.py` | Invariato |
| `llm_wiki/ingest_raw/examples.py` | `llm_wiki/ingest_raw/examples.py` | Carica esempi da `WIKI_DIR` + `pack.examples_path` (merge) |
| `llm_wiki/ingest_raw/llm_client.py` | `llm_wiki/ingest_raw/llm_client.py` | Invariato |
| `llm_wiki/wiki/parser.py` | `llm_wiki/wiki/parser.py` | `_infer_type` usa `pack.page_types[*].folder` con fallback legacy. `to_payload` legge `schema.payload_keys()` |
| `llm_wiki/wiki/ingest.py` | `llm_wiki/wiki/ingest.py` | Invariato |
| `llm_wiki/vectorstore/*` | `llm_wiki/vectorstore/*` | Invariati (già agnostici) |
| `llm_wiki/graphdb/*` | `llm_wiki/graphdb/*` | Invariato |
| `llm_wiki/utils/*` | `llm_wiki/utils/*` | Invariati |

### 2.2 Layer nuovo: `llm_wiki/domain/`

| File | Ruolo |
 | --- | --- |
| `domain/__init__.py` | Re-export di tutti i symbols |
| `domain/pack.py` | `DomainPack` + `PageType` + `GroupingRule` + `UILabels` + `FrontmatterField` |
| `domain/registry.py` | `load_pack()` + `get_pack()` + cache thread-safe |
| `domain/prompts.py` | `PromptRegistry` Jinja2 + `render()` |
| `domain/schema.py` | `FrontmatterSchema.validate()` + `payload_keys()` |
| `domain/strategies.py` | `PageTypeStrategy` Protocol + `select_page_type_strategy()` + `DefaultPageTypeStrategy` |

### 2.3 HTTP layer

| rag-wiki endpoint | wiki-white-label endpoint | Note |
 | --- | --- | --- |
| `GET /api/status` | `GET /api/status` | + sezione `domain` |
| — | `GET /api/branding` | NUOVO. Labels per UI |
| `GET /api/editions` | `GET /api/groups/{key}` | Generic. `key=editions` per insurance |
| — | `GET /api/groups` | NUOVO. Lista delle regole disponibili |
| `POST /api/chat` | `POST /api/chat` | Invariato |
| `POST /api/chat/stream` | `POST /api/chat/stream` | Invariato |
| `GET /api/wiki/pages` | `GET /api/wiki/pages` | Invariato |
| `GET /api/wiki/page/{id}` | `GET /api/wiki/page/{id}` | Invariato |
| `POST /api/ingest` | `POST /api/ingest` | Invariato |
| `POST /api/ingest/file` | `POST /api/ingest/file` | Invariato |
| `POST /api/ingest/raw` | `POST /api/ingest/raw` | Invariato |
| `GET /api/ingest/raw/jobs/*` | `GET /api/ingest/raw/jobs/*` | Invariati |
| `GET /api/raw/files` | `GET /api/raw/files` | Invariato |
| `POST /api/feedback` | `POST /api/feedback` | Invariato |

### 2.4 Frontend

| rag-wiki | wiki-white-label | Modifica |
 | --- | --- | --- |
| `frontend/src/contexts/BrandingContext.tsx` | `frontend/contexts/BrandingContext.tsx` | Invariato (gestisce theme/colors da `branding.json`) |
| — | `frontend/contexts/DomainContext.tsx` | NUOVO. Fetcha `/api/branding` per labels/page_types/groups |
| `frontend/src/main.tsx` | `frontend/main.tsx` | Wrap aggiunto: `<DomainProvider>` dentro `<BrandingProvider>` |
| Resto | Resto | Invariato (componenti, hooks, lib) |

### 2.5 Domain Pack: `domains/insurance/`

Port completo del progetto rag-wiki come **un singolo pack**:

| Origine rag-wiki | Destinazione insurance pack |
 | --- | --- |
| `agents/rag_agent.py:SYSTEM_PROMPT` | `domains/insurance/prompts/system.j2` |
| `agents/rag_agent.py:USER_TEMPLATE` | `domains/insurance/prompts/user.j2` |
| `agents/rag_agent.py` no-hits message | `domains/insurance/prompts/no_hits.j2` |
| `ingest_raw/prompts.py:SYSTEM_BASE` | `domains/insurance/prompts/ingest/_base.j2` |
| `ingest_raw/prompts.py:CLASSIFY_SYSTEM` | `domains/insurance/prompts/ingest/classify_system.j2` |
| `ingest_raw/prompts.py:classify_user_prompt()` | `domains/insurance/prompts/ingest/classify_user.j2` |
| `ingest_raw/prompts.py:PLAN_SYSTEM` | `domains/insurance/prompts/ingest/plan_system.j2` |
| `ingest_raw/prompts.py:plan_user_prompt()` | `domains/insurance/prompts/ingest/plan_user.j2` |
| `ingest_raw/prompts.py:SOURCE_PAGE_SYSTEM` | `domains/insurance/prompts/ingest/source_page_system.j2` |
| `ingest_raw/prompts.py:source_page_user_prompt()` | `domains/insurance/prompts/ingest/source_page_user.j2` |
| `ingest_raw/prompts.py:GARANZIA_PAGE_SYSTEM` | `domains/insurance/prompts/ingest/garanzia_page_system.j2` |
| `ingest_raw/prompts.py:garanzia_page_user_prompt()` | `domains/insurance/prompts/ingest/garanzia_page_user.j2` |
| `ingest_raw/prompts.py:ENTITY_PAGE_SYSTEM` | `domains/insurance/prompts/ingest/entity_page_system.j2` |
| `ingest_raw/prompts.py:entity_page_user_prompt()` | `domains/insurance/prompts/ingest/entity_page_user.j2` |
| `ingest_raw/prompts.py:REFINE_SYSTEM` | `domains/insurance/prompts/ingest/refine_system.j2` |
| `ingest_raw/prompts.py:refine_user_prompt()` | `domains/insurance/prompts/ingest/refine_user.j2` |
| `ingest_raw/schemas.py:SourceFrontmatter`/`ConceptFrontmatter`/`EntityFrontmatter` | `domains/insurance/schema.yaml` |
| `ingest_raw/schemas.py:PageSubtype`/`SourceType`/`Rango`/`StatoFonte` | `domains/insurance/pack.yaml: subtypes` |
| `ingest_raw/generator.py:_generate_source_page()` | `domains/insurance/strategies.py:InsuranceSourceStrategy` |
| `ingest_raw/generator.py:_generate_garanzia_page()` | `domains/insurance/strategies.py:InsuranceGaranziaStrategy` |
| `ingest_raw/generator.py:_generate_entity_page()` | `domains/insurance/strategies.py:InsuranceEntityStrategy` |
| `ingest_raw/orchestrator.py:_frontmatter_defaults()` (insurance branch) | `domains/insurance/strategies.py:frontmatter_defaults()` |
| `main.py:/api/editions` (logica codice-prodotto + edizione-iso) | `domains/insurance/pack.yaml: grouping[editions]` |

## 3. Compatibilità con il vault esistente

Un vault esistente di rag-wiki è caricabile **as-is** sotto white-label con `APP_DOMAIN=insurance`:

- Frontmatter delle pagine `wiki/sources/`, `wiki/concepts/`, `wiki/entities/` → consumato da `parser.py` invariatamente
- `index.md` + `log.md` → leggibili (non scritti dall'engine, gestiti dall'agente LLM-Wiki dialogante)
- `raw/` → percorso riconosciuto dal `RAW_DIR` config

Migrazione zero-downtime:

```bash
git clone wiki-white-label
cp -r /path/old/rag-wiki/wiki ./vaults/insurance/wiki
cp -r /path/old/rag-wiki/raw  ./vaults/insurance/raw
# .env:
echo "APP_DOMAIN=insurance" > .env
echo "WIKI_ROOT=$(pwd)/vaults/insurance" >> .env
docker compose up -d qdrant
python -m llm_wiki serve
```

L'unico re-indexing richiesto è la prima `POST /api/ingest` per popolare la nuova collection Qdrant `insurance-wiki`. Le pagine `.md` non si toccano.

## 4. Breaking change

| Cosa | Impatto |
 | --- | --- |
| Pacchetto Python rinominato `llm_wiki` (preservato come reference). Import paths invariati. | Nessuno — stessi import |
| Nome script CLI `llm-wiki` → `wiki-wl` (entry-point in `pyproject.toml`) | Aggiornare alias / cron jobs / CI |
| `COLLECTION_NAME` default `llm-wiki` → `<APP_DOMAIN>-wiki` | Re-indexing prima volta. Override esplicito via env preserva comportamento |
| `/api/editions` → `/api/groups/editions` | Update fetch nel frontend (insurance UI) |
| `WikiPage.to_payload()` accetta arg opzionale `schema` | Esistenti chiamate `page.to_payload()` continuano a funzionare (default schema da `get_schema()`) |
| `ingest_raw/prompts.py` non espone più `*_SYSTEM` constants | Nessuno — codice esterno usa i `bundle()` factory |

## 5. Decommissioning rag-wiki

Strategy raccomandata:

1. **Fase 1 (oggi)**: deploy `wiki-white-label` con `APP_DOMAIN=insurance` accanto a rag-wiki, stesso vault montato. Validare parità funzionale (regression suite + spot check chat).
2. **Fase 2 (+1 sprint)**: spegnere rag-wiki, mantenere il repo come reference per audit.
3. **Fase 3 (+2 sprint)**: aggiungere il primo dominio nuovo (Legale o Medica) come prova del concetto white-label.

Rollback fase 1: stop white-label, restart rag-wiki. Il vault è condiviso, nessuna perdita dati.
