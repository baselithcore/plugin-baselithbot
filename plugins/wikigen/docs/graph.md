# Knowledge Graph layer (graphify-inspired)

> Strato di knowledge graph attivabile sopra il motore wiki, ispirato al
> paradigma di [graphify](https://github.com/safishamsi/graphify):
> **wiki-as-knowledge** invece di code-as-knowledge. Estrae entità e
> relazioni tipate dalle pagine wiki, le organizza in un grafo FalkorDB
> (Cypher) e potenzia il RAG con espansione context-aware.

PR1 copre: estrazione + storage + RAG-aware retrieval + API base.
PR2 aggiungerà algoritmi grafo (Leiden communities, PageRank, god-nodes,
report). PR3 aggiungerà la viz UI React.

## Quick start

1. Avvia FalkorDB:

   ```bash
   docker compose --profile graph up -d
   ```

2. Installa l'extra (FalkorDB + `networkx` + `python-igraph` + `leidenalg`
   per algoritmi PR2):

   ```bash
   pip install -e ".[graph]"
   ```

3. Attiva nel `.env`:

   ```ini
   GRAPH_DB_ENABLED=true
   GRAPH_EXTRACT_ENABLED=true   # estrai entità a ogni ingest
   GRAPH_RAG_ENABLED=true       # arricchisci context RAG via grafo
   ```

4. Lancia un ingest:

   ```bash
   python -m llm_wiki ingest path/to/file.pdf
   ```

   Per ogni pagina scritta, l'orchestratore chiama il LLM in modalità
   JSON-schema costretta per estrarre entità + relazioni, poi le scrive
   su FalkorDB.

5. Verifica:

   ```bash
   curl localhost:8000/api/graph/stats
   ```

## Architettura

```text
ingest PDF                                     query RAG
   ↓                                              ↓
orchestrator.run_pipeline                       rag_agent.answer()
   ↓                                              ↓
output_writer.write_page                        vectorstore.search()
   ↓                                              ↓
graph.extraction.extract_from_page              expansions.expand_with_entity_graph()
   ↓ LLM JSON-schema                              ↓
graph.store.KnowledgeGraphStore                Cypher: Page→Entity→neighbors→Page
   ↓                                              ↓
FalkorDB (Cypher)                              extra hits annotated graph_expanded=true
```

### Schema FalkorDB

| Nodo                            | Properties                                            |
| ------------------------------- | ----------------------------------------------------- |
| `(:Page)`                       | `id, title, type, category, tags, source_file`        |
| `(:Entity)`                     | `id, name, kind, aliases`                             |

| Arco                                              | Properties                                           |
| ------------------------------------------------- | ---------------------------------------------------- |
| `(:Page)-[:LINKS_TO]->(:Page)`                    | da wikilinks (motore esistente)                      |
| `(:Page)-[:MENTIONS]->(:Entity)`                  | `confidence, tier`                                   |
| `(:Entity)-[:DEFINED_IN]->(:Page)`                | quando il page_type è canonical (concept/entity/topic) |
| `(:Entity)-[:R {kind}]->(:Entity)`                | `confidence, tier, evidence, page_id`                |

`tier` ∈ `{EXTRACTED, INFERRED, AMBIGUOUS}` segue la classificazione a 3
livelli di graphify:

| Tier        | Range confidence | Significato                                   |
| ----------- | ---------------- | --------------------------------------------- |
| `EXTRACTED` | ≥ 0.85           | citazione esplicita + evidenza strutturale    |
| `INFERRED`  | 0.50–0.85        | implicito ma supportato dal contesto          |
| `AMBIGUOUS` | < 0.50           | segnale debole — filtrato di default nel RAG  |

### Ontologia per-pack

Ogni Domain Pack dichiara la propria ontologia in `pack.yaml`:

