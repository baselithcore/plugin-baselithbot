from __future__ import annotations

from typing import Any, Mapping, Sequence

from agent_jira.project_manager import ProjectPlan
from agent_jira.config import PROJECT_PLANNER_ENABLE_TEST_CASES

from .utils import jira_link_for_story, safe_sequence


def _render_scenarios_html(raw_scenarios: Sequence[Any]) -> list[str]:
    lines: list[str] = []
    for idx, scenario in enumerate(raw_scenarios, start=1):
        scenario_id = str(
            getattr(scenario, "scenario_id", "") or f"SCENARIO_{idx}"
        ).strip()
        title = str(getattr(scenario, "title", "") or f"Scenario {idx}").strip()
        given = safe_sequence(getattr(scenario, "given", []))
        when = safe_sequence(getattr(scenario, "when", []))
        then = safe_sequence(getattr(scenario, "then", []))

        def _tagged_steps(tag: str, steps: list[str]) -> list[str]:
            if not steps:
                return [f"<li><strong>{tag}</strong> N/A</li>"]
            tagged: list[str] = []
            for i, step in enumerate(steps):
                if i == 0:
                    tagged.append(f"<li><strong>{tag}</strong> {step}</li>")
                else:
                    tagged.append(f"<li><strong>And</strong> {step}</li>")
            return tagged

        lines.append(
            '<div class="scenario">'
            f'<div class="scenario-title"><strong>{scenario_id}</strong> — {title}</div>'
            '<ul class="scenario-steps">'
            + "".join(_tagged_steps("Given", given))
            + "".join(_tagged_steps("When", when))
            + "".join(_tagged_steps("Then", then))
            + "</ul></div>"
        )
    return lines


def _render_test_cases_html(raw_tests: Sequence[Any]) -> list[str]:
    if not PROJECT_PLANNER_ENABLE_TEST_CASES or not raw_tests:
        return []
    rows: list[str] = []
    for idx, test_case in enumerate(raw_tests, start=1):
        title = str(getattr(test_case, "title", "") or "Test case").strip()
        objective = str(getattr(test_case, "objective", "") or "N/A").strip()
        expected = str(getattr(test_case, "expected_result", "") or "N/A").strip()
        steps = "; ".join(safe_sequence(getattr(test_case, "steps", []))) or "N/A"
        rows.append(
            f"<tr><td>{idx}</td><td>{title}</td><td>{objective}</td><td>{steps}</td><td>{expected}</td></tr>"
        )
    return rows


