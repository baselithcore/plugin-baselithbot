# Architettura — `wiki-white-label`

## 1. Obiettivo

Trasformare il progetto verticale `rag-wiki` (specifico per polizze assicurative italiane) in un **engine white-label** capace di istanziare una wiki RAG verticale (Legale, Medica, Tecnica, Assicurativa, …) senza modificare il core. La selezione del dominio avviene in fase di scaffolding (`python -m llm_wiki init --domain <name>`) e il runtime è **single-tenant** (`1 process = 1 APP_DOMAIN`).

## 2. Diagramma a livelli

```text
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  BrandingContext (tema)   +   DomainContext (labels via API)    │
└─────────────────────────────┬───────────────────────────────────┘
                              │  fetch /api/branding,
                              │  /api/chat, /api/groups, …
┌─────────────────────────────▼───────────────────────────────────┐
│                     FASTAPI HTTP LAYER                          │
│   main.py · CORS · lifespan(load_pack + warmup) · streaming     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                          DOMAIN LAYER                           │
│  domain/registry.py     domain/pack.py     domain/prompts.py    │
│  domain/schema.py       domain/strategies.py                    │
│       ▲                                                         │
│       │ load + cache                                            │
│       │                                                         │
│  ┌────┴───────── domains/<APP_DOMAIN>/ ──────────────────────┐  │
│  │  pack.yaml · schema.yaml · prompts/*.j2 · examples/       │  │
│  │  strategies.py (opzionale, page-type & extractor hooks)   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                     ENGINE (DOMAIN-AGNOSTIC)                    │
│   agents/rag_agent.py        ingest_raw/orchestrator.py         │
│   wiki/parser.py · groups.py vectorstore/* · graphdb/* · utils  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                INFRASTRUCTURE (LOCAL/REMOTE)                    │
│   Qdrant (hybrid: dense + sparse + ColBERT)                     │
│   Ollama / OpenAI-compat                                        │
│   FalkorDB / RedisGraph (opzionale)                             │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Contratti chiave

### 3.1 `DomainPack` (pydantic)

Definito in [`llm_wiki/domain/pack.py`](../llm_wiki/domain/pack.py). Materializza un singolo verticale.

| Campo | Tipo | Ruolo |
 | --- | --- | --- |
| `schema_version` | `int` | Bumped su breaking changes del contratto |
| `name` | `str` (regex `^[a-z_][a-z0-9_-]*$`) | Identificatore + nome cartella |
| `label` | `str` | Stringa display |
| `language` | `str` (es. `it`, `en-US`) | Lingua del verticale |
| `page_types` | `list[PageType]` | Tassonomia delle pagine: `id`, `label`, `folder`, `prompt_template` |
| `subtypes` | `dict[str, list[str]]` | Sotto-classificazione per `page_type` |
| `frontmatter_schema` | `str` | Filename relativo dello `schema.yaml` |
| `grouping` | `list[GroupingRule]` | Regole servite da `GET /api/groups/{key}` |
| `ui` | `UILabels` | Stringhe esposte al frontend via `/api/branding` |
| `prompts_dir` | `str` | Default `prompts/` |
| `examples_dir` | `str` | Default `examples/` |

### 3.2 `PromptRegistry` (Jinja2)

Definito in [`llm_wiki/domain/prompts.py`](../llm_wiki/domain/prompts.py). Sostituisce le costanti Python `SYSTEM_PROMPT` di `rag-wiki`.

```python
from llm_wiki.domain.prompts import render

# render carica il template <pack>/prompts/<name>, applica StrictUndefined
prompt = render("system.j2")
prompt = render("user.j2", context=ctx_block, question=user_question)
prompt = render("ingest/classify_system.j2")
```

Variabili sempre disponibili nei template:

- `{{ pack }}` — istanza `DomainPack` corrente.
- `{{ pack.label }}`, `{{ pack.language }}`, `{{ pack.subtypes.get("source") }}`, ecc.
- Tutte le `**vars` passate alla `render()`.

`StrictUndefined` è attivo: una variabile mancante fa fallire il render con eccezione esplicita (preferito vs. silent-empty).

### 3.3 `FrontmatterSchema`

Definito in [`llm_wiki/domain/schema.py`](../llm_wiki/domain/schema.py). Sostituisce la lista hardcoded di chiavi in `WikiPage.to_payload()` di rag-wiki.

```python
from llm_wiki.domain.schema import get_schema

