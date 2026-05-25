"""Writer per ``wiki/log.md`` e ``wiki/index.md`` post-ingest.

Estratto da ``orchestrator.py`` per rispettare il budget 500 LOC.
Operazioni filesystem deterministe: niente LLM, niente embedder.

- ``append_log``: aggiunge un'entry cronologica a ``wiki/log.md`` con
  source PDF, backend di estrazione, pagine prodotte, errori.
- ``update_index``: refresh idempotente di ``wiki/index.md`` con le
  pagine appena scritte raggruppate per page-type.

I tipi ``IngestResult``/``PageResult`` restano definiti in
``orchestrator.py`` per evitare cycle; qui sono importati solo via
``TYPE_CHECKING`` e usati come type hint forward-ref.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import TYPE_CHECKING

from llm_wiki.config import WIKI_DIR, WIKI_ROOT
from llm_wiki.domain.registry import get_pack
from llm_wiki.ingest_raw.frontmatter import slug_from_target

if TYPE_CHECKING:
    from llm_wiki.ingest_raw.orchestrator import IngestResult

logger = logging.getLogger(__name__)


def append_log(result: IngestResult, *, today: date | None) -> None:
    """Append entry cronologica a ``wiki/log.md``.

    Path matcha il seed dello scaffold (``wiki/log.md``, NON ``log.md``
    al vault root) così il LLM agent e gli esempi in istruzioni.md la
    trovano in posizione canonica. Header form ``## [YYYY-MM-DD] ingest |``
    rende `grep '^## \\['` poco costoso.
    """
    log_path = WIKI_DIR / "log.md"
    today_iso = (today or date.today()).isoformat()
    pages_line = ", ".join(
        f"[[{slug_from_target(str(p.target_path.relative_to(WIKI_ROOT)))}]]" for p in result.pages
    )
    entry = (
        f"\n## [{today_iso}] ingest | {result.source_path.name}\n"
        f"- Source: raw/{result.source_path.name}\n"
        f"- Extraction backend: {result.backend}\n"
        f"- Pages touched: {pages_line}\n"
        f"- Errors: {len(result.errors)}\n"
    )
    if result.errors:
        entry += "\n".join(f"  - {e}" for e in result.errors) + "\n"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry)
    except OSError as exc:
        logger.warning("could not write log.md: %s", exc)


def update_index(result: IngestResult) -> None:
    """Insert/refresh entry in ``wiki/index.md`` per ogni pagina scritta.

    Per istruzioni.md: "Aggiorna index.md ad ogni ingest" — il catalogo
    deve elencare ogni pagina prodotta dalla pipeline, raggruppata per
    page-type.

    Format: sotto la section header che matcha il plural label del
    page-type (creato dallo scaffold seed), aggiunge
    ``- [[slug]] — <title or category>``. Idempotente — entry già
    presenti (matchate via substring ``[[slug]]``) sono saltate, così
    re-ingest con ``overwrite=True`` non duplica righe.

    Failure non-fatale: un index corrotto non blocca l'ingestion. La
    prossima run riproverà.
    """
    index_path = WIKI_DIR / "index.md"
    if not index_path.is_file():
        # Niente index seedato — skip silenzioso. Lo scaffold del wizard
        # lo crea; vault più vecchi possono opt-in rilanciando scaffold.
        return
    try:
        text = index_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("could not read index.md: %s", exc)
        return

    pack = get_pack()
    plural_for: dict[str, str] = {}
    folder_for: dict[str, str] = {}
    for pt in pack.page_types:
        plural_for[pt.id] = (pt.plural or pt.id).capitalize()
        folder_for[pt.id] = pt.folder or pt.plural or pt.id

    plan = result.plan
    type_by_target: dict[str, str] = {}
    if plan is not None:
        for pp in [plan.source_page, *plan.derived_pages]:
            type_by_target[slug_from_target(pp.target_path)] = pp.page_type

    new_lines_by_type: dict[str, list[str]] = {}
    for page in result.pages:
        if page.status != "written":
            continue
        try:
            rel = page.target_path.relative_to(WIKI_ROOT)
        except ValueError:
            continue
        slug = slug_from_target(str(rel))
        ptype = type_by_target.get(slug, "source")
        pretty = page.target_path.stem.replace("-", " ").replace("_", " ").strip()
        line = f"- [[{slug}]] — {pretty}"
        new_lines_by_type.setdefault(ptype, []).append(line)

    if not new_lines_by_type:
        return

    updated = text
    for ptype, lines in new_lines_by_type.items():
        plural = plural_for.get(ptype) or ptype.capitalize()
        # Section header form: `## Plural[ (`wiki/folder/`)]` per scaffold seed.
        pattern = re.compile(
            rf"^(##\s+{re.escape(plural)}(?:\s+\([^)]+\))?\s*\n)",
            re.MULTILINE,
        )
        match = pattern.search(updated)
        if match is None:
            folder = folder_for.get(ptype, ptype)
            block = f"\n## {plural} (`wiki/{folder}/`)\n\n"
            for line in lines:
                if f"[[{line.split('[[')[1].split(']]')[0]}]]" not in updated:
                    block += line + "\n"
            updated = updated.rstrip() + "\n" + block + "\n"
            continue
        insertion: list[str] = []
        for line in lines:
            slug_marker = "[[" + line.split("[[", 1)[1].split("]]", 1)[0] + "]]"
            if slug_marker in updated:
                continue
            insertion.append(line)
        if not insertion:
            continue
        # Strip seed placeholder `_Nessuna voce ancora..._` se presente
        # nella sezione, così la prima entry non sta sotto dead text.
        section_end = updated.find("\n## ", match.end())
        if section_end == -1:
            section_end = len(updated)
        section_body = updated[match.end() : section_end]
        cleaned_body = re.sub(r"_Nessuna voce ancora\..*?_\n?", "", section_body, count=1)
        rebuilt = "\n".join(insertion) + "\n" + cleaned_body.lstrip("\n")
        updated = updated[: match.end()] + rebuilt + updated[section_end:]

    try:
        index_path.write_text(updated, encoding="utf-8")
    except OSError as exc:
        logger.warning("could not write index.md: %s", exc)
