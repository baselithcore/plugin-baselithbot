# Code snippets — pronti per i file core

Snippet incollabili direttamente nei file del Domain Pack o nel core. Tutti testati contro il pack `_template` e `insurance`.

## 1. Pack: nuovo verticale "Medical"

### `domains/medical/pack.yaml`

```yaml
schema_version: 1

name: medical
label: "Wiki Medica"
description: "Linee guida cliniche, referti, letteratura biomedica."
language: it

page_types:
  - id: source
    label: "Fonte"
    plural: "fonti"
    folder: sources
    prompt_template: source_page.j2
  - id: concept
    label: "Concetto / Patologia"
    plural: "concetti"
    folder: concepts
    prompt_template: entity_page.j2
  - id: entity
    label: "Entità"
    plural: "entità"
    folder: entities
    prompt_template: entity_page.j2
  - id: topic
    label: "Tema clinico"
    plural: "temi"
    folder: topics
    prompt_template: entity_page.j2

subtypes:
  source:
    - linea-guida
    - referto
    - paper
    - rct
    - meta-analisi
    - case-report
  concept:
    - patologia
    - sintomo
    - farmaco
    - procedura
    - test-diagnostico
  entity:
    - paziente
    - clinico
    - struttura
    - autorita-regolatoria

frontmatter_schema: schema.yaml

grouping:
  - key: by-patologia
    label: "Per patologia"
    page_type: concept
    group_by: [patologia]
    label_from: "{title}"
    sort_by: [patologia]
    extra_fields: [icd-10, severita]

  - key: by-evidenza
    label: "Per livello di evidenza"
    page_type: source
    group_by: [livello-evidenza]
    label_from: "{title}"
    sort_by: [data]
    extra_fields: [data, autori]

ui:
  app_name: "Wiki Medica"
  short_name: "Medica"
  vault_label: "Vault clinico"
  tagline: "Knowledge base evidence-based per pratica clinica."
  empty_state: "Carica una linea guida o un referto per iniziare."
  page_type_labels:
    source: "Linee guida e fonti"
    concept: "Patologie, farmaci, procedure"
    entity: "Pazienti, clinici, strutture"
    topic: "Aree cliniche"
  extra:
    badges:
      livello-evidenza: ["1a", "1b", "2a", "2b", "3", "4", "5"]

prompts_dir: prompts
examples_dir: examples
```

### `domains/medical/schema.yaml`

```yaml
fields:
  - name: title
    type: string
    required: true
  - name: type
    type: string
    required: true
    enum: [source, concept, entity, topic]
  - name: tags
    type: array
  - name: aliases
    type: array

  # Source-specific
  - name: source_type
    type: string
    page_types: [source]
    enum: [linea-guida, referto, paper, rct, meta-analisi, case-report]
  - name: autori
    type: array
    page_types: [source]
  - name: data
    type: date
    page_types: [source]
  - name: doi
    type: string
    page_types: [source]
  - name: livello-evidenza
    type: string
    page_types: [source]
    enum: ["1a", "1b", "2a", "2b", "3", "4", "5"]
  - name: linee-guida
    type: array
    page_types: [source, concept]

  # Concept-specific
  - name: subtype
    type: string
    page_types: [concept]
    enum: [patologia, sintomo, farmaco, procedura, test-diagnostico]
  - name: icd-10
    type: string
    page_types: [concept]
  - name: atc
    type: string
    page_types: [concept]
    description: "Codice ATC per farmaci"
  - name: severita
    type: string
    page_types: [concept]
    enum: [lieve, moderata, severa, critica]

extra: {}
```

### `domains/medical/strategies.py`

