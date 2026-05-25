"""Linter deterministico per pagine wiki generate.

Scopo: **gate duro** tra LLM e disco. Ogni pagina generata passa da qui;
errori ``severity=error`` bloccano la scrittura e vengono re-inoltrati al
critic.

Le costanti (regex, sezioni obbligatorie, termini vietati) vivono in
:mod:`llm_wiki.ingest_raw.lint_constants`. I singoli check in
:mod:`llm_wiki.ingest_raw.lint_checks`. Questo modulo orchestra solo.

Output: lista di ``LintIssue`` + bool ``has_errors``. Nessun LLM qui.
"""

from __future__ import annotations

from pathlib import Path

from llm_wiki.ingest_raw.lint_checks import (
    check_citations,
    check_cover_exclusion_pair,
    check_fonti_section,
    check_franchigia_scoperto,
    check_frontmatter,
    check_no_raw_dir_writes,
    check_rule_callouts,
    check_sections,
    check_tables,
    check_terminology,
    check_verbatim,
    check_wikilinks,
    is_normative_page,
    split_frontmatter,
)
from llm_wiki.ingest_raw.lint_constants import LintIssue, LintReport, Severity

__all__ = [
    "LintIssue",
    "LintReport",
    "Severity",
    "lint_many",
    "lint_wiki_file",
    "lint_wiki_text",
]


def lint_wiki_file(path: Path, *, expected_wikilinks: set[str] | None = None) -> LintReport:
    """Linta un singolo file wiki.

    ``expected_wikilinks`` = target noti del piano (pagine che stiamo
    generando nella stessa sessione, non ancora su disco).
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        rpt = LintReport(path=str(path))
        rpt.add("io.unreadable", f"file non leggibile: {exc}", Severity.ERROR)
        return rpt
    return lint_wiki_text(raw, path=path, expected_wikilinks=expected_wikilinks)


def lint_wiki_text(
    text: str,
    *,
    path: Path | str,
    expected_wikilinks: set[str] | None = None,
) -> LintReport:
    """Linta il contenuto markdown. Usato sia da disco che da LLM output pre-write."""
    rpt = LintReport(path=str(path))
    expected = expected_wikilinks or set()

    frontmatter, body, fm_end_line = split_frontmatter(text, rpt)
    check_frontmatter(frontmatter, rpt)
    check_sections(body, frontmatter, rpt, offset_line=fm_end_line)
    # Le regole "normative" valgono nel corpo contrattuale di garanzie/clausole,
    # non nelle pagine `source` (riassunto fonte raw), `entity` (anagrafica),
    # `topic` (aggregatore). Per quelle, terminology/tables sono troppo
    # stringenti e producono errori non risolvibili dal critic.
    if is_normative_page(frontmatter):
        check_terminology(body, rpt, offset_line=fm_end_line)
        check_tables(body, rpt, offset_line=fm_end_line)
        check_franchigia_scoperto(body, rpt, offset_line=fm_end_line)
    check_citations(body, rpt, offset_line=fm_end_line)
    check_rule_callouts(body, rpt, offset_line=fm_end_line)
    check_verbatim(body, rpt, offset_line=fm_end_line)
    check_cover_exclusion_pair(body, frontmatter, rpt, offset_line=fm_end_line)
    check_wikilinks(body, rpt, expected=expected, offset_line=fm_end_line)
    check_fonti_section(body, rpt, offset_line=fm_end_line)
    check_no_raw_dir_writes(path, rpt)
    return rpt


def lint_many(paths: list[Path]) -> dict[str, LintReport]:
    return {str(p): lint_wiki_file(p) for p in paths}