```yaml
graph:
  entity_types:
    - id: concept
      label: "Concetto / Garanzia"
      description: "Garanzie, pack opzionali, clausole."
      examples: ["RCT", "regola proporzionale"]
    - id: entity
      label: "Entità"
      examples: ["Unipol Assicurazioni", "IVASS"]
    - id: source
      label: "Fonte"
      examples: ["Set Informativo", "Cass. Civ. 12345/2024"]
  relation_types:
    - id: COVERS
      label: "copre"
    - id: EXCLUDES
      label: "esclude"
    - id: DERIVES_FROM
      label: "deriva da"
  extraction_hints: |
    Identifica garanzie come concept e compagnie come entity.
```

Il prompt di estrazione enumera la vocabulary nel JSON-schema fornito al
LLM, e il post-processor `_validate_against_spec` scarta entità/
relazioni con `kind` fuori dalla spec — niente allucinazioni.

Se il pack omette `graph:`, l'engine usa un'ontologia generica
(`concept`/`entity`/`source` + `RELATES_TO`/`PART_OF`/`DERIVES_FROM`/
`DEFINED_BY`). I pack esistenti continuano a funzionare invariati.

## Env variables

| Variabile                    | Default | Note                                                                                       |
| ---------------------------- | ------- | ------------------------------------------------------------------------------------------ |
| `GRAPH_DB_ENABLED`           | `false` | Master switch per FalkorDB.                                                                |
| `GRAPH_DB_URL`               | `redis://localhost:6379` | URL FalkorDB (è un modulo Redis).                                            |
| `GRAPH_DB_NAME`              | `=COLLECTION_NAME` | Nome del grafo (multi-tenant per default).                                        |
| `GRAPH_EXTRACT_ENABLED`      | `false` | Estrazione entità/relazioni post-ingest. Costo: 1 LLM call / pagina.                       |
| `GRAPH_EXTRACT_MODEL`        | (vuoto) | Override modello sintesi; vuoto = riusa `INGEST_OLLAMA_MODEL` / `INGEST_OPENAI_MODEL`.    |
| `GRAPH_RAG_ENABLED`          | `false` | Espansione context RAG via grafo entità.                                                   |
| `GRAPH_RAG_HOPS`             | `1`     | Profondità BFS espansione (clamp [1,3]).                                                   |
| `GRAPH_RAG_MAX_EXTRA_PAGES`  | `3`     | Cap pagine extra aggiunte al context per query.                                            |
| `GRAPH_CONFIDENCE_MIN`       | `0.5`   | Filtra MENTIONS / R sotto soglia in retrieval (default tiene EXTRACTED + INFERRED).        |

## API

Tutti gli endpoint sono read-only, montati su `/api/graph/*`.

### `GET /api/graph/stats`

Metriche di alto livello. Mai 503 — restituisce `{enabled: false, ...}`
con zeri quando il grafo è offline (l'UI può renderizzare un banner).

### `GET /api/graph/entity/{id}`

Recupera un singolo nodo `Entity`. `id` formato `<kind>:<slug>` (es.
`concept:rct`). 404 se non esiste, 503 se grafo offline.

### `GET /api/graph/search?q=&kind=&limit=`

Substring match su `entity.name`. Filtro opzionale per `kind`.

### `GET /api/graph/neighbors/{id}?hops=&confidence_min=&kind=&limit=`

Espansione k-hop tipata. `hops ∈ [1,3]`. Filtra archi sotto `confidence_min`.

### `GET /api/graph/path?src=&dst=&max_hops=`

Shortest path entità-entità via edge `R`. Risponde `{found, length, path}`.

## RAG-aware retrieval

Quando `GRAPH_RAG_ENABLED=true`, dopo la stage MMR il retrieval invoca
`expand_with_entity_graph(hits)`:

1. Per ogni hit top-K → `document_id` → entità menzionate.
2. Per ogni entità → k-hop neighbors (filtrati per confidence).
3. Per ogni neighbor → pagine che lo menzionano (≠ seed docs).
4. Fetch del primo chunk Qdrant di ciascuna nuova pagina; append come hit
   `graph_expanded=true` con score 0.0.
5. Il reranker downstream (se attivo) riordina insieme ai seed.

L'espansione è **fallback-safe**: qualunque errore (grafo offline, Cypher
fallito, Qdrant timeout) → ritorna gli hits originali invariati.