def build_project_plan_html(
    plan: ProjectPlan,
    *,
    metadata: Mapping[str, Any] | None = None,
    summary: str | None = None,
    jira_results: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    meta = metadata or {}
    original_name = (
        meta.get("original_name")
        or meta.get("display_name")
        or meta.get("file_name")
        or meta.get("filename")
        or meta.get("name")
    )
    doc_title = original_name or "Documento"
    doc_type = meta.get("doc_type") or meta.get("mime") or meta.get("mimetype")
    doc_size = meta.get("size_human") or meta.get("size") or meta.get("bytes")
    kb_path = meta.get("kb_path") or meta.get("path")
    kb_label = meta.get("kb_label") or meta.get("label")
    raw_summary_lines: list[str] = []
    if summary:
        raw_summary_lines = [
            line.strip() for line in summary.split("·") if line.strip()
        ]

    parts: list[str] = []
    parts.append(f'<section class="section"><h1>{doc_title}</h1></section>')

    meta_items = []
    meta_seen: set[str] = set()
    if original_name:
        meta_items.append(f"<li>Nome file: <strong>{original_name}</strong></li>")
        meta_seen.add("documento")
    if doc_type:
        meta_items.append(f"<li>Tipo documento: <strong>{doc_type}</strong></li>")
        meta_seen.add("tipo")
    if doc_size:
        meta_items.append(f"<li>Dimensione: <strong>{doc_size}</strong></li>")
        meta_seen.add("dimensione")
    if kb_path:
        meta_items.append(f"<li>Percorso KB: <code>{kb_path}</code></li>")
        meta_seen.add("percorso")
    if kb_label:
        meta_items.append(f"<li>Etichetta Jira/KB: <code>{kb_label}</code></li>")
        meta_seen.add("etichetta")
    summary_lines: list[str] = []
    if raw_summary_lines:
        for line in raw_summary_lines:
            lower = line.lower()
            if (
                lower.startswith("documento:")
                or lower.startswith("dimensione:")
                or lower.startswith("percorso kb:")
                or lower.startswith("etichetta")
                or lower.startswith("tipo")
                or lower.startswith("testo analizzato")
            ):
                key = (
                    "documento"
                    if lower.startswith("documento:")
                    else "dimensione"
                    if lower.startswith("dimensione:")
                    else "percorso"
                    if lower.startswith("percorso kb:")
                    else "etichetta"
                    if lower.startswith("etichetta")
                    else "tipo"
                    if lower.startswith("tipo")
                    else "testo"
                )
                if key not in meta_seen:
                    meta_items.append(f"<li>{line}</li>")
                    meta_seen.add(key)
            else:
                summary_lines.append(line)

    if meta_items:
        parts.append(
            '<section class="section"><h2>Dettagli documento</h2><ul>'
            + "".join(meta_items)
            + "</ul></section>"
        )

    if summary_lines:
        parts.append(
            '<section class="section"><h2>Riepilogo analisi</h2><ul>'
            + "".join(f"<li>{line}</li>" for line in summary_lines)
            + "</ul></section>"
        )

    if plan.functional_summary:
        parts.append(
            f'<section class="section"><h2>Sintesi funzionale</h2><p>{plan.functional_summary}</p></section>'
        )

    if plan.key_requirements:
        parts.append(
            '<section class="section"><h2>Requisiti chiave</h2><ul>'
            + "".join(f"<li>{req}</li>" for req in plan.key_requirements)
            + "</ul></section>"
        )

    if plan.user_stories:

        def _priority_rank(val: str | None) -> int:
            if not val:
                return 5
            v = val.lower()
            if v in {"highest", "blocker", "critical"}:
                return 0
            if v in {"high"}:
                return 1
            if v in {"medium", "should"}:
                return 2
            if v in {"low", "could"}:
                return 3
            return 4

        sorted_stories = sorted(
            plan.user_stories,
            key=lambda s: _priority_rank(getattr(s, "priority", None)),
        )
        story_sections: list[str] = []
        for idx, story in enumerate(sorted_stories, start=1):
            jira_link = jira_link_for_story(story, jira_results or [])
            story_parts: list[str] = []
            story_parts.append(f"<h3>{idx}. {story.title}</h3>")
            story_parts.append(
                "<ul>"
                f"<li><strong>Priorità:</strong> {story.priority or 'n/d'}</li>"
                f"<li><strong>Jira:</strong> {jira_link}</li>"
                "</ul>"
            )
            section_idx = 1
            story_parts.append(
                f"<h4>{section_idx}. Descrizione</h4>"
                f"<p><strong>Come</strong> {story.role} <strong>voglio</strong> {story.goal} "
                f"<strong>cosi da</strong> {story.benefit}.</p>"
            )
            section_idx += 1

            raw_business_values = safe_sequence(getattr(story, "business_value", []))
            business_values: list[str] = []
            seen: set[str] = set()
            for val in raw_business_values:
                clean = str(val).strip()
                if not clean:
                    continue
                lower = clean.lower()
                if lower in seen:
                    continue
                seen.add(lower)
                business_values.append(clean)

            benefit_fallback = str(getattr(story, "benefit", "") or "").strip()
            if benefit_fallback:
                lower_benefit = benefit_fallback.lower()
                if lower_benefit not in seen:
                    business_values.append(benefit_fallback)

            # Keep business value concise in the report (max 3 bullet points).
            business_values = business_values[:3]

            if business_values:
                story_parts.append(
                    f"<h4>{section_idx}. Business value</h4><ul>"
                    + "".join(f"<li>{val}</li>" for val in business_values)
                    + "</ul>"
                )
                section_idx += 1

            scenarios = getattr(story, "scenarios", []) or getattr(
                story, "bdd_scenarios", []
            )
            if scenarios:
                scenario_lines = _render_scenarios_html(scenarios)
                story_parts.append(
                    f'<section class="scenario-block"><h4>{section_idx}. Scenari BDD</h4>'
                    + "".join(scenario_lines)
                    + "</section>"
                )
                section_idx += 1
            else:
                acceptance = safe_sequence(getattr(story, "acceptance_criteria", []))
                if acceptance:
                    story_parts.append(
                        f"<h4>{section_idx}. Criteri di accettazione</h4><ul>"
                        + "".join(f"<li>{item}</li>" for item in acceptance)
                        + "</ul>"
                    )
                    section_idx += 1

            tests = getattr(story, "test_cases", [])
            test_rows = _render_test_cases_html(tests)
            if test_rows:
                table_html = (
                    f"<h4>{section_idx}. Test case suggeriti</h4>"
                    "<table><thead><tr><th>#</th><th>Titolo</th><th>Obiettivo</th><th>Passi</th><th>Risultato atteso</th></tr></thead>"
                    "<tbody>" + "".join(test_rows) + "</tbody></table>"
                )
                story_parts.append(table_html)
            story_sections.append(
                '<div class="story-block">' + "".join(story_parts) + "</div>"
            )

        parts.append(
            '<section class="section"><h2>User story e collegamenti Jira</h2>'
            + "".join(story_sections)
            + "</section>"
        )

    if plan.risks:
        parts.append(
            '<section class="section"><h2>Rischi individuati</h2><ul>'
            + "".join(f"<li>{risk}</li>" for risk in plan.risks)
            + "</ul></section>"
        )

    if plan.open_questions:
        parts.append(
            '<section class="section"><h2>Domande aperte</h2><ul>'
            + "".join(f"<li>{question}</li>" for question in plan.open_questions)
            + "</ul></section>"
        )

    return "".join(parts)


def render_report_html(body_html: str, title: str | None = None) -> str:
    page_title = (title or "Project plan").strip() or "Project plan"
    styles = """
    body { font-family: "Inter", system-ui, -apple-system, sans-serif; color: #0f172a; margin: 0; padding: 0; }
    .report { max-width: 900px; margin: 24px auto; padding: 0 24px 48px; position: relative; }
    @page { margin: 18mm; }
    h1, h2, h3, h4 { color: #0f172a; margin-top: 1.6em; }
    h1 { font-size: 28px; }
    h2 { font-size: 22px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }
    h3 { font-size: 18px; margin-top: 1.2em; }
    h4 { font-size: 16px; margin: 0 0 8px; }
    p { line-height: 1.6; margin: 0 0 10px; }
    code { background: #f8fafc; padding: 2px 6px; border-radius: 6px; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; page-break-inside: avoid; break-inside: avoid; }
    th, td { border: 1px solid #e2e8f0; padding: 6px 8px; text-align: left; vertical-align: top; }
    strong { color: #0f172a; }
    ul, ol { padding-left: 18px; page-break-inside: avoid; break-inside: avoid; margin: 6px 0; }
    li { margin: 2px 0; }
    h2, h3, h4 { page-break-after: avoid; page-break-inside: avoid; break-inside: avoid; }
    .story-block { page-break-inside: avoid; break-inside: avoid; margin-bottom: 18px; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0; }
    .story-block h3 { margin-bottom: 4px; }
    .section { page-break-inside: avoid; break-inside: avoid; }
    .report-header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e2e8f0; padding: 12px 0; margin-bottom: 18px; }
    .logo-placeholder { width: 140px; height: 40px; border: 1px dashed #cbd5e1; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px; }
    .report-meta { text-align: right; font-size: 12px; color: #475569; }
    .report-meta .title { font-weight: 700; color: #0f172a; }
    .report-meta .date { display: block; margin-top: 4px; }
    .scenario-block { page-break-inside: avoid; break-inside: avoid; margin-bottom: 10px; }
    .scenario { margin-bottom: 8px; }
    .scenario-title { font-weight: 700; margin-bottom: 4px; }
    .scenario-steps { margin: 4px 0 0 18px; padding: 0; list-style: disc; }
    .report-body { padding-top: 0; }
    """
    return f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>{page_title}</title>
    <style>{styles}</style>
  </head>
  <body>
    <article class="report">
      <header class="report-header">
        <div class="logo-placeholder">LOGO</div>
        <div class="report-meta">
          <span class="title">{page_title}</span>
          <span class="date">{""}</span>
        </div>
      </header>
      <div class="report-body">{body_html}</div>
    </article>
    <script>
      window.onload = () => {{
        window.focus();
        window.print();
      }};
    </script>
  </body>
</html>"""


__all__ = [
    "build_project_plan_html",
    "render_report_html",
]
