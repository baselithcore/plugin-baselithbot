"""Pure rendering helpers translating payloads into Markdown snippets."""

from __future__ import annotations

from typing import Any, List, Mapping, Sequence

from agent_jira.project_manager import ProjectPlan
from agent_jira.config import PROJECT_PLANNER_ENABLE_TEST_CASES

from .constants import EMPTY_JIRA, EMPTY_PLAN, EMPTY_SOURCES


def format_ratio(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value * 100:.1f}%"
    return "n/d"


def format_score(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return "n/d"


def build_preview_block(
    content: str, *, max_lines: int = 6, max_chars: int = 600
) -> str:
    snippets: List[str] = []
    total_chars = 0
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        snippets.append(stripped)
        total_chars += len(stripped)
        if len(snippets) >= max_lines or total_chars >= max_chars:
            break
    return "\n".join(snippets)


def render_sources_markdown(
    sources: Sequence[Mapping[str, Any]],
    metrics: Mapping[str, Any] | None = None,
) -> str:
    if not sources:
        return EMPTY_SOURCES

    lines: List[str] = []
    for idx, source in enumerate(sources, start=1):
        title = str(source.get("title") or f"Documento {idx}").strip()
        source_type = source.get("source_type") or ""
        link = source.get("url") if source_type == "url" else source.get("path")
        if isinstance(link, str) and link.strip():
            link_clean = link.strip()
            label = (
                f"[{title}]({link_clean})"
                if source_type == "url"
                else f"{title} · `{link_clean}`"
            )
        else:
            label = title
        ratio = format_ratio(source.get("context_ratio"))
        score = format_score(source.get("score_avg") or source.get("score"))
        origin = source.get("origin") or source.get("source_type") or "n/d"
        chunks = source.get("chunks_used")
        chunk_info = (
            f"{chunks} chunk" if isinstance(chunks, int) and chunks > 0 else "n/d chunk"
        )
        lines.append(
            f"{idx}. {label} — origin: `{origin}` · score: {score} · copertura: {ratio} · {chunk_info}"
        )

    if metrics:
        bullet_lines = ["", "**Metriche di retrieval**:"]
        total_ratio = metrics.get("total_context_ratio")
        mean_ratio = metrics.get("mean_context_ratio")
        top_ratio = metrics.get("top_context_ratio")
        max_score = metrics.get("max_score")
        mean_score = metrics.get("mean_score")
        low_coverage = metrics.get("low_coverage")

        metric_items = [
            f"- Copertura totale: {format_ratio(total_ratio)}",
            f"- Copertura media: {format_ratio(mean_ratio)}",
            f"- Miglior documento: {format_ratio(top_ratio)}",
            f"- Score medio: {format_score(mean_score)}",
            f"- Score massimo: {format_score(max_score)}",
        ]
        if isinstance(low_coverage, bool):
            metric_items.append(
                f"- Copertura sufficiente: {'✅' if not low_coverage else '⚠️ bassa'}"
            )
        bullet_lines.extend(metric_items)
        lines.extend(bullet_lines)

    return "\n".join(lines)


def _get_value_from_plan(plan: Mapping[str, Any] | ProjectPlan | None, key: str) -> Any:
    if isinstance(plan, Mapping):
        return plan.get(key)
    if isinstance(plan, ProjectPlan):
        return getattr(plan, key, None)
    return None


def _escape_table_value(value: str) -> str:
    text = (value or "—").strip()
    return text.replace("|", "\\|").replace("\n", "<br>")


def _normalize_steps_value(raw_steps: Any) -> str:
    if isinstance(raw_steps, Sequence) and not isinstance(raw_steps, (str, bytes)):
        steps = [str(step).strip() for step in raw_steps if str(step).strip()]
        if steps:
            return "; ".join(steps)
    return ""


def _clean_sequence(value: Any) -> List[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _build_scenario_block(raw_scenarios: Sequence[Any]) -> List[str]:
    if not raw_scenarios:
        return []
    lines: List[str] = []
    for idx, scenario in enumerate(raw_scenarios, start=1):
        if isinstance(scenario, Mapping):
            scenario_id = str(
                scenario.get("id") or scenario.get("scenario_id") or ""
            ).strip()
            title = str(scenario.get("title") or "Scenario").strip() or "Scenario"
            given = _clean_sequence(scenario.get("given"))
            when = _clean_sequence(scenario.get("when"))
            then = _clean_sequence(scenario.get("then"))
        else:
            scenario_id = str(getattr(scenario, "scenario_id", "") or "").strip()
            title = getattr(scenario, "title", "Scenario") or "Scenario"
            title = str(title).strip() or "Scenario"
            given = _clean_sequence(getattr(scenario, "given", []))
            when = _clean_sequence(getattr(scenario, "when", []))
            then = _clean_sequence(getattr(scenario, "then", []))

        label = scenario_id or f"Scenario {idx}"
        lines.append(f"{label} – {title}")
        rows: List[tuple[int, str, str]] = []
        step_idx = 1
        for i, item in enumerate(given):
            tag = "`Given`" if i == 0 else "`And`"
            rows.append((step_idx, tag, item))
            step_idx += 1
        for i, item in enumerate(when):
            tag = "`When`" if i == 0 else "`And`"
            rows.append((step_idx, tag, item))
            step_idx += 1
        for i, item in enumerate(then):
            tag = "`Then`" if i == 0 else "`And`"
            rows.append((step_idx, tag, item))
            step_idx += 1
        if rows:
            lines.append("| # | Tag | Descrizione |")
            lines.append("| - | --- | ----------- |")
            lines.extend(f"| {num} | {tag} | {text} |" for num, tag, text in rows)
        lines.append("")
    return lines


def _build_markdown_test_case_table(test_cases: Sequence[Any]) -> List[str]:
    if not PROJECT_PLANNER_ENABLE_TEST_CASES or not test_cases:
        return []
    header = [
        "| # | Titolo | Obiettivo | Passi | Risultato atteso |",
        "| - | ------ | --------- | ----- | ---------------- |",
    ]
    rows: List[str] = []
    for idx, test_case in enumerate(test_cases, start=1):
        if isinstance(test_case, Mapping):
            title = str(test_case.get("title") or "").strip() or "Test case"
            objective = str(test_case.get("objective") or "").strip()
            raw_steps = test_case.get("steps", [])
            expected = str(test_case.get("expected_result") or "").strip()
        else:
            title = getattr(test_case, "title", "").strip() or "Test case"
            objective = getattr(test_case, "objective", "").strip()
            raw_steps = getattr(test_case, "steps", [])
            expected = getattr(test_case, "expected_result", "").strip()
        steps = _normalize_steps_value(raw_steps)
        rows.append(
            "| {idx} | {title} | {objective} | {steps} | {expected} |".format(
                idx=idx,
                title=_escape_table_value(title),
                objective=_escape_table_value(objective),
                steps=_escape_table_value(steps or "—"),
                expected=_escape_table_value(expected or "—"),
            )
        )
    return header + rows


def render_project_plan(plan: Mapping[str, Any] | ProjectPlan | None) -> str:
    if not plan:
        return EMPTY_PLAN

    parts: List[str] = []
    summary = str(_get_value_from_plan(plan, "functional_summary") or "").strip()
    if summary:
        parts.append(f"**Sintesi funzionale**\n\n{summary}")

    requirements = [
        item.strip()
        for item in (_get_value_from_plan(plan, "key_requirements") or [])
        if isinstance(item, str) and item.strip()
    ]
    if requirements:
        bullet = "\n".join(f"- {req}" for req in requirements)
        parts.append(f"**Requisiti chiave**\n\n{bullet}")

    user_stories = _get_value_from_plan(plan, "user_stories") or []
    story_lines: List[str] = []
    for idx, story in enumerate(user_stories, start=1):
        if isinstance(story, Mapping):
            title = story.get("title") or f"User Story {idx}"
            desc = story.get("description") or ""
            role = story.get("role") or ""
            goal = story.get("goal") or ""
            benefit = story.get("benefit") or ""
            priority = story.get("priority") or "n/d"
            story_points = story.get("story_points")
            jira_key = story.get("jira_issue_key")
            labels = _clean_sequence(story.get("labels"))
            raw_scenarios = story.get("scenarios") or story.get("bdd_scenarios") or []
            acceptance = [
                str(criterion).strip()
                for criterion in story.get("acceptance_criteria", [])
                if str(criterion).strip()
            ]
            raw_test_cases = story.get("test_cases") or []
        else:
            title = getattr(story, "title", f"User Story {idx}")
            desc = getattr(story, "description", "")
            role = getattr(story, "role", "")
            goal = getattr(story, "goal", "")
            benefit = getattr(story, "benefit", "")
            priority = getattr(story, "priority", "n/d")
            story_points = getattr(story, "story_points", None)
            jira_key = getattr(story, "jira_issue_key", None)
            labels = _clean_sequence(getattr(story, "labels", []))
            raw_scenarios = getattr(story, "scenarios", [])
            acceptance = [
                str(criterion).strip()
                for criterion in getattr(story, "acceptance_criteria", [])
                if str(criterion).strip()
            ]
            raw_test_cases = getattr(story, "test_cases", [])

        story_lines.append(f"### User Story {idx}: {title}")
        story_lines.append("")
        story_lines.append("**Descrizione**")
        if role or goal or benefit:
            story_lines.append(f"Come {role or 'utente'}")
            story_lines.append(f"voglio {goal or 'raggiungere un obiettivo'}")
            story_lines.append(f"così da {benefit or 'ottenere valore'}.")
        elif desc:
            story_lines.append(desc)
        story_lines.append("")

        if raw_scenarios:
            story_lines.append("**Scenari BDD**")
            scenario_lines = _build_scenario_block(raw_scenarios)
            story_lines.extend(scenario_lines)
        elif acceptance:
            story_lines.append("**Criteri di accettazione**")
            story_lines.extend(f"- {item}" for item in acceptance)
        story_lines.append("")

        meta_bits: List[str] = [f"Priorità: {priority}"]
        if isinstance(story_points, int):
            meta_bits.append(f"Story points: {story_points}")
        if jira_key:
            meta_bits.append(f"Jira: {jira_key}")
        if labels:
            meta_bits.append(f"Etichette: {', '.join(labels)}")
        story_lines.append("**Dettagli**")
        story_lines.append("\n".join(f"- {bit}" for bit in meta_bits))
        story_lines.append("")

        table_lines: List[str] = []
        if PROJECT_PLANNER_ENABLE_TEST_CASES and isinstance(raw_test_cases, Sequence):
            table_lines = _build_markdown_test_case_table(raw_test_cases)
        if table_lines:
            story_lines.append("**Casi di test suggeriti**")
            story_lines.append("")
            story_lines.extend(table_lines)
        story_lines.append("")

    if story_lines:
        parts.append("**Backlog suggerito**\n\n" + "\n".join(story_lines))

    risks = [
        item.strip()
        for item in (_get_value_from_plan(plan, "risks") or [])
        if isinstance(item, str) and item.strip()
    ]
    if risks:
        parts.append(
            "**Rischi rilevati**\n\n" + "\n".join(f"- ⚠️ {risk}" for risk in risks)
        )

    questions = [
        item.strip()
        for item in (_get_value_from_plan(plan, "open_questions") or [])
        if isinstance(item, str) and item.strip()
    ]
    if questions:
        parts.append(
            "**Domande aperte**\n\n"
            + "\n".join(f"- ❓ {question}" for question in questions)
        )

    return "\n\n".join(parts)


def render_jira_results(results: Sequence[Mapping[str, Any]]) -> str:
    if not results:
        return EMPTY_JIRA

    lines: List[str] = []
    for entry in results:
        summary = str(entry.get("summary") or "").strip() or "Richiesta"
        error = entry.get("error")
        key = entry.get("key")
        url = entry.get("url")
        status = str(entry.get("status") or "").strip()
        if error:
            lines.append(f"- ❌ **{summary}** — {error}")
            continue
        if isinstance(url, str) and url.strip():
            url_clean = url.strip()
            label = f"[{key}]({url_clean})" if key else url_clean
        else:
            label = key or "Jira"
        status_suffix = f" _(Status: {status})_" if status else ""
        lines.append(f"- ✅ {label} — {summary}{status_suffix}")
    return "\n".join(lines)


__all__ = [
    "build_preview_block",
    "format_ratio",
    "format_score",
    "render_jira_results",
    "render_project_plan",
    "render_sources_markdown",
]