```python
"""Medical vertical: 2 page-type strategies + frontmatter defaults."""

from typing import Any
from datetime import date

from llm_wiki.domain.strategies import GenerationContext, PageTypeStrategy
from llm_wiki.ingest_raw.examples import pick_examples
from llm_wiki.ingest_raw.llm_client import generate_text
from llm_wiki.ingest_raw.prompts import (
    entity_page_bundle,
    source_page_bundle,
)


class MedicalLineaGuidaStrategy:
    """Linee guida cliniche — outline più aggressivo (12k char) per coprire metodologia."""

    name = "medical.linea-guida"

    def matches(self, *, page_type: str, subtype: str | None) -> bool:
        return page_type == "source" and subtype == "linea-guida"

    def generate(self, ctx: GenerationContext) -> str:
        examples = pick_examples(
            page_type="source",
            subtype="linea-guida",
            hint_keywords=[ctx.plan_entry.title],
            max_examples=2,
        )
        bundle = source_page_bundle(
            plan=ctx.plan.model_dump(mode="json"),
            classification={"source_type": "linea-guida"},
            source_path=str(ctx.extracted.source_path),
            outline=ctx.extracted.markdown[:12000],
            examples_blocks=[e.as_prompt_block() for e in examples],
            today_iso=(ctx.today or date.today()).isoformat(),
        )
        return generate_text(messages=bundle.as_messages(), model=ctx.model)


class MedicalPatologiaStrategy:
    """Concept patologia — usa entity_page bundle (template generico)."""

    name = "medical.patologia"

    def matches(self, *, page_type: str, subtype: str | None) -> bool:
        return page_type == "concept" and subtype == "patologia"

    def generate(self, ctx: GenerationContext) -> str:
        snippet = ctx.extracted.markdown[:3000]  # primi 3k
        bundle = entity_page_bundle(
            plan_entry=ctx.plan_entry.model_dump(mode="json"),
            source_path=ctx.plan.source_page.target_path,
            context_snippet=snippet,
            today_iso=(ctx.today or date.today()).isoformat(),
        )
        return generate_text(messages=bundle.as_messages(), model=ctx.model)


def page_type_strategies() -> list[PageTypeStrategy]:
    return [
        MedicalLineaGuidaStrategy(),
        MedicalPatologiaStrategy(),
    ]


def extractor_strategies() -> list[Any]:
    return []


def frontmatter_defaults(*, entry: Any, plan: Any) -> dict[str, Any]:
    """Default specifici medical."""
    if entry.page_type == "source" and entry.subtype == "linea-guida":
        return {"livello-evidenza": "1a", "autori": []}
    if entry.page_type == "concept" and entry.subtype == "patologia":
        return {"icd-10": None, "severita": None}
    return {}
```

## 2. ExtractorStrategy custom

Esempio: pack legale che riconosce sentenze dal layout (header "REPUBBLICA ITALIANA" + numero sezione).

### `domains/legal/strategies.py` — extractor block

```python
"""Aggiungi a domains/legal/strategies.py la logica di extraction custom."""

import re
from pathlib import Path
from typing import Any


class LegalSentenzaExtractor:
    """Riconosce sentenze italiane dal preambolo + applica TableFormer aggressivo."""

    name = "legal.sentenza-extractor"

    _MARKER_RE = re.compile(
        r"REPUBBLICA\s+ITALIANA|IN\s+NOME\s+DEL\s+POPOLO\s+ITALIANO",
        re.IGNORECASE,
    )

    def claim(self, source_path: Path, hints: dict[str, Any]) -> bool:
        """Prima di leggere, decide se questa strategy gestisce il PDF."""
        # heuristic 1: filename
        if "sentenza" in source_path.stem.lower():
            return True
        # heuristic 2: hints già rilevati
        if hints.get("source_type") == "sentenza":
            return True
        return False

    def post_process(self, doc: Any) -> Any:
        """Manipola un ExtractedDocument dopo l'estrazione generica."""
        # esempio: estrai il numero della sentenza dal testo
        m = re.search(r"sentenza\s+n\.\s*(\d+)/(\d{4})", doc.markdown[:3000], re.IGNORECASE)
        if m:
            doc.metadata["numero"] = m.group(1)
            doc.metadata["anno"] = int(m.group(2))
        return doc


def extractor_strategies() -> list[Any]:
    return [LegalSentenzaExtractor()]
```

> **Nota**: il dispatcher `ExtractorStrategy` è esposto come Protocol; il punto d'integrazione live nel `extractor.py` dell'engine. Per un'integrazione end-to-end usa `_extract_metadata()` come hook custom o aggiungi un wrapper in `orchestrator.ingest_raw_file()`.

## 3. Frontend: usare `DomainContext` in un componente

### `frontend/components/Sidebar.tsx` — esempio di consumo

```tsx
import { useDomain } from '../contexts/DomainContext';

export function Sidebar() {
  const { branding, loading, pageTypeLabel } = useDomain();

  if (loading) return <div>Loading…</div>;
  if (!branding) return null;

  return (
    <aside className="bg-sidebar text-sidebar-text">
      <h1>{branding.ui.app_name}</h1>
      <p className="text-sm opacity-70">{branding.ui.tagline}</p>

      <nav>
        {branding.page_types.map((pt) => (
          <a key={pt.id} href={`/page-type/${pt.id}`}>
            {pageTypeLabel(pt.id)}
          </a>
        ))}
      </nav>

      <h2>{branding.groups.length > 0 ? 'Gruppi' : null}</h2>
      <nav>
        {branding.groups.map((g) => (
          <a key={g.key} href={`/groups/${g.key}`}>
            {g.label}
          </a>
        ))}
      </nav>
    </aside>
  );
}
```

### `frontend/components/EditionSelector.tsx` — sostituire `/api/editions` con `/api/groups/editions`

