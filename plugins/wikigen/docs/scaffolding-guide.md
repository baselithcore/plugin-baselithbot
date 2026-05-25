# Guida operativa — dalla zero a una wiki Legale in 5 minuti

Workflow concreto per creare un nuovo verticale white-label. Tutti i comandi sono eseguibili dalla repo root.

## Prerequisiti

- Python ≥ 3.10
- Docker (per Qdrant) — opzionale se usi Qdrant remoto
- Ollama installato e attivo (`http://localhost:11434`) — oppure chiave OpenAI
- Frontend: Node ≥ 20, npm ≥ 10

## Step 1 — Setup ambiente (una tantum)

```bash
git clone <repo> wiki-white-label
cd wiki-white-label

python -m venv .venv
source .venv/bin/activate
pip install -e ".[hybrid,ingest]"        # core + retrieval ibrido + PDF docling
# oppure: pip install -e ".[dgx]"        # preset con tutto incluso (graph + ingest + hybrid)

docker compose up -d qdrant              # Qdrant in locale, porta 6333
```

## Step 2 — Scaffold del nuovo dominio

Comando unico:

```bash
python -m llm_wiki init \
  --domain legal \
  --label "Wiki Legale" \
  --description "Sentenze, normative, contrattualistica" \
  --language it \
  --vault-root ./vaults/legal
```

Cosa fa:

1. Copia `domains/_template/` → `domains/legal/`
2. Customizza `domains/legal/pack.yaml`:
   - `name: legal`
   - `label: "Wiki Legale"`
   - `description: "Sentenze, normative, contrattualistica"`
   - `language: it`
   - `ui.app_name: "Wiki Legale"`
   - `ui.short_name: "Legale"`
3. Crea `./vaults/legal/wiki/` e `./vaults/legal/raw/` (vault Obsidian)
4. Upserta `.env` con `APP_DOMAIN=legal` e `WIKI_ROOT=$(pwd)/vaults/legal` (preserva altri secrets)

Output atteso:

```text
╭──────────────────────── Domain 'legal' ready ────────────────────────╮
│ ✓ Scaffolded domain pack at domains/legal                            │
│ ✓ Vault directory at /abs/path/wiki-white-label/vaults/legal         │
│ ✓ Wrote .env with APP_DOMAIN=legal                                   │
│                                                                      │
│ Next steps:                                                          │
│   1. Tune domains/legal/pack.yaml (page types, grouping, UI labels). │
│   2. Customize domains/legal/prompts/* for the vertical.             │
│   3. Optional: rename strategies.py.example → strategies.py          │
│   4. Verify with wiki-wl status.                                     │
│   5. Boot the API with wiki-wl serve.                                │
╰──────────────────────────────────────────────────────────────────────╯
```

## Step 3 — Personalizzazione dominio (opzionale ma raccomandato)

### 3.1 Subtypes specifici del settore

Edita `domains/legal/pack.yaml`:

```yaml
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
    - interpretazione
  entity:
    - corte
    - autorita
    - parte
    - giurista
```

### 3.2 Schema frontmatter

Edita `domains/legal/schema.yaml`:

```yaml
fields:
  - name: title
    type: string
    required: true
  - name: type
    type: string
    required: true
    enum: [source, concept, entity, topic]

  # Campi sentenze
  - name: corte
    type: string
    page_types: [source]
    enum: [cassazione, costituzionale, ce, cgue, tar, consiglio-stato]
  - name: anno
    type: integer
    page_types: [source]
  - name: numero
    type: string
    page_types: [source]
  - name: sezione
    type: string
    page_types: [source]
  - name: rango
    type: string
    page_types: [source, concept]
    enum: [costituzionale, primario, secondario, contrattuale]
  - name: vigenza
    type: string
    page_types: [source]
    enum: [vigente, abrogata, sostituita]

extra: {}
```

### 3.3 Grouping per la UI

`pack.yaml`:

```yaml
grouping:
  - key: by-corte
    label: "Per Corte"
    page_type: source
    group_by: [corte]
    label_from: "{title}"
    sort_by: [anno]
    extra_fields: [anno, numero]

  - key: by-anno
    label: "Per anno"
    page_type: source
    group_by: [anno]
    label_from: "{anno}"
```

Endpoint disponibili:

- `GET /api/groups` → ritorna le 2 regole disponibili
- `GET /api/groups/by-corte` → materializza i gruppi per corte
- `GET /api/groups/by-anno` → idem per anno

### 3.4 Prompt RAG

