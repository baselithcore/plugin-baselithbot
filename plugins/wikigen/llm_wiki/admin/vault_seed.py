"""Vault seed rendering: index.md / log.md / CLAUDE.md (Karpathy pattern).

Materialises the three files mandated by ``istruzioni.md`` plus per-page-type
subfolders under ``wiki/``. Idempotent — never clobbers existing user edits.

Kept separate from :mod:`llm_wiki.admin.scaffold` so the markdown templates
can grow without bloating the scaffold orchestrator.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def read_pack_data(pack_dir: Path) -> dict[str, Any]:
    pack_yaml = pack_dir / "pack.yaml"
    try:
        return yaml.safe_load(pack_yaml.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def seed_vault(vault: Path, pack_dir: Path, *, name: str, label: str) -> None:
    """Materialise the three files mandated by ``istruzioni.md``:

    - ``wiki/index.md`` — content-oriented catalog grouped by page type.
    - ``wiki/log.md`` — chronological append-only log.
    - ``CLAUDE.md`` — agent schema document at vault root.

    Per-page-type subfolders under ``wiki/`` are also created. Skips any
    file that already exists — re-scaffold (``force=true``) does not
    clobber user edits to ``index.md`` / ``log.md`` / ``CLAUDE.md``.
    """
    pack_data = read_pack_data(pack_dir)
    page_types: list[dict[str, Any]] = pack_data.get("page_types") or []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    wiki_dir = vault / "wiki"
    for pt in page_types:
        folder = pt.get("folder") or pt.get("plural") or pt.get("id")
        if folder:
            (wiki_dir / str(folder)).mkdir(parents=True, exist_ok=True)

    index_path = wiki_dir / "index.md"
    if not index_path.exists():
        index_path.write_text(_render_index(label, page_types), encoding="utf-8")

    log_path = wiki_dir / "log.md"
    if not log_path.exists():
        log_path.write_text(_render_log(name, label, today), encoding="utf-8")

    claude_path = vault / "CLAUDE.md"
    if not claude_path.exists():
        claude_path.write_text(_render_claude_md(name, label, page_types), encoding="utf-8")


def _render_index(label: str, page_types: list[dict[str, Any]]) -> str:
    lines = [
        f"# {label} — Index",
        "",
        "_Catalog content-oriented della wiki. Aggiornato dall'agente LLM ad ogni ingest._",
        "",
        "## Sommario",
        "",
        "_Una breve descrizione del dominio comparirà qui dopo i primi ingest._",
        "",
    ]
    for pt in page_types:
        plural = str(pt.get("plural") or pt.get("id") or "voci").capitalize()
        folder = pt.get("folder") or pt.get("plural") or pt.get("id")
        anchor_hint = f" (`wiki/{folder}/`)" if folder else ""
        lines += [
            f"## {plural}{anchor_hint}",
            "",
            "_Nessuna voce ancora. L'agente LLM popola questa sezione al primo ingest._",
            "",
        ]
    lines += [
        "---",
        "",
        "Convenzioni:",
        "- Una riga per voce, formato `- [[slug]] — descrizione in una frase`.",
        "- Categorie ordinate alfabeticamente all'interno di ogni sezione.",
        "- L'agente aggiorna questo file ad ogni ingest senza chiedere conferma.",
        "",
    ]
    return "\n".join(lines)


def _render_log(name: str, label: str, today: str) -> str:
    return (
        f"# {label} — Log\n"
        "\n"
        "_Registro append-only delle operazioni sulla wiki. Greppabile con_\n"
        "`grep '^## \\[' log.md | tail -n 20`.\n"
        "\n"
        f"## [{today}] scaffold | {name}\n"
        "\n"
        f"Vault inizializzato dal Setup Wizard. Pack: `{name}` ({label}).\n"
        "Layout: `raw/` (immutabile), `wiki/` (LLM-managed), `CLAUDE.md` (schema).\n"
        "Indici creati: `wiki/index.md`, `wiki/log.md`.\n"
        "\n"
    )


def _render_claude_md(name: str, label: str, page_types: list[dict[str, Any]]) -> str:
    pt_lines = []
    for pt in page_types:
        pid = str(pt.get("id") or "")
        plabel = str(pt.get("label") or pid)
        folder = pt.get("folder") or pt.get("plural") or pid
        pt_lines.append(f"- **{pid}** — {plabel} → `wiki/{folder}/`")
    pt_block = "\n".join(pt_lines) if pt_lines else "_(definiti in `domains/<pack>/pack.yaml`)_"

    return f"""# CLAUDE.md — schema agente per `{name}`

> **{label}** — istanza del pattern LLM-Wiki (Karpathy).
> Questo file definisce le **regole** che l'agente LLM segue ogni volta
> che lavora su questo vault. Aggiornalo se cambiano convenzioni.

## Layer

Tre layer immutabili:

1. **Raw** (`raw/`) — fonti caricate dall'utente. **Mai modificare.**
2. **Wiki** (`wiki/`) — markdown generato e mantenuto **solo dall'agente LLM**.
3. **Schema** (questo file `CLAUDE.md`) — regole stabili. Co-evolvono con l'utente.

## Tassonomia delle pagine

{pt_block}

Ogni pagina deve avere frontmatter YAML conforme a `domains/{name}/schema.yaml`:

```yaml
---
title: "..."
page_type: source | concept | entity | topic
tags: [...]
---
```

## Indici

- `wiki/index.md` è **content-oriented**: catalogo di tutte le pagine
  raggruppate per page type. L'agente lo aggiorna ad ogni ingest senza
  chiedere conferma.
- `wiki/log.md` è **cronologico**, append-only. Ogni entry inizia con
  `## [YYYY-MM-DD] {{op}} | {{titolo}}` per essere greppabile.

## Operations

### Ingest
1. Leggi la nuova fonte sotto `raw/`.
2. Discuti con l'utente i takeaway chiave.
3. Scrivi la pagina source `wiki/sources/<slug>.md`.
4. Aggiorna/crea entity/concept/topic correlati con cross-link `[[...]]`.
5. Aggiorna `index.md` (nuove voci) e `log.md` (entry datata).
6. Segnala contraddizioni con pagine esistenti.

### Query
1. Leggi `index.md` per trovare le pagine rilevanti.
2. Leggi le pagine, rispondi sintetizzando con citazioni `[[slug#anchor]]`.
3. Risposte interessanti vanno filed back come nuove pagine.

### Lint
Periodicamente:
- contraddizioni tra pagine
- claim stantii sostituiti da fonti più recenti
- pagine orfane (zero inbound link)
- concetti citati senza pagina dedicata
- gap di copertura → suggerisci nuove fonti / web search

## Cross-link

Sempre `[[slug]]` (Obsidian style). L'agente non rompe link esistenti
quando rinomina; aggiorna ogni occorrenza.

## Engine integrato

Questo vault è gestito dal motore white-label `llm-wiki`. Configurazione
attiva sotto `domains/{name}/`:

- `pack.yaml` — tassonomia + grouping rules + UI labels
- `prompts/` — Jinja2 template per RAG e ingest
- `schema.yaml` — frontmatter validation rules
- `strategies.py` (opzionale) — hook per page_type/subtype custom

Modifica questi file per personalizzare il comportamento dell'agente.

## Mai

- Modificare `raw/`.
- Cancellare `index.md` o `log.md` (sono indici append/aggregato, non rigenerabili da soli).
- Scrivere prompt o regole hardcoded nel codice Python: vivono in `prompts/`.
"""