schema = get_schema()
errors = schema.validate("source", page.frontmatter)  # list[str]
keys = schema.payload_keys("source")                  # campi safe-to-index
```

`schema.yaml` per pack, esempio insurance:

```yaml
fields:
  - name: edizione-iso
    type: date
    page_types: [source]
  - name: stato
    type: string
    page_types: [source]
    enum: [vigente, superata, abrogata]
```

### 3.4 `PageTypeStrategy` (Protocol)

Definito in [`llm_wiki/domain/strategies.py`](../llm_wiki/domain/strategies.py). Sostituisce la dispatch table `if subtype == "garanzia-assicurativa"` di `generator.py`.

```python
from llm_wiki.domain.strategies import GenerationContext, PageTypeStrategy

class MyStrategy:
    name = "legal.sentenza"

    def matches(self, *, page_type: str, subtype: str | None) -> bool:
        return page_type == "concept" and subtype == "sentenza"

    def generate(self, ctx: GenerationContext) -> str:
        # ...estrai sezioni dal PDF, scegli prompt, chiama LLM, ritorna markdown
        return markdown
```

Registrazione: `domains/<pack>/strategies.py` espone `page_type_strategies()` che ritorna la lista in priority order.

### 3.5 `GroupingRule`

Definito in [`llm_wiki/domain/pack.py`](../llm_wiki/domain/pack.py). Sostituisce l'endpoint hardcoded `/api/editions` di rag-wiki con un motore generico `/api/groups/{key}`.

`pack.yaml`:

```yaml
grouping:
  - key: editions
    label: "Edizioni Prodotto"
    page_type: source
    group_by: [codice-prodotto, edizione-iso]
    label_from: "{title}"
    sort_by: [edizione-iso]
    extra_fields: [modello, stato, edizione]
```

`compute_groups()` in [`llm_wiki/wiki/groups.py`](../llm_wiki/wiki/groups.py) materializza la regola scansionando il vault.

## 4. Flussi dati

### 4.1 RAG (chat)

```text

client → POST /api/chat/stream {message, history, limit}
     │
     ▼
RAGAgent.stream()
  │
  ├─ search()  ──────────────► vectorstore.core (hybrid+rerank)
  │
  ├─ render("system.j2")  ────► PromptRegistry → Jinja2 template
  ├─ render("user.j2", …)  ───►        idem
  │
  └─ generate(messages) ──────► utils.llm (Ollama/OpenAI)
                          │
                          ▼
                    NDJSON event stream → client

```

Zero stringhe dominio in `RAGAgent`. Cambiare verticale = restart con `APP_DOMAIN=<altro>`, stessa pipeline.

### 4.2 Ingest PDF

```text

client → POST /api/ingest/raw  (upload .pdf)
     │
     ▼
spawn_worker → ingest_raw_file()
  │
  ├─ extract_pdf()       (docling | marker | fallback)
  │
  ├─ classify_document() → build_classification_schema(pack) [enum dinamici]
  │   → generate_structured(Classification, …) [JSON-mode]
  │
  ├─ plan_document()     → build_plan_schema(pack) [page_type enum dinamici]
  │   → generate_structured(IngestPlan, …)
  │   → normalize_plan() [pack.page_type("source").folder]
  │
  └─ for entry in plan.derived_pages:
       │
       ├─ select_page_type_strategy(entry.page_type, entry.subtype)
       │   ├─ insurance.garanzia        (se pack=insurance + subtype match)
       │   ├─ insurance.source / entity (idem)
       │   └─ DefaultPageTypeStrategy   (fallback)
       │
       ├─ strategy.generate(ctx)  → markdown
       │
├─ensure_frontmatter()   → merge defaults + pack.frontmatter_defaults() hook
       │
       └─ refine_until_clean()    → linter + critic loop
                                  → write to disk (or .needs-review.md)

```

### 4.3 Carica branding (frontend)

```text

React boot → DomainProvider mount → fetch GET /api/branding
                                    │
                                    ▼
                        main.py: serializzazione di DomainPack.ui + page_types + grouping
                                    │
                                    ▼
                        DomainContext.tsx: setBranding(data) + document.title = data.ui.app_name

