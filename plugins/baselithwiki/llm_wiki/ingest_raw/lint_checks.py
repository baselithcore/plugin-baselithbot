"""Singoli check del linter wiki.

Ogni funzione è pura: legge il body markdown + frontmatter e accumula
issue su un :class:`LintReport`. Niente I/O di rete o LLM.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from llm_wiki.ingest_raw.lint_constants import (
    ART_RE,
    FRONTMATTER_RE,
    QUOTE_CALLOUT_RE,
    RULE_CALLOUT_RE,
    SEZIONI_GARANZIA,
    SEZIONI_SOURCE,
    TERMINI_SENSIBILI_RE,
    TERMINI_VIETATI_RE,
    WIKILINK_RE,
    LintReport,
    Severity,
)


def is_normative_page(fm: dict[str, Any]) -> bool:
    """Pagina con corpo contrattuale: concept con subtype garanzia/pack/clausola/normativa.

    Source/entity/topic riassumono o anagrafano: il corpo è editoriale, non
    contrattuale. Applicare a esse il regime "Rigore terminologico" produce
    falsi positivi (es. "Standard" in titolo originale di fonte).
    """
    if fm.get("type") != "concept":
        return False
    subtype = fm.get("subtype", "")
    return subtype in {
        "garanzia-assicurativa",
        "pack-opzionale",
        "clausola",
        "prodotto-assicurativo",
        "normativa",
        "sentenza",
    }


def split_frontmatter(text: str, rpt: LintReport) -> tuple[dict[str, Any], str, int]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        rpt.add(
            "frontmatter.missing",
            "frontmatter YAML assente (obbligatorio, CLAUDE.md §Frontmatter di base).",
            Severity.ERROR,
            line=1,
        )
        return {}, text, 0
    try:
        fm = yaml.safe_load(m.group(1)) or {}
        if not isinstance(fm, dict):
            raise yaml.YAMLError("frontmatter non è un dict")
    except yaml.YAMLError as exc:
        rpt.add(
            "frontmatter.invalid", f"YAML non parsabile: {exc}", Severity.ERROR, line=1
        )
        return {}, text[m.end() :], text[: m.end()].count("\n")
    return fm, text[m.end() :], text[: m.end()].count("\n")


def check_frontmatter(fm: dict[str, Any], rpt: LintReport) -> None:
    if not fm:
        return
    ptype = fm.get("type")
    if ptype not in {"concept", "entity", "topic", "source", "synthesis"}:
        rpt.add(
            "frontmatter.type",
            f"campo `type` mancante o non valido: {ptype!r}",
            Severity.ERROR,
            hint="valori ammessi: concept|entity|topic|source|synthesis",
        )
        return
    if "title" not in fm or not fm["title"]:
        rpt.add("frontmatter.title", "campo `title` obbligatorio.", Severity.ERROR)

    if ptype == "source":
        for req in ("source_file", "source_type", "ingested"):
            if req not in fm:
                rpt.add(
                    "frontmatter.source.missing",
                    f"campo `{req}` obbligatorio per `type: source`.",
                    Severity.ERROR,
                )
        # versioning per fonti contrattuali/regolamentari
        stype = fm.get("source_type", "")
        if stype in {
            "polizza-set-informativo",
            "norme-assuntive",
            "regolamento-ivass",
            "circolare-ivass",
            "dip",
            "dip-aggiuntivo",
        }:
            for req in ("edizione", "edizione-iso", "decorrenza", "stato", "modello"):
                if req not in fm:
                    rpt.add(
                        "frontmatter.versioning.missing",
                        f"campo `{req}` obbligatorio per fonte contrattuale/regolamentare.",
                        Severity.ERROR,
                        hint="CLAUDE.md §Versioning",
                    )

    if ptype == "concept" and fm.get("subtype") == "garanzia-assicurativa":
        for req in (
            "richiede-sezioni",
            "richiede-logica",
            "acquistabile-senza-base",
            "vincoli-note",
        ):
            if req not in fm:
                rpt.add(
                    "frontmatter.propedeuticita.missing",
                    f"campo `{req}` obbligatorio per garanzia assicurativa.",
                    Severity.ERROR,
                    hint="CLAUDE.md §Gerarchie di garanzia",
                )
        logica = fm.get("richiede-logica")
        if logica not in {"any_of", "all_of", "none"}:
            rpt.add(
                "frontmatter.propedeuticita.logica",
                f"`richiede-logica` = {logica!r} non ammesso",
                Severity.ERROR,
                hint="any_of | all_of | none",
            )


def check_sections(
    body: str, fm: dict[str, Any], rpt: LintReport, *, offset_line: int
) -> None:
    ptype = fm.get("type")
    subtype = fm.get("subtype")
    if ptype == "concept" and subtype in {"garanzia-assicurativa", "pack-opzionale"}:
        required = SEZIONI_GARANZIA
    elif ptype == "source":
        required = SEZIONI_SOURCE
    else:
        return
    for section in required:
        if not _section_present(body, section):
            rpt.add(
                "structure.missing_section",
                f"sezione obbligatoria mancante: `{section}`",
                Severity.ERROR,
                hint="vedi template CLAUDE.md §Struttura-tipo",
            )


def _section_present(body: str, header: str) -> bool:
    # accetta heading a QUALSIASI livello ≥ quello specificato (`##` o `###`...).
    # match parziale sul testo: "## Limiti" matcha anche "## Limiti di indennizzo ...".
    # Pagine "umbrella" (es. Eventi Catastrofali 5.1 + 5.2) usano H3 sotto H2 di sub-garanzia.
    level_prefix = header.count("#")
    text = header.lstrip("# ").strip()
    pat = re.compile(
        rf"^#{{{level_prefix},6}}\s+{re.escape(text)}\b", re.MULTILINE | re.IGNORECASE
    )
    return pat.search(body) is not None


def check_terminology(body: str, rpt: LintReport, *, offset_line: int) -> None:
    # escludi contenuto dentro callout divulgativi (tip/question/example) dove i
    # tecnicismi colloquiali sono ammessi
    normative = _strip_divulgative_callouts(body)
    for m in TERMINI_VIETATI_RE.finditer(normative):
        line = normative[: m.start()].count("\n") + 1 + offset_line
        rpt.add(
            "terminology.forbidden",
            f"termine vietato nel corpo normativo: `{m.group(0)}`",
            Severity.ERROR,
            line=line,
            hint="usa la formulazione contrattuale esatta — CLAUDE.md §Rigore terminologico",
        )


def _strip_divulgative_callouts(body: str) -> str:
    # rimuove callout [!tip] [!question] [!example] dal body → rimane corpo normativo
    return re.sub(
        r"(^>\s*\[!(tip|question|example|info)\][^\n]*\n(>.*\n?)*)",
        "",
        body,
        flags=re.MULTILINE,
    )


def check_citations(body: str, rpt: LintReport, *, offset_line: int) -> None:
    # ogni bullet/paragrafo con claim quantitativo ("€", "%", "giorni", "anni")
    # dovrebbe contenere un riferimento articolo
    lines = body.splitlines()
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(
            (">", "#", "|", "```", "yaml", "-", "*")
        ):
            continue
        # tratta anche bullet "- ..."
        content = stripped.lstrip("-* ").strip()
        if not content:
            continue
        if _has_quantitative_claim(content) and not ART_RE.search(content):
            # guarda le 3 righe precedenti/successive per tolleranza (citazione distante)
            window = "\n".join(lines[max(0, idx - 3) : idx + 2])
            if not ART_RE.search(window):
                rpt.add(
                    "citations.missing_article",
                    "claim quantitativo senza riferimento articolo.",
                    Severity.WARN,
                    line=idx + offset_line,
                    hint=f"aggiungi `(art. X.Y CdA)` o equivalente. Riga: {content[:80]!r}",
                )


def _has_quantitative_claim(text: str) -> bool:
    return bool(
        re.search(
            r"(€|EUR)\s*\d|\d+\s*%|\d+\s+(giorn|mes|ann)i?|\bmassimal",
            text,
            re.IGNORECASE,
        )
    )


def check_rule_callouts(body: str, rpt: LintReport, *, offset_line: int) -> None:
    # ogni `> [!rule]` deve contenere Condizione:, Valore/effetto:, Fonte:
    for m in RULE_CALLOUT_RE.finditer(body):
        start = m.start()
        # estrai il blocco callout (righe contigue che iniziano con `>`)
        block_lines = []
        for line in body[start:].splitlines():
            if not line.startswith(">") and not line.strip() == "":
                break
            block_lines.append(line)
            if line.strip() == "":
                # consentito una riga vuota interna al callout se seguita da `>`
                continue
        block = "\n".join(block_lines)
        missing = []
        if not re.search(r"\*\*Condizione\*\*", block, re.IGNORECASE):
            missing.append("Condizione")
        if not re.search(
            r"\*\*Valore/effetto\*\*|\*\*Effetto\*\*", block, re.IGNORECASE
        ):
            missing.append("Valore/effetto")
        if not re.search(r"\*\*Fonte\*\*", block, re.IGNORECASE):
            missing.append("Fonte")
        if missing:
            line_no = body[:start].count("\n") + 1 + offset_line
            rpt.add(
                "rules.incomplete",
                f"callout `> [!rule]` senza campi: {', '.join(missing)}",
                Severity.ERROR,
                line=line_no,
                hint="CLAUDE.md §Regole condizionali — callout dedicato",
            )


def check_tables(body: str, rpt: LintReport, *, offset_line: int) -> None:
    """Ogni tabella tecnica (>= 3 righe dati) deve avere caption + YAML sibling."""
    tables = _extract_tables(body)
    for tbl in tables:
        # considera "tecnica" se contiene Euro, percentuali, numeri grossi
        joined = "\n".join(tbl["rows"])
        is_technical = bool(re.search(r"€\s*\d|EUR\s*\d|\d+\s*%|\d{3,}", joined))
        n_data_rows = max(0, len(tbl["rows"]) - 2)  # sottrai header + separator
        if not is_technical or n_data_rows < 3:
            continue
        # caption = riga di testo sopra la tabella che inizia con ** e cita art./pag.
        caption = _caption_before(body, tbl["start_idx"])
        line = body[: tbl["start_idx"]].count("\n") + 1 + offset_line
        if not caption or not ART_RE.search(caption):
            rpt.add(
                "tables.caption.missing",
                "tabella tecnica senza caption con riferimento articolo/pagina.",
                Severity.ERROR,
                line=line,
                hint="`**Tabella N.M — <oggetto> (fonte, art. X, pag. N).**`",
            )
        if not _yaml_sibling_after(body, tbl["end_idx"]):
            rpt.add(
                "tables.yaml_sibling.missing",
                "tabella tecnica senza blocco YAML strutturato (`yaml` fence) subito dopo.",
                Severity.ERROR,
                line=line,
                hint="CLAUDE.md §Tabelle strutturate — blocco YAML sibling",
            )


def _extract_tables(body: str) -> list[dict[str, Any]]:
    """Restituisce lista di tabelle: {start_idx, end_idx, rows}."""
    out: list[dict[str, Any]] = []
    lines = body.splitlines(keepends=True)
    i = 0
    offset = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("|") and "|" in line.rstrip()[1:]:
            start_idx = offset
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].rstrip("\n"))
                offset += len(lines[i])
                i += 1
            end_idx = offset
            if len(rows) >= 2:
                out.append({"start_idx": start_idx, "end_idx": end_idx, "rows": rows})
            continue
        offset += len(line)
        i += 1
    return out


def _caption_before(body: str, idx: int) -> str | None:
    # cerca indietro fino a 3 righe non vuote
    chunk = body[:idx].rstrip()
    lines = chunk.splitlines()[-3:]
    for ln in reversed(lines):
        if ln.strip().startswith("**Tabella") or ln.strip().startswith("**Tab."):
            return ln.strip()
    return None


def _yaml_sibling_after(body: str, idx: int) -> bool:
    after = body[idx : idx + 1500]  # guarda prossimi ~1.5KB
    # salta righe vuote
    after_stripped = after.lstrip("\n ")
    return after_stripped.startswith("```yaml")


def check_verbatim(body: str, rpt: LintReport, *, offset_line: int) -> None:
    # se presenti termini sensibili, deve esserci almeno un `> [!quote]` nella pagina
    if TERMINI_SENSIBILI_RE.search(body) and not QUOTE_CALLOUT_RE.search(body):
        m = TERMINI_SENSIBILI_RE.search(body)
        line = body[: m.start()].count("\n") + 1 + offset_line if m else None
        rpt.add(
            "verbatim.missing",
            "termini sensibili (dolo/colpa grave/...) presenti senza callout `> [!quote]`.",
            Severity.ERROR,
            line=line,
            hint="CLAUDE.md §Citazioni verbatim — grounding visivo obbligatorio",
        )


def check_franchigia_scoperto(body: str, rpt: LintReport, *, offset_line: int) -> None:
    # pattern vietato: intestazione "Franchigia/Scoperto" fusa
    if re.search(r"Franchigia\s*/\s*Scoperto", body, re.IGNORECASE):
        rpt.add(
            "tables.franchigia_scoperto.fused",
            "colonna `Franchigia/Scoperto` fusa: CLAUDE.md §Franchigia vs Scoperto richiede colonne distinte.",
            Severity.ERROR,
        )
    # pattern vietato: "franchigia del X%"
    for m in re.finditer(r"franchigia\s+del\s+\d+\s*%", body, re.IGNORECASE):
        line = body[: m.start()].count("\n") + 1 + offset_line
        rpt.add(
            "terminology.franchigia_pct",
            "`franchigia del N%` è errore contrattuale: la franchigia è fissa in €, la % è Scoperto.",
            Severity.ERROR,
            line=line,
        )


def check_cover_exclusion_pair(
    body: str, fm: dict[str, Any], rpt: LintReport, *, offset_line: int
) -> None:
    if fm.get("subtype") not in {"garanzia-assicurativa", "pack-opzionale"}:
        return
    # entrambe sezioni devono esistere
    has_copre = "## Cosa copre" in body or re.search(
        r"^###\s+Cosa copre", body, re.MULTILINE
    )
    has_non = "## Cosa NON copre" in body or re.search(
        r"^###\s+Esclusioni|^###\s+Cosa NON copre", body, re.MULTILINE
    )
    if has_copre and not has_non:
        rpt.add(
            "crossref.missing_exclusions",
            "`## Cosa copre` presente senza `## Cosa NON copre` corrispondente.",
            Severity.ERROR,
            hint="CLAUDE.md §Cross-link cover/exclusion",
        )


def check_wikilinks(
    body: str, rpt: LintReport, *, expected: set[str], offset_line: int
) -> None:
    seen = WIKILINK_RE.findall(body)
    # no hard-fail su risoluzione perché molti target possono essere del piano;
    # segnala solo wikilink con caratteri strani
    for target in seen:
        target = target.strip()
        if not re.match(r"^[a-z0-9\-/]+$", target):
            rpt.add(
                "wikilinks.non_kebab",
                f"wikilink non kebab-case ASCII: `[[{target}]]`",
                Severity.WARN,
                hint="CLAUDE.md §Lingua: nomi file kebab-case ASCII",
            )


def check_fonti_section(body: str, rpt: LintReport, *, offset_line: int) -> None:
    if "## Fonti" not in body:
        return  # already flagged as missing-section per-type
    # la sezione deve contenere almeno un wikilink
    fonti_match = re.search(r"^## Fonti\s*\n(.*)", body, re.MULTILINE | re.DOTALL)
    if fonti_match and not WIKILINK_RE.search(fonti_match.group(1)):
        rpt.add(
            "citations.fonti.empty",
            "sezione `## Fonti` senza wikilink a `wiki/sources/...`",
            Severity.ERROR,
            hint="CLAUDE.md §Citazioni obbligatorie",
        )


def check_no_raw_dir_writes(path: Path | str, rpt: LintReport) -> None:
    # sanity: la pagina non deve essere in raw/
    s = str(path)
    if "/raw/" in s or s.startswith("raw/") or s.endswith("/raw"):
        rpt.add(
            "safety.raw_write",
            "tentativo di scrittura in `raw/` (immutabile, CLAUDE.md §1).",
            Severity.ERROR,
        )