## Backward compatibility / no-regression

- Tutti i flag `GRAPH_*` partono `false`. Comportamento esistente
  inalterato a meno che si attivi esplicitamente.
- Lo schema FalkorDB è **additivo**: aggiunti label `Entity` e archi
  `MENTIONS/DEFINED_IN/R`. Il label `Page` e `LINKS_TO` esistenti non
  sono toccati.
- `pack.yaml.graph` è opzionale (default factory in `DomainPack`). I
  pack pre-PR1 caricano senza modifiche.
- Il prompt template `prompts/graph/extract.j2` è opzionale: se assente,
  l'engine genera un prompt baseline dalla `GraphSpec` del pack.

## PR2 — Algoritmi + report + export

`pip install -e ".[graph]"` ora include anche `python-igraph + leidenalg`.

### Algoritmi (`llm_wiki.graphdb.algorithms`)

- `pagerank(g, alpha, top_n)` — Brin & Page 1998. Identifica "god nodes"
  (entità con autorità inbound sproporzionata). Pesato per `confidence`
  degli archi.
- `degree_centrality(g, top_n)` — metrica veloce first-pass.
- `leiden_communities(g, resolution)` — Traag/Waltman/van Eck 2019.
  Fallback automatico a weakly-connected-components se `leidenalg` non
  è installato (stessa shape, qualità minore).
- `surprising_connections(g, communities, confidence_min, top_n)` —
  high-confidence edges che attraversano boundary di community. Insight-
  density più alta per esplorazione knowledge graph.
- `snapshot(g, top_n)` — bundle one-shot di tutto sopra; usato da
  `/api/graph/report` e CLI.

### Endpoint API aggiuntivi

| Endpoint                          | Descrizione                                              |
| --------------------------------- | -------------------------------------------------------- |
| `GET /api/graph/centrality`       | Top-N PageRank/degree (`metric=pagerank|degree`).        |
| `GET /api/graph/communities`      | Leiden partition (`resolution`, `members_preview`).      |
| `GET /api/graph/surprising`       | Cross-community high-conf edges (`confidence_min`).      |
| `POST /api/graph/report`          | Genera GRAPH_REPORT.md + graph.json on demand.           |

### CLI (`wiki-wl graph ...`)

```bash
# Re-extract entities/relations from every wiki page (1 LLM call/page).
# Idempotent: wipes prior MENTIONS/DEFINED_IN/R(page_id=…) before re-write.
wiki-wl graph rebuild [--limit N] [--page-type concept]

# Write GRAPH_REPORT.md + graph.json under GRAPH_REPORT_DIR (default
# WIKI_ROOT/.graphify).
wiki-wl graph report [--output-dir PATH]

# Export entity graph in standard formats.
wiki-wl graph export --format graphml   # Gephi/yEd/Cytoscape
wiki-wl graph export --format cypher    # Neo4j import
wiki-wl graph export --format obsidian  # Wikilinked MD vault
```

### Env aggiunte

| Variabile                  | Default                       | Note                                          |
| -------------------------- | ----------------------------- | --------------------------------------------- |
| `GRAPH_LEIDEN_RESOLUTION`  | `1.0`                         | Resolution parameter Leiden RBConfiguration. |
| `GRAPH_PAGERANK_ALPHA`     | `0.85`                        | Damping factor (paper Brin & Page).          |
| `GRAPH_CENTRALITY_TOP_N`   | `25`                          | Cap default `/centrality` + report.          |
| `GRAPH_REPORT_DIR`         | `WIKI_ROOT/.graphify`         | Dove atterrano report e exports.             |

### Schema artifacts