```

Frontend mantiene tema/colors/Tailwind invariati: solo testi/labels cambiano. Dual-context design: `BrandingContext` (theme) + `DomainContext` (labels) sono disaccoppiati.

## 5. Decisioni architetturali

### 5.1 Single-tenant by design

Una sola pack per processo, materializzata al boot. Motivazioni:

- Karpathy pattern: 1 vault Obsidian = 1 wiki, scelta esplicita all'init.
- Cache di embedder/reranker/Qdrant collection dimensionata su un solo verticale → no cold start di switch.
- Naming Qdrant collection: `<APP_DOMAIN>-wiki` (default) → multiple istanze su Qdrant condiviso non collidono.
- Semplicità di security: nessun cross-tenant leakage perché non c'è cross-tenant.

Multi-tenant runtime futuro: si fa con multiple istanze del processo dietro un router (Traefik/Nginx) con `Host:` → `APP_DOMAIN` mapping. Non si embeda.

### 5.2 YAML+Jinja2 vs. tutto-Python

Domain Pack è **dichiarativo** (YAML + Jinja2) per scelta:

- Non-developer (analista di dominio) può modificare `pack.yaml` + prompts senza toccare Python.
- Validazione pydantic al load → errori chiari, no silent typos.
- Diff git su pack.yaml è leggibile, non rumoroso come diff su `if/elif` Python.
- Strategy Python rimane disponibile per logica complessa (`strategies.py` è opzionale).

### 5.3 `StrictUndefined` Jinja2

Default `Undefined` permissivo è bug-prone: una variabile sbagliata produce stringhe vuote nel prompt → degradazione silenziosa della qualità RAG. `StrictUndefined` solleva eccezione → fail fast in dev, mai prompt degradati in prod.

### 5.4 Schema dinamici per ingest

`build_classification_schema(pack)` e `build_plan_schema(pack)` costruiscono `pydantic.BaseModel` con `Field(json_schema_extra={"enum": pack.subtypes["source"]})` al boot. Questo permette JSON-schema constrained decoding (Ollama `format=<schema>`, OpenAI `response_format=json_schema`) con enum specifici del verticale → l'LLM non può inventare un `source_type` sconosciuto.

### 5.5 Frontmatter schema separato dal pack core

`schema.yaml` separato da `pack.yaml` perché:

- Contratti diversi: pack = engine config, schema = data model.
- Schema può evolvere indipendentemente (aggiungere un campo non rompe page_types).
- Validazione diversa: pack = pydantic strict, schema = soft (warning/error a seconda).

### 5.6 Default Strategy come safety net

`DefaultPageTypeStrategy` rende `<page_type>_page.j2` per ogni `(page_type, subtype)` non claimed. Implicazioni:

- Pack neonati (scaffolded da `_template`) **funzionano subito** senza scrivere strategies.
- Pack maturi (es. insurance) registrano strategy specifiche e il default rimane fallback.
- Ingest pipeline non si rompe mai per un page_type non gestito → degradazione graceful.

### 5.7 No prompt giganti caricati a runtime

`SYSTEM_BASE` di rag-wiki concatenato a ogni `*_SYSTEM` constant produceva prompt di 1500+ token ripetuti. White-label usa `{% include "ingest/_base.j2" %}` di Jinja2 → un solo file `_base.j2` riusato, drastica riduzione duplicazione + cache template attiva.

## 6. Layout filesystem

```text

