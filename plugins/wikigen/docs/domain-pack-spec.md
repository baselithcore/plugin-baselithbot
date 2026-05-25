# Domain Pack — Specifica formale

Un Domain Pack è una directory autonoma sotto `domains/<name>/` che dichiara tutto ciò che varia tra wiki verticali: prompt, tassonomia delle pagine, schema frontmatter, esempi few-shot, label UI e (opzionale) strategie di generazione.

## 1. Layout obbligatorio

```text
domains/<name>/
├── pack.yaml              # OBBLIGATORIO — descriptor principale
├── schema.yaml            # OBBLIGATORIO — frontmatter rules
├── prompts/               # OBBLIGATORIO
│   ├── system.j2          #   RAG agent system prompt
│   ├── user.j2            #   RAG user template (vars: context, question)
│   ├── no_hits.j2         #   fallback retrieval vuoto
│   └── ingest/            #   pipeline ingest
│       ├── _base.j2       #     incluso da tutti i system_*
│       ├── classify_system.j2  + classify_user.j2
│       ├── plan_system.j2      + plan_user.j2
│       ├── source_page_system.j2 + source_page_user.j2
│       ├── entity_page_system.j2 + entity_page_user.j2
│       └── refine_system.j2    + refine_user.j2
├── examples/              # OPZIONALE — pagine wiki di riferimento (few-shot)
├── strategies.py          # OPZIONALE — page-type & extractor hooks
└── __init__.py            # vuoto, abilita import Python
```

## 2. `pack.yaml` — schema completo

```yaml
schema_version: 1                # OBBLIGATORIO. Bumped su breaking changes

# Identificatore + nome cartella. Regex ^[a-z_][a-z0-9_-]*$
# (l'underscore iniziale è riservato per scaffold engine, es. _template).
name: legal

# Stringa display per UI e log.
label: "Wiki Legale"

# One-liner di scopo. Mostrato in /api/branding e prompt scaffold.
description: "Knowledge base sentenze, normative, contrattualistica."

# ISO 639-1 (`it`, `en`, `de`, …) o BCP-47 (`en-US`, `it-IT`).
language: it

# Tassonomia delle pagine. id snake_case ASCII — viaggia in frontmatter,
# JSON-Schema enum LLM, path filesystem. Ordine = priority planner.
page_types:
  - id: source                  # id obbligatorio, regex ^[a-z][a-z0-9_]*$
    label: "Fonte"              # display
    plural: "fonti"             # opzionale, default: id+'s'
    folder: sources             # cartella sotto wiki/. Default = plural o id
    prompt_template: source_page.j2  # opzionale, fallback default strategy
    description: "Documento primario del corpus"  # opzionale

  - id: concept
    label: "Concetto"
    plural: "concetti"
    folder: concepts
    prompt_template: entity_page.j2

  - id: entity
    label: "Entità"
    plural: "entità"
    folder: entities
    prompt_template: entity_page.j2

  - id: topic
    label: "Tema"
    plural: "temi"
    folder: topics
    prompt_template: entity_page.j2

# Sotto-classificazione per page_type. Free-form, scoped per pack.
# Iniettato come enum nel JSON-Schema del planner LLM.
subtypes:
  source:
    - sentenza
    - normativa
    - regolamento
    - dottrina
  concept:
    - principio
    - clausola
    - istituto
  entity:
    - corte
    - autorita
    - parte

# Filename schema.yaml relativo al pack root.
frontmatter_schema: schema.yaml

# Regole di grouping servite da GET /api/groups/{key}.
# Sostituisce endpoint hardcoded come /api/editions di rag-wiki.
grouping:
  - key: by-corte                # path slug — ^[a-z][a-z0-9_]*$
    label: "Corti"               # display
    page_type: source            # quale page_type scansionare
    group_by: [corte]            # composite key (lista di campi frontmatter)
    label_from: "{title}"        # template, supporta {title} e {<frontmatter_key>}
    sort_by: [corte]             # opzionale
    extra_fields: [anno, sezione] # campi raccolti come metadata gruppo

# Branding strings per il frontend (servite da /api/branding).
# Frontend mantiene tema/colors invariati: solo testo cambia.
ui:
  app_name: "Wiki Legale"
  short_name: "Legale"
  vault_label: "Vault giuridico"
  tagline: "Sentenze, normative, contrattualistica."
  empty_state: "Carica una sentenza per iniziare."
  page_type_labels:               # override delle label di page_types[*]
    source: "Sentenze e atti"
    concept: "Principi e istituti"
    entity: "Corti, autorità, parti"
    topic: "Aree del diritto"
  extra:                          # free-form per badge custom UI
    badges:
      stato: ["vigente", "abrogata"]

# Default 'prompts'.
prompts_dir: prompts
# Default 'examples'.
examples_dir: examples
# Opzionale — directory di hint/regex per ExtractorStrategy.
# extractors_dir: extractors
```