`GRAPH_REPORT.md`: sezioni "Top entities by PageRank", "Communities",
"Surprising connections" (tabelle markdown).

`graph.json`:

```jsonc
{
  "generated_at": "2026-05-22T10:00:00+00:00",
  "stats": {"node_count": 123, "edge_count": 456, "community_count": 8},
  "nodes": [{"id": "concept:rct", "name": "RCT", "kind": "concept",
             "pagerank": 0.0834, "degree": 0.421, "community": 2}],
  "edges": [{"src": "concept:rct", "dst": "entity:unipol",
             "kind": "ISSUED_BY", "confidence": 0.94}],
  "communities": [{"id": 0, "size": 32, "cohesion": 0.71, "members": [...]}],
  "surprising": [{"src": "...", "dst": "...", "kind": "...",
                  "confidence": 0.93, "src_community": 0, "dst_community": 4}]
}
```

Consumabile dalla UI React (PR3) per renderizzare la viz cytoscape.

## PR3 — Interactive graph UI (React + cytoscape.js)

Pagina full-screen `/graph` con tre colonne:

```text
┌────────────┬──────────────────────────────┬────────────┐
│  Filtri    │       GraphCanvas            │  Detail /  │
│            │       (cytoscape)            │  Surpr.    │
└────────────┴──────────────────────────────┴────────────┘
```

### Componenti

- `frontend/pages/GraphPage.tsx` — shell + state machine + fetch.
- `frontend/components/graph/GraphCanvas.tsx` — cytoscape mount.
    - Layout `cose-bilkent` (force-directed, regge ~2k nodi interattivi).
    - Nodi: colore = community (12-color palette), dimensione = log10(PageRank).
    - Archi: spessore = confidence, label = relation kind.
    - Filtri applicati via class toggle `dimmed` (no relayout).
- `frontend/components/graph/GraphFilters.tsx` — pills kind + community,
  search input, confidence slider.
- `frontend/components/graph/EntitySidebar.tsx` — dettaglio entità
  selezionata + vicini 1-hop (lazy-fetched).
- `frontend/components/graph/SurprisingPanel.tsx` — top cross-community
  high-conf edges, click → pivot in EntitySidebar.
- `frontend/lib/api/graph.ts` — client tipato per
  `/stats /data /entity/{id} /search /neighbors /path`.

### Endpoint backend aggiunto

`GET /api/graph/data` — full payload UI-ready, stessa shape di `graph.json`:

```text
GET /api/graph/data?confidence_min=0&top_n=25&max_nodes=500&resolution=1.0
→ {enabled, stats, nodes, edges, communities, surprising}
```

Filtri server-side per bound del wire payload (cap su PageRank top-N).
Restituisce `{enabled: false, …}` se grafo offline (mai 503 → UI
renderizza banner pulito).

### Deps frontend

```json
"cytoscape": "^3.30.0",
"cytoscape-cose-bilkent": "^4.1.0",
"@types/cytoscape": "^3.21.0"
```

### Route + navigazione

- Mount: `App.tsx` intercetta `pathname.startsWith('/graph')` → render
  `<GraphPage />` full-screen (no Sidebar / Composer).
- Header chat: pulsante icona `Network` accanto agli admin tool →
  `navigate('/graph')`.
- Gating: auth richiesta (stesso gate del chat). Permesso dedicato
  `graph.read` previsto per PR4.

### Limiti noti / follow-up

- `cose-bilkent` su >2k nodi rallenta (~5–8s layout). Per grafi grandi
  PR4 introdurrà clustering iniziale → drill-in.
- L'EntitySidebar mostra il link "Vedi pagina wiki" come `#anchor`
  segnaposto. PR4: deep-link a chat con prompt pre-popolato sull'entità.
- Esiste viz solo per il vertice `Entity` (con archi `R`). Pages e
  `MENTIONS` archi non sono visualizzati — sono il livello document,
  fuori scope di una grafo-vista.