wiki-white-label/
├── llm_wiki/                      # ENGINE (zero stringhe dominio)
│   ├── __init__.py
│   ├── __main__.py                # python -m llm_wiki
│   ├── cli.py                     # init / status / serve / ingest / pack list
│   ├── config.py                  # APP_DOMAIN + WIKI_ROOT + COLLECTION_NAME
│   ├── agents/
│   │   ├── __init__.py
│   │   └── rag_agent.py           # render-driven, no constants
│   ├── domain/                    # ⭐ ABSTRACTION LAYER
│   │   ├── __init__.py
│   │   ├── pack.py                # DomainPack + PageType + GroupingRule + UILabels
│   │   ├── registry.py            # load_pack / get_pack / cache
│   │   ├── prompts.py             # PromptRegistry (Jinja2 StrictUndefined)
│   │   ├── schema.py              # FrontmatterSchema (validate + payload_keys)
│   │   └── strategies.py          # PageTypeStrategy + ExtractorStrategy + dispatch
│   ├── ingest_raw/                # PIPELINE
│   │   ├── extractor.py           # docling/marker/fallback
│   │   ├── examples.py            # few-shot da vault + pack.examples_path
│   │   ├── prompts.py             # façade → PromptBundle
│   │   ├── schemas.py             # pydantic + build_*_schema(pack)
│   │   ├── llm_client.py          # JSON-mode constrained
│   │   ├── planner.py             # classify + plan (pack-aware enums)
│   │   ├── generator.py           # dispatch via select_page_type_strategy()
│   │   ├── critic.py              # refine loop guidato dal linter
│   │   ├── linter.py              # gate hard pre-write
│   │   ├── orchestrator.py        # extract→plan→generate→lint→write
│   │   ├── runner.py              # background worker
│   │   └── jobs.py                # job registry + NDJSON streaming
│   ├── wiki/
│   │   ├── parser.py              # page_type da pack.page_types[*].folder
│   │   ├── groups.py              # /api/groups motore generico
│   │   └── ingest.py              # vector indexing
│   ├── vectorstore/               # Qdrant + BGE-M3 + ColBERT + reranker
│   ├── graphdb/                   # FalkorDB optional
│   └── utils/                     # cache + LLM clients
│
├── domains/                       # ⭐ DOMAIN PACKS
│   ├── template/                 # scaffold base copiato da `init`
│   │   ├── pack.yaml
│   │   ├── schema.yaml
│   │   ├── prompts/
│   │   │   ├── system.j2          # RAG agent
│   │   │   ├── user.j2
│   │   │   ├── no_hits.j2
│   │   │   └── ingest/
│   │   │       ├── *base.j2       # included da tutti i system
│   │   │       ├── classify**.j2
│   │   │       ├── plan.j2
│   │   │       ├── source_page_*.j2
│   │   │       ├── entity_page_*.j2
│   │   │       └── refine_*.j2
│   │   ├── examples/              # few-shot opzionali
│   │   └── strategies.py.example  # rinominare per attivare
│   └── insurance/                 # PORT COMPLETO MVP
│       ├── pack.yaml              # subtypes assicurative + grouping editions
│       ├── schema.yaml            # frontmatter contrattuale
│       ├── strategies.py          # InsuranceSourceStrategy + Garanzia + Entity
│       ├── prompts/               # 16 template Jinja2
│       └── examples/
│
├── frontend/                      # React 19 + Vite + Tailwind v4
│   ├── App.tsx
│   ├── main.tsx                   # <BrandingProvider><DomainProvider>
│   ├── contexts/
│   │   ├── BrandingContext.tsx    # theme/colors (preesistente)
│   │   └── DomainContext.tsx      # ⭐ labels via /api/branding
│   └── components/                # invariati
│
├── main.py                        # FastAPI app
├── pyproject.toml
├── requirements.txt
├── .env.example
├── docker-compose.yml             # qdrant
├── README.md
└── docs/                          # ⭐ questa documentazione

```

## 7. Estensione

| Voglio | Faccio |
 | --- | --- |
| Aggiungere un dominio nuovo | `python -m llm_wiki init --domain X --label "Wiki X"` |
| Cambiare il prompt di sistema | Edit `domains/<pack>/prompts/system.j2`, riavvia |
| Aggiungere una page-type | Aggiungi a `pack.yaml: page_types[]`, crea il template `<id>_page.j2` (o registra strategy) |
| Validare un campo frontmatter custom | Aggiungi a `schema.yaml: fields[]` con `enum` o `required` |
| Bias estrazione PDF dominio | Implementa `ExtractorStrategy` in `strategies.py`, esponi via `extractor_strategies()` |
| Endpoint custom | Aggiungi route in `main.py`. Per dati pack-driven, usa `load_pack()` |

## 8. Test

`tests/` copre:

- `test_domain_pack.py` — pack contract, registry, cache, fail-fast
- `test_prompt_registry.py` — Jinja2 render, strict undefined, pack-aware variables
- `test_schema_and_groups.py` — FrontmatterSchema validation, grouping rules
- `test_strategies.py` — PageTypeStrategy dispatch + DefaultPageTypeStrategy fallback
- `test_init_scaffold.py` — end-to-end CLI scaffolding + render dei 14 prompt scaffoldati

Esecuzione: `pytest tests/ -v` con `pip install -e ".[dev]"`.