Edita `domains/legal/prompts/system.j2` per il tono giuridico:

```jinja2
Sei un assistente specializzato in diritto italiano. Rispondi in italiano,
citando sempre articoli, comma, lettera quando rilevanti.

REGOLE:
- Distingui norma cogente (Costituzione, codici) da norma derogabile.
- Cita sempre la fonte come wikilink Obsidian: [[sources/<slug>]].
- Per principi giurisprudenziali, riporta verbatim i passaggi delle massime.
- Mai dare consigli legali individuali; spiega l'istituto.

PAGE TYPES disponibili nel vault {{ pack.label }}:
{% for pt in pack.page_types %}
- [[{{ pt.folder }}/...]]: {{ pt.label }}{% if pt.description %} — {{ pt.description }}{% endif %}
{% endfor %}
```

### 3.5 Prompt ingest specifici

Per la pipeline di ingest sentenze, edita `domains/legal/prompts/ingest/source_page_system.j2`:

```jinja2
{% include "ingest/_base.j2" %}

Task: genera la pagina `wiki/sources/<slug>.md` per la sentenza fornita.

Struttura OBBLIGATORIA:

---
<frontmatter YAML conforme a schema.yaml>
---

# <Tribunale> sez. <X>, <Anno> n. <Numero>

## Massima

verbatim della massima della sentenza.

## Fatti

breve sintesi dei fatti rilevanti.

## Diritto

ragionamento giuridico, con citazione di articoli applicati.

## Decisione

dispositivo letterale.

## Precedenti citati

- [[sources/...]] (anno, numero)
- norme richiamate (citazione articolo)

## Principi enunciati

- [[concepts/...]] — descrizione del principio.

```

Frontmatter OBBLIGATORIO:

```yaml

title: "<Tribunale> n. <numero>/<anno>"
type: source
subtype: sentenza
corte: <cassazione|costituzionale|...>
anno: <int>
numero: "<stringa>"
sezione: "<stringa>"
rango: <costituzionale|primario|...>
vigenza: vigente
tags: [...]
created: <YYYY-MM-DD>
sources: 1
---
```

Output: MARKDOWN completo. Niente preambolo.

### 3.6 Strategie Python (opzionale)

Per logica complessa per page-type. Rinomina `strategies.py.example` → `strategies.py`, edita:

```python
"""domains/legal/strategies.py"""

from typing import Any
from llm_wiki.domain.strategies import GenerationContext, PageTypeStrategy
from llm_wiki.ingest_raw.examples import pick_examples
from llm_wiki.ingest_raw.llm_client import generate_text
from llm_wiki.ingest_raw.prompts import source_page_bundle


class LegalSentenzaStrategy:
    """Strategy per sentenze: estrae massima/fatti/diritto dal PDF."""

    name = "legal.sentenza"

    def matches(self, *, page_type: str, subtype: str | None) -> bool:
        return page_type == "source" and subtype == "sentenza"

    def generate(self, ctx: GenerationContext) -> str:
        plan = ctx.plan
        doc = ctx.extracted

        # passa solo le prime 6000 char (massima + diritto sono tipicamente in apertura)
        outline = doc.markdown[:6000]

        examples = pick_examples(
            page_type="source",
            subtype="sentenza",
            hint_keywords=[ctx.plan_entry.title],
            max_examples=2,
        )

        bundle = source_page_bundle(
            plan=plan.model_dump(mode="json"),
            classification={"source_type": "sentenza"},
            source_path=str(doc.source_path),
            outline=outline,
            examples_blocks=[e.as_prompt_block() for e in examples],
            today_iso=(ctx.today.isoformat() if ctx.today else ""),
        )
        return generate_text(messages=bundle.as_messages(), model=ctx.model)


def page_type_strategies() -> list[PageTypeStrategy]:
    return [LegalSentenzaStrategy()]


def extractor_strategies() -> list[Any]:
    return []


def frontmatter_defaults(*, entry: Any, plan: Any) -> dict[str, Any]:
    if entry.page_type == "source" and entry.subtype == "sentenza":
        return {"vigenza": "vigente", "rango": "primario"}
    return {}
```

## Step 4 — Verifica

```bash
# Sanity check del pack
python -m llm_wiki status

# Output atteso:
# Domain: legal (Wiki Legale)
# Language: it
# Page types: source, concept, entity, topic
# Grouping rules: by-corte, by-anno
# Vault root: /abs/path/vaults/legal
# Qdrant: server → legal-wiki
# LLM vendor: ollama

python -m llm_wiki pack list

# ┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
# ┃ name      ┃ label                     ┃ page types                     ┃
# ┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
# │ _template │ Template Wiki             │ source, concept, entity, topic │
# │ insurance │ Wiki Polizze Assicurative │ source, concept, entity, topic │
# │ legal     │ Wiki Legale               │ source, concept, entity, topic │
# └───────────┴───────────────────────────┴────────────────────────────────┘
```