```tsx
import { useEffect, useState } from 'react';
import { useDomain } from '../contexts/DomainContext';

interface Group {
  id: string;
  label: string;
  key: Record<string, string>;
  members: Array<{ document_id: string; title: string; subtype: string | null }>;
  extras: Record<string, string | null>;
}

export function EditionSelector() {
  const { branding } = useDomain();
  const [groups, setGroups] = useState<Group[]>([]);

  useEffect(() => {
    if (!branding) return;
    // pick the first grouping rule, or look up by key
    const ruleKey = branding.groups.find((g) => g.key === 'editions')?.key
      ?? branding.groups[0]?.key;
    if (!ruleKey) return;

    fetch(`/api/groups/${ruleKey}`)
      .then((r) => r.json())
      .then((data) => setGroups(data.groups));
  }, [branding]);

  return (
    <select>
      {groups.map((g) => (
        <option key={g.id} value={g.id}>
          {g.label}
        </option>
      ))}
    </select>
  );
}
```

## 4. Custom prompt override per `(page_type, subtype)`

Scenario: vuoi un prompt completamente diverso per sentenze costituzionali rispetto a sentenze ordinarie.

### `domains/legal/prompts/ingest/source_page_costituzionale.j2`

```jinja2
{% include "ingest/_base.j2" %}

Task: genera la pagina per una sentenza della Corte Costituzionale.

Struttura speciale per sentenze costituzionali:
- ## Quaestio: la questione di legittimità costituzionale sollevata
- ## Norme parametro: articoli costituzionali invocati
- ## Norme oggetto: leggi/decreti il cui giudizio è richiesto
- ## Decisione: dispositivo (manifestamente infondata / accolta / rigettata)
- ## Effetti: declaratoria di illegittimità (erga omnes) o interpretativa
- ## Principi enunciati: massime sintetiche

Regole specifiche:
- Cita ogni articolo della Costituzione che la sentenza richiama (es. "art. 3 Cost.").
- Se la sentenza è interpretativa di rigetto, usa callout `> [!important]`.
- Output completamente in italiano.
```

### `domains/legal/strategies.py`

```python
class LegalCostituzionaleStrategy:
    name = "legal.costituzionale"

    def matches(self, *, page_type: str, subtype: str | None) -> bool:
        # Match sentenze costituzionali tramite frontmatter "corte"
        # in plan_entry.notes (passed by planner via JSON-schema enum hint)
        return page_type == "source" and subtype == "sentenza"

    def generate(self, ctx: GenerationContext) -> str:
        # filtro extra: il pack pianifica `corte` come extra dato planner
        from llm_wiki.domain.prompts import render
        from llm_wiki.ingest_raw.llm_client import generate_text

        # template specifico
        system = render("ingest/source_page_costituzionale.j2")
        user = render(
            "ingest/source_page_user.j2",
            plan=ctx.plan.model_dump(mode="json"),
            classification={"source_type": "sentenza"},
            source_path=str(ctx.extracted.source_path),
            outline=ctx.extracted.markdown[:8000],
            examples_block="(none)",
            today_iso=(ctx.today.isoformat() if ctx.today else ""),
        )
        return generate_text(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            model=ctx.model,
        )
```

## 5. Test smoke per il proprio pack

### `tests/test_legal_pack.py`

```python
"""Smoke test per il pack legale custom."""

from collections.abc import Iterator

import pytest

from llm_wiki.domain.registry import load_pack, reset_pack_cache
from llm_wiki.domain.prompts import render, reset_registry_cache
from llm_wiki.domain.schema import get_schema, reset_schema_cache
from llm_wiki.domain.strategies import (
    reset_strategies_cache,
    select_page_type_strategy,
)


@pytest.fixture(autouse=True)
def _isolate() -> Iterator[None]:
    reset_pack_cache()
    reset_registry_cache()
    reset_schema_cache()
    reset_strategies_cache()
    yield
    reset_pack_cache()
    reset_registry_cache()
    reset_schema_cache()
    reset_strategies_cache()


def test_legal_pack_loads() -> None:
    pack = load_pack("legal", force=True)
    assert pack.label == "Wiki Legale"
    assert pack.has_page_type("source")
    keys = [r.key for r in pack.grouping]
    assert "by-corte" in keys


def test_legal_renders_all_prompts() -> None:
    load_pack("legal", force=True)
    for name in ("system.j2", "user.j2", "no_hits.j2"):
        out = render(name, context="ctx", question="q")
        assert "Wiki Legale" in out or len(out) > 50


def test_legal_validates_sentenza_frontmatter() -> None:
    load_pack("legal", force=True)
    schema = get_schema()
    errors = schema.validate(
        "source",
        {
            "title": "Cass. Sez. Un. 12345/2024",
            "type": "source",
            "subtype": "sentenza",
            "corte": "cassazione",
            "anno": 2024,
            "rango": "primario",
        },
    )
    assert errors == []


def test_legal_dispatches_sentenza_strategy() -> None:
    load_pack("legal", force=True)
    strat = select_page_type_strategy(page_type="source", subtype="sentenza")
    assert strat.name == "legal.sentenza"
```