## 3. `schema.yaml` — frontmatter rules

```yaml
fields:
  # campi universali (no `page_types` → applicano a tutti)
  - name: title
    type: string
    required: true
  - name: type
    type: string
    required: true
    enum: [source, concept, entity, topic]   # match con pack.page_types[*].id
  - name: tags
    type: array
  - name: aliases
    type: array

  # campi specifici di un page_type
  - name: corte
    type: string
    page_types: [source]
    enum: [cassazione, costituzionale, ce, cgue, tar, consiglio-stato]
  - name: anno
    type: integer
    page_types: [source]
  - name: sezione
    type: string
    page_types: [source]

  - name: rango
    type: string
    page_types: [source, concept]
    enum: [costituzionale, primario, secondario, contrattuale]

# Future: JSON Schema raw merged at validation time
extra: {}
```

Tipi supportati da `_matches_type()`: `string`, `integer`, `number`, `boolean`, `array`, `object`, `date` (accetta `YYYY-MM-DD` string o `datetime.date`).

## 4. Template Jinja2

Contesto sempre disponibile:

- `{{ pack }}` — istanza `DomainPack` corrente
- `{{ pack.label }}`, `{{ pack.language }}`, `{{ pack.description }}`
- `{{ pack.page_types }}` — `list[PageType]`, iterabile (`{% for pt in pack.page_types %}`)
- `{{ pack.subtypes }}` — `dict[str, list[str]]`. Accesso safe: `{{ pack.subtypes.get("source") }}`
- `{{ pack.page_type("source") }}` — helper, ritorna `PageType | None`
- Tutte le `**vars` passate alla `render()`

Esempio `system.j2`:

```jinja2
Sei l'assistente conversazionale di {{ pack.label }} ({{ pack.description }}).

Rispondi sempre in lingua {{ pack.language }}. Cita sempre le fonti come wikilink Obsidian.

Page types disponibili: {{ pack.page_types | map(attribute="label") | join(", ") }}.
```

`StrictUndefined` attivo: variabile inesistente solleva `UndefinedError` → fail fast in dev.

## 5. `strategies.py` — opzionale

Hook Python per logiche complesse non esprimibili in Jinja2. Espone tre factory opzionali:

```python
"""domains/<name>/strategies.py"""

from typing import Any
from llm_wiki.domain.strategies import GenerationContext, PageTypeStrategy


class LegalSentenzaStrategy:
    """Esempio: strategia dedicata per sentenze."""

    name = "legal.sentenza"

    def matches(self, *, page_type: str, subtype: str | None) -> bool:
        return page_type == "source" and subtype == "sentenza"

    def generate(self, ctx: GenerationContext) -> str:
        # ctx.plan_entry, ctx.plan, ctx.extracted, ctx.today, ctx.model
        from llm_wiki.ingest_raw.llm_client import generate_text
        from llm_wiki.ingest_raw.prompts import source_page_bundle

        bundle = source_page_bundle(
            plan=ctx.plan.model_dump(mode="json"),
            classification={"source_type": "sentenza"},
            source_path=str(ctx.extracted.source_path),
            outline=ctx.extracted.markdown[:8000],
            examples_blocks=[],
            today_iso=(ctx.today.isoformat() if ctx.today else ""),
        )
        return generate_text(messages=bundle.as_messages(), model=ctx.model)


def page_type_strategies() -> list[PageTypeStrategy]:
    """Strategie in priority order. Prima `matches()` truthy vince."""
    return [
        LegalSentenzaStrategy(),
        # …
    ]


def extractor_strategies() -> list[Any]:
    """ExtractorStrategy per bias backend / post-process PDF."""
    return []


def frontmatter_defaults(*, entry: Any, plan: Any) -> dict[str, Any]:
    """Default pack-specific iniettati dall'orchestrator nel frontmatter.

    Viene mergeato sopra ai default base (title, type, created, updated, tags).
    Restituisci solo i campi specifici del dominio.
    """
    if entry.page_type == "source" and entry.subtype == "sentenza":
        return {"rango": "primario", "anno": None, "corte": None}
    return {}
```

