from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from agent_jira.project_manager import TestCase


def build_bdd_scenario_adf(
    *,
    scenario_title: str,
    given: Sequence[str],
    when: Sequence[str],
    then: Sequence[str],
    scenario_id: Optional[str] = None,
    priority: Any = None,
) -> Dict[str, Any]:
    def _steps_block(tag: str, steps: Sequence[str]) -> List[Dict[str, Any]]:
        if not steps:
            return []
        items: List[Dict[str, Any]] = []
        for idx, step in enumerate(steps, 1):
            items.append(
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": f"{tag if idx == 1 else 'And'}: ",
                                            "marks": [{"type": "strong"}],
                                        },
                                        {"type": "text", "text": step},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            )
        return items

    header_table = {
        "type": "table",
        "content": [
            {
                "type": "tableRow",
                "content": [
                    table_header_cell("Scenario ID"),
                    table_header_cell("Titolo"),
                    table_header_cell("Pre-condizioni"),
                    table_header_cell("Post-condizioni"),
                    table_header_cell("Priorità"),
                ],
            },
            {
                "type": "tableRow",
                "content": [
                    table_cell_node(scenario_id or "—"),
                    table_cell_node(scenario_title or "—"),
                    table_cell_node("; ".join(step for step in given if step) or "—"),
                    table_cell_node("; ".join(step for step in then if step) or "—"),
                    table_cell_node(str(priority).strip() if priority else "—"),
                ],
            },
        ],
    }

    return {
        "type": "doc",
        "version": 1,
        "content": [
            header_table,
            {
                "type": "heading",
                "attrs": {"level": 5},
                "content": [{"type": "text", "text": "Steps"}],
            },
            *_steps_block("Given", given),
            *_steps_block("When", when),
            *_steps_block("Then", then),
        ],
    }


def build_user_story_description(
    *,
    description: str,
    acceptance_criteria: Sequence[str],
    business_value: Sequence[str],
    test_cases: Optional[Sequence[Union[TestCase, Mapping[str, Any]]]] = None,
) -> Dict[str, Any]:
    content: List[Dict[str, Any]] = []
    main_description = (description or "").strip()
    if main_description:
        content.extend(paragraphs_from_text(main_description))
    else:
        content.append(paragraph_node("—"))
    if business_value:
        content.append(paragraph_node("Business value:"))
        for value in business_value:
            content.append(paragraph_node(f"• {value}"))
    if acceptance_criteria:
        content.append(paragraph_node("Criteria:"))
        for criterion in acceptance_criteria:
            crit = str(criterion or "").strip()
            if not crit:
                continue
            lines = [line.strip() for line in crit.splitlines() if line.strip()]
            if not lines:
                continue
            title = lines[0]
            table_lines = [line for line in lines[1:] if line.startswith("|")]
            content.append(paragraph_node(title))
            table_node = build_pipe_table_node(table_lines)
            if table_node:
                content.append(table_node)
    table_node = build_test_case_table(test_cases)
    if table_node:
        content.append(paragraph_node("Test cases:"))
        content.append(table_node)
    if not content:
        content.append(paragraph_node("Dettagli non forniti"))
    return {
        "type": "doc",
        "version": 1,
        "content": content,
    }


def build_test_case_table(
    test_cases: Optional[Sequence[Union[TestCase, Mapping[str, Any]]]],
) -> Optional[Dict[str, Any]]:
    if not test_cases:
        return None
    rows: List[Dict[str, Any]] = [
        {
            "type": "tableRow",
            "content": [
                table_header_cell("#"),
                table_header_cell("Titolo"),
                table_header_cell("Obiettivo"),
                table_header_cell("Passi"),
                table_header_cell("Risultato atteso"),
            ],
        }
    ]
    for idx, entry in enumerate(test_cases, start=1):
        title, objective, steps, expected = extract_test_case_fields(entry)
        rows.append(
            {
                "type": "tableRow",
                "content": [
                    table_cell_node(str(idx)),
                    table_cell_node(title),
                    table_cell_node(objective),
                    table_cell_node(steps),
                    table_cell_node(expected),
                ],
            }
        )
    if len(rows) == 1:
        return None
    return {"type": "table", "content": rows}


def build_pipe_table_node(
    table_lines: Sequence[str],
) -> Optional[Dict[str, Any]]:
    if not table_lines:
        return None

    def _split_line(line: str) -> List[str]:
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        return [part for part in parts if part]

    header_cells = _split_line(table_lines[0])
    if not header_cells:
        return None

    rows: List[Dict[str, Any]] = [
        {
            "type": "tableRow",
            "content": [table_header_cell(cell) for cell in header_cells],
        }
    ]

    for line in table_lines[1:]:
        cells = _split_line(line)
        if not cells:
            continue
        if all(set(cell) <= {"-", " "} for cell in cells):
            continue
        rows.append(
            {
                "type": "tableRow",
                "content": [table_cell_node(cell) for cell in cells],
            }
        )

    if len(rows) <= 1:
        return None
    return {"type": "table", "content": rows}


def extract_test_case_fields(
    entry: Union[TestCase, Mapping[str, Any]],
) -> tuple[str, str, str, str]:
    if isinstance(entry, Mapping):
        title = str(entry.get("title") or "").strip() or "Test case"
        objective = str(entry.get("objective") or "").strip()
        raw_steps = entry.get("steps", [])
        expected = str(entry.get("expected_result") or "").strip()
    else:
        title = getattr(entry, "title", "").strip() or "Test case"
        objective = getattr(entry, "objective", "").strip()
        raw_steps = getattr(entry, "steps", [])
        expected = getattr(entry, "expected_result", "").strip()
    if isinstance(raw_steps, Sequence) and not isinstance(raw_steps, (str, bytes)):
        steps_clean = [str(step).strip() for step in raw_steps if str(step).strip()]
    else:
        steps_clean = []
    steps = "; ".join(steps_clean)
    objective = objective or "—"
    steps = steps or "—"
    expected = expected or "—"
    return title, objective, steps, expected


def paragraphs_from_text(text: str) -> List[Dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    return [paragraph_node(line) for line in lines]


def paragraph_node(text: str) -> Dict[str, Any]:
    return {
        "type": "paragraph",
        "content": [
            {
                "type": "text",
                "text": text or "",
            }
        ],
    }


def table_cell_node(text: str) -> Dict[str, Any]:
    return {
        "type": "tableCell",
        "content": [paragraph_node(text or "—")],
    }


def table_header_cell(text: str) -> Dict[str, Any]:
    return {
        "type": "tableHeader",
        "content": [paragraph_node(text or "—")],
    }


__all__ = [
    "build_bdd_scenario_adf",
    "build_user_story_description",
    "build_test_case_table",
    "build_pipe_table_node",
    "extract_test_case_fields",
    "paragraphs_from_text",
    "paragraph_node",
    "table_cell_node",
    "table_header_cell",
]