## 6. Aggiungere un endpoint custom

Esempio: endpoint dominio-specifico che ritorna lo "stato del vault legale" filtrando per anno corrente.

### `main.py`

```python
from datetime import date
from llm_wiki.domain.registry import load_pack
from llm_wiki.wiki.parser import parse_file, walk_wiki

@app.get("/api/legal/recent-sentences")
def recent_sentences(year: int | None = None) -> dict[str, Any]:
    """Endpoint custom — disponibile solo se APP_DOMAIN=legal.

    Best practice: gating esplicito sulla pack name. Mantiene il core
    agnostico anche quando aggiungi feature dominio.
    """
    pack = load_pack()
    if pack.name != "legal":
        raise HTTPException(status_code=404, detail="endpoint not available for this domain")

    target_year = year or date.today().year
    files = walk_wiki(config.WIKI_DIR)
    out: list[dict[str, Any]] = []
    for f in files:
        page = parse_file(f, config.WIKI_ROOT)
        if not page or page.page_type != "source":
            continue
        if page.frontmatter.get("subtype") != "sentenza":
            continue
        if page.frontmatter.get("anno") != target_year:
            continue
        out.append(
            {
                "document_id": page.document_id,
                "title": page.title,
                "corte": page.frontmatter.get("corte"),
                "numero": page.frontmatter.get("numero"),
            }
        )
    return {"count": len(out), "year": target_year, "sentences": out}
```

> **Trade-off**: questo è dominio-specifico nel core. Per mantenere il core 100% agnostico, mettilo dietro un mount Pack:
>
> ```python
> # in domains/legal/api.py — opzionale future-feature
> from fastapi import APIRouter
> router = APIRouter()
> @router.get("/api/legal/recent-sentences") ...
> ```
>
> e in `main.py` il bootstrap fa:
>
> ```python
> import importlib
> try:
>     api_mod = importlib.import_module(f"domains.{pack.name}.api")
>     app.include_router(api_mod.router)
> except ModuleNotFoundError:
>     pass
> ```
>
> (estensione futura, non implementata in questa iterazione).

## 7. Hook di logging custom

Per audit dominio-specifici (es. logging conformità per dominio sanitario):

### `domains/medical/strategies.py` — log emit

```python
import logging
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("medical.audit")
_audit_log = Path("./vaults/medical/.audit.jsonl")


class MedicalAuditedStrategy:
    """Wrapper che logga ogni generazione per audit GDPR/conformità."""

    name = "medical.audited"

    def __init__(self, inner):
        self._inner = inner

    def matches(self, **kwargs):
        return self._inner.matches(**kwargs)

    def generate(self, ctx):
        result = self._inner.generate(ctx)
        _audit_log.parent.mkdir(parents=True, exist_ok=True)
        with _audit_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "t": datetime.utcnow().isoformat(),
                "page_type": ctx.plan_entry.page_type,
                "subtype": ctx.plan_entry.subtype,
                "target": ctx.plan_entry.target_path,
                "model": ctx.model,
                "char_count": len(result),
            }) + "\n")
        return result


def page_type_strategies():
    base = MedicalLineaGuidaStrategy()
    return [MedicalAuditedStrategy(base), MedicalPatologiaStrategy()]
```

## 8. Migrazione vault rag-wiki esistente

```bash
# il vault esistente di rag-wiki: /Users/giovanni/dev/lavoro/rag-wiki/{wiki,raw}
cd /Users/giovanni/dev/lavoro/wiki-white-label

# step 1: scaffold dominio insurance (se non già presente)
python -m llm_wiki init --domain insurance --label "Wiki Polizze" --vault-root ./vaults/insurance

# step 2: copia vault esistente nel nuovo path
cp -r /Users/giovanni/dev/lavoro/rag-wiki/wiki ./vaults/insurance/
cp -r /Users/giovanni/dev/lavoro/rag-wiki/raw  ./vaults/insurance/
cp /Users/giovanni/dev/lavoro/rag-wiki/index.md ./vaults/insurance/
cp /Users/giovanni/dev/lavoro/rag-wiki/log.md   ./vaults/insurance/

# step 3: re-index Qdrant (la nuova collection si chiama insurance-wiki, non llm-wiki)
docker compose up -d qdrant
python -m llm_wiki serve &
sleep 3
curl -X POST http://127.0.0.1:8000/api/ingest

# step 4: verifica parità chat
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Cosa copre la garanzia furto?"}'
```