Discovery: il modulo viene importato come `domains.<pack_name>.strategies` da `llm_wiki.domain.strategies.get_strategies()`. Cache process-wide. Errori di import = log warning + fallback a `DefaultPageTypeStrategy`.

## 6. Lifecycle del pack

### 6.1 Loading

```text
process boot
  │
  ▼
load_pack()
  │
  ├─ legge APP_DOMAIN da env (o arg esplicito per test)
  ├─ risolve path: DOMAIN_PACK_DIR (se set) | <repo>/domains/<APP_DOMAIN>
  ├─ parse pack.yaml → DomainPack(**data) (pydantic)
  ├─ verifica schema_version
  ├─ verifica name == APP_DOMAIN (sanity)
  ├─ pack.root = <pack_dir>.resolve()
  └─ cache _cached = pack
```

Errori:

- `DomainPackNotFoundError`: `APP_DOMAIN` unset o cartella non trovata
- `DomainPackInvalidError`: YAML non valido, schema_version sbagliato, `name` mismatch

### 6.2 Validazione contratto

`pydantic.ValidationError` viene wrappato in `DomainPackInvalidError` con il messaggio originale. Esempi di violazioni:

```text
domains/legal/pack.yaml: 1 validation error for DomainPack
  page_types.0.id
    String should match pattern '^[a-z][a-z0-9_]*$' [input='Source']
```

```text
unsupported pack schema_version 2; engine expects 1
```

### 6.3 Cache invalidation

Single-tenant: pack è frozen per la process lifetime. Test invalidano via `reset_pack_cache()`. In produzione: restart del processo per swap.

## 7. Validazione tooling

```bash
# Verifica che un pack carichi correttamente
APP_DOMAIN=legal python -c "
from llm_wiki.domain import load_pack
pack = load_pack()
print(f'OK {pack.name}: {pack.label}')
print(f'page_types: {[pt.id for pt in pack.page_types]}')
print(f'grouping: {[r.key for r in pack.grouping]}')
"

# Verifica che tutti i prompt renderino
APP_DOMAIN=legal python -c "
from llm_wiki.domain import load_pack
from llm_wiki.domain.prompts import render
load_pack()
for name in ['system.j2', 'user.j2', 'no_hits.j2']:
    out = render(name, context='ctx', question='q')
    assert len(out) > 0, name
    print(f'OK {name}: {len(out)} chars')
"

# Lista pack visti dall'engine
python -m llm_wiki pack list
```

## 8. Anti-pattern da evitare

| ❌ Anti-pattern | ✅ Approccio corretto |
 | --- | --- |
| Hardcodare stringhe in template Jinja2 | Usare `{{ pack.label }}`, `{{ pack.language }}`, `{{ pack.subtypes.get("source") }}` |
| Importare `domains.<pack>.*` dal core | Usare solo `llm_wiki.domain.*` astrazioni; pack si auto-registra via factory |
| Mutare `pack.frontmatter` o `pack.ui` a runtime | Pack è immutabile dopo `load_pack()`. Cambiamenti → modifica YAML + restart |
| Mettere API key / segreti in `pack.yaml` | Segreti SOLO in `.env`. `pack.yaml` è committed in git |
| Usare path assoluti nel pack | Tutto relativo a `pack.root` (auto-set dal registry) |
| Catch eccezioni di `load_pack()` per "fallback grazioso" | Fail fast: una pack rotta deve crashare il boot, non degradare a wiki vuota |
| Skip `schema_version` perché "non si rompe niente" | Sempre dichiarato. Quando l'engine fa breaking change, il versioning è l'unico modo di gate i pack vecchi |