Verifica template render:

```bash
python -c "
from llm_wiki.domain import load_pack, render
load_pack()
print(render('system.j2')[:500])
"
```

## Step 5 — Boot

```bash
# Backend (terminal 1)
python -m llm_wiki serve --reload
# uvicorn parte su 127.0.0.1:8000

# Frontend (terminal 2)
cd frontend
npm install                           # solo prima volta
npm run dev
# vite parte su http://localhost:5173
```

Verifica HTTP:

```bash
curl -s http://127.0.0.1:8000/api/branding | jq
# {
#   "domain": "legal",
#   "label": "Wiki Legale",
#   "description": "Sentenze, normative, contrattualistica",
#   "language": "it",
#   "ui": { ... },
#   "page_types": [...],
#   "subtypes": { ... },
#   "groups": [...]
# }

curl -s http://127.0.0.1:8000/api/status | jq .domain
# {
#   "name": "legal",
#   "label": "Wiki Legale",
#   "language": "it",
#   "page_types": ["source", "concept", "entity", "topic"]
# }
```

## Step 6 — Carica fonti

Dropping in `vaults/legal/raw/`:

```bash
cp ~/Documents/sentenza-cassazione-12345-2024.pdf vaults/legal/raw/

# trigger ingest via API
curl -X POST http://127.0.0.1:8000/api/ingest/raw \
  -F "file=@vaults/legal/raw/sentenza-cassazione-12345-2024.pdf" \
  -F "overwrite=false" \
  -F "reindex=true"

# {"job_id": "abc123", "filename": "sentenza-cassazione-12345-2024.pdf", ...}

# segui il job
curl -N http://127.0.0.1:8000/api/ingest/raw/jobs/abc123/stream
# NDJSON event stream: extract → classify → plan → generate(N pagine) → done
```

Pagine generate sotto `vaults/legal/wiki/{sources,concepts,entities}/`.

## Step 7 — Chat

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Quali sono i requisiti dell'\''art. 2043 CC?", "limit": 8}'
```

UI: aprire `http://localhost:5173` — il `DomainContext` fetcha automaticamente `/api/branding` e mostra "Wiki Legale" come app name.

## Switch fra domini in dev

Multipli pack scaffoldati coesistono. Per cambiare verticale:

```bash
# Opzione A: edit .env
sed -i '' 's/^APP_DOMAIN=.*/APP_DOMAIN=insurance/' .env
sed -i '' "s|^WIKI_ROOT=.*|WIKI_ROOT=$(pwd)/vaults/insurance|" .env

# Opzione B: env inline
APP_DOMAIN=insurance WIKI_ROOT=$(pwd)/vaults/insurance python -m llm_wiki serve

# Opzione C: re-init (overwrites .env)
python -m llm_wiki init --domain insurance --vault-root ./vaults/insurance
```

Restart del backend. Frontend si re-hydrata via `/api/branding` al primo refresh.

## Troubleshooting

| Sintomo | Causa | Fix |
 | --- | --- | --- |
| `DomainPackNotFoundError: APP_DOMAIN env var is unset` | `.env` non caricato o variable mancante | `cat .env \| grep APP_DOMAIN`, source `.env` o usa `python-dotenv` |
| `pack name mismatch: APP_DOMAIN='legal' but pack.yaml declares name='_template'` | Hai modificato pack.yaml a mano sbagliando | re-init con `--force` |
| `UndefinedError: 'pack' is undefined` in render template | Stai usando `{{ foo }}` invece di `{{ pack.foo }}` | Tutti i campi pack sono sotto `pack.` |
| `qdrant collection 'legal-wiki' has different dim` | Hai cambiato `EMBEDDER_MODEL` su collection esistente | `curl -X DELETE http://localhost:6333/collections/legal-wiki` poi reindex |
| Frontend mostra "Wiki" invece del label custom | Cache browser o backend non riavviato | Hard refresh del browser; verifica `curl /api/branding` |
| Ingest fallisce con `LLM timeout on N-char prompt` | Modello locale lento + prompt lungo | Riduci `CHUNK_SIZE`, usa modello più veloce, alza `LLM_TIMEOUT` in `.env` |
