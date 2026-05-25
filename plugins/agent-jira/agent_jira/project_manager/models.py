from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass
class Scenario:
    """Rappresenta uno scenario BDD/Gherkin per una user story."""

    title: str
    given: Sequence[str] = field(default_factory=list)
    when: Sequence[str] = field(default_factory=list)
    then: Sequence[str] = field(default_factory=list)
    scenario_id: str = ""
    priority: str = "Medium"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Scenario":
        def _collect_sequence(field_name: str) -> list[str]:
            raw_values = payload.get(field_name, [])
            if not isinstance(raw_values, Sequence) or isinstance(
                raw_values, (str, bytes)
            ):
                return []
            return [_clean_text(item) for item in raw_values if _clean_text(item)]

        scenario_id = _clean_text(payload.get("id") or payload.get("scenario_id"))
        priority = _clean_text(payload.get("priority")) or "Medium"
        return cls(
            title=_clean_text(payload.get("title")) or "Scenario",
            given=_collect_sequence("given"),
            when=_collect_sequence("when"),
            then=_collect_sequence("then"),
            scenario_id=scenario_id,
            priority=priority,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.scenario_id,
            "title": self.title,
            "given": list(self.given),
            "when": list(self.when),
            "then": list(self.then),
            "priority": self.priority,
        }


@dataclass
class TestCase:
    """Rappresenta un caso di test collegato a una user story."""

    title: str
    objective: str = ""
    preconditions: Sequence[str] = field(default_factory=list)
    test_data: Sequence[str] = field(default_factory=list)
    steps: Sequence[str] = field(default_factory=list)
    expected_result: str = ""
    priority: str = "Medium"
    labels: Sequence[str] = field(default_factory=list)
    jira_issue_type: str = "Test Case"
    jira_issue_key: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "TestCase":
        def _collect_sequence(
            field_name: str, default: Optional[Sequence[Any]] = None
        ) -> list[str]:
            raw_values = payload.get(field_name, default or [])
            if not isinstance(raw_values, Sequence) or isinstance(
                raw_values, (str, bytes)
            ):
                return []
            return [_clean_text(item) for item in raw_values if _clean_text(item)]

        preconditions = _collect_sequence("preconditions")
        test_data = _collect_sequence("test_data")
        steps = _collect_sequence("steps")
        labels = _collect_sequence("labels")
        return cls(
            title=_clean_text(payload.get("title")) or "Test case",
            objective=_clean_text(payload.get("objective")) or "",
            preconditions=preconditions,
            test_data=test_data,
            steps=steps,
            expected_result=_clean_text(payload.get("expected_result")) or "",
            priority=_clean_text(payload.get("priority")) or "Medium",
            labels=labels or ["test-case", "qa"],
            jira_issue_type=_clean_text(payload.get("jira_issue_type")) or "Test Case",
            jira_issue_key=_clean_text(payload.get("jira_issue_key")) or None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "objective": self.objective,
            "preconditions": list(self.preconditions),
            "test_data": list(self.test_data),
            "steps": list(self.steps),
            "expected_result": self.expected_result,
            "priority": self.priority,
            "labels": list(self.labels),
            "jira_issue_type": self.jira_issue_type,
            "jira_issue_key": self.jira_issue_key,
        }


@dataclass
class Requirement:
    """Rappresenta un requisito strutturato con ID e testo."""

    req_id: str
    text: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Requirement":
        return cls(
            req_id=_clean_text(payload.get("id")) or "REQ_UNKNOWN",
            text=_clean_text(payload.get("text")) or "",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.req_id, "text": self.text}


@dataclass
class UserStory:
    """User story con struttura BDD e scenari Gherkin."""

    title: str
    role: str
    goal: str
    benefit: str
    business_value: Sequence[str] = field(default_factory=list)
    scenarios: Sequence[Scenario] = field(default_factory=list)
    priority: str = "Should"
    story_points: Optional[int] = None
    labels: Sequence[str] = field(default_factory=list)
    jira_issue_key: Optional[str] = None
    jira_project_key: Optional[str] = None
    test_cases: Sequence[TestCase] = field(default_factory=list)
    satisfied_requirements: Sequence[str] = field(default_factory=list)
    _acceptance: Sequence[str] = field(default_factory=list, repr=False)
    _description: Optional[str] = field(default=None, repr=False)

    @property
    def description(self) -> str:
        if self._description:
            return self._description
        return f"Come {self.role}\nvoglio {self.goal}\ncosì da {self.benefit}."

    @property
    def acceptance_criteria(self) -> Sequence[str]:
        if not self.scenarios:
            return list(self._acceptance)

        criteria: list[str] = []
        for idx, scenario in enumerate(self.scenarios, 1):
            scenario_id = scenario.scenario_id or f"SCENARIO_{idx:02d}"
            label_line = f"{scenario_id} – {scenario.title}"
            rows: list[str] = []
            step_idx = 1

            for i, item in enumerate(scenario.given):
                tag = "Given" if i == 0 else "And"
                rows.append(f"| {step_idx} | `{tag}` | {item} |")
                step_idx += 1
            for i, item in enumerate(scenario.when):
                tag = "When" if i == 0 else "And"
                rows.append(f"| {step_idx} | `{tag}` | {item} |")
                step_idx += 1
            for i, item in enumerate(scenario.then):
                tag = "Then" if i == 0 else "And"
                rows.append(f"| {step_idx} | `{tag}` | {item} |")
                step_idx += 1

            table = "\n".join(
                [
                    "| # | Tag | Descrizione |",
                    "| - | --- | ----------- |",
                    *rows,
                ]
            )
            criteria.append("\n".join([label_line, table]))
        return criteria

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "UserStory":
        labels = [
            _clean_text(item) for item in payload.get("labels", []) if _clean_text(item)
        ]
        business_value = [
            _clean_text(item)
            for item in payload.get("business_value", []) or []
            if _clean_text(item)
        ]
        satisfied_requirements = [
            _clean_text(item)
            for item in payload.get("satisfied_requirements", [])
            if _clean_text(item)
        ]
        test_cases_payload = payload.get("test_cases", [])
        test_cases: list[TestCase] = []
        if isinstance(test_cases_payload, Sequence):
            for entry in test_cases_payload:
                if isinstance(entry, Mapping):
                    test_cases.append(TestCase.from_payload(entry))

        scenarios_payload = payload.get("bdd_scenarios", payload.get("scenarios", []))
        scenarios: list[Scenario] = []
        if isinstance(scenarios_payload, Sequence):
            for entry in scenarios_payload:
                if isinstance(entry, Mapping):
                    scenarios.append(Scenario.from_payload(entry))
        for idx, scenario in enumerate(scenarios, 1):
            if not scenario.scenario_id:
                scenario.scenario_id = f"SCENARIO_{idx:02d}"

        acceptance_raw = [
            _clean_text(item)
            for item in payload.get("acceptance_criteria", [])
            if _clean_text(item)
        ]
        business_value_raw = [
            _clean_text(item)
            for item in payload.get("business_value", [])
            if _clean_text(item)
        ]

        description_override = _clean_text(payload.get("description"))
        role = _clean_text(payload.get("role")) or "Utente"
        goal = _clean_text(payload.get("goal")) or "raggiungere un obiettivo"
        benefit = _clean_text(payload.get("benefit")) or "ottenere valore"
        business_value = cls._ensure_business_value(
            business_value_raw, benefit=benefit, goal=goal, role=role
        )

        return cls(
            title=_clean_text(payload.get("title")) or "User story",
            role=role,
            goal=goal,
            benefit=benefit,
            business_value=business_value,
            scenarios=scenarios,
            priority=_clean_text(payload.get("priority")) or "Should",
            story_points=_safe_int(payload.get("story_points")),
            labels=labels,
            jira_issue_key=_clean_text(payload.get("jira_issue_key")) or None,
            jira_project_key=_clean_text(payload.get("jira_project_key")) or None,
            test_cases=test_cases,
            satisfied_requirements=satisfied_requirements,
            _acceptance=acceptance_raw,
            _description=description_override or None,
        )

    def to_dict(self) -> Dict[str, Any]:
        for idx, scenario in enumerate(self.scenarios, 1):
            if not scenario.scenario_id:
                scenario.scenario_id = f"SCENARIO_{idx:02d}"
        return {
            "title": self.title,
            "role": self.role,
            "goal": self.goal,
            "benefit": self.benefit,
            "business_value": list(self.business_value),
            "description": self.description,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "acceptance_criteria": list(self.acceptance_criteria),
            "priority": self.priority,
            "story_points": self.story_points,
            "labels": list(self.labels),
            "jira_issue_key": self.jira_issue_key,
            "jira_project_key": self.jira_project_key,
            "test_cases": [test_case.to_dict() for test_case in self.test_cases],
            "satisfied_requirements": list(self.satisfied_requirements),
        }

    @staticmethod
    def _ensure_business_value(
        items: Sequence[str], *, benefit: str, goal: str, role: str
    ) -> list[str]:
        values = [item for item in items if item]
        if not values and benefit:
            for part in benefit.replace(";", ".").split("."):
                clean = _clean_text(part)
                if clean:
                    values.append(clean)
        if goal and goal not in values:
            values.append(goal)
        if role and role not in values:
            values.append(f"Per {role}")
        while len(values) < 3 and values:
            values.append(values[-1])
        if not values:
            values = ["Valore da definire", "Valore da definire", "Valore da definire"]
        return values


@dataclass
class ProjectPlan:
    """Risultato strutturato dell'analisi agile del documento."""

    functional_summary: str
    key_requirements: Sequence[str] = field(default_factory=list)
    structured_requirements: Sequence[Requirement] = field(default_factory=list)
    user_stories: Sequence[UserStory] = field(default_factory=list)
    risks: Sequence[str] = field(default_factory=list)
    open_questions: Sequence[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ProjectPlan":
        requirements = [
            _clean_text(item)
            for item in payload.get("key_requirements", [])
            if _clean_text(item)
        ]

        structured_reqs = []
        raw_structured = payload.get("structured_requirements", [])
        if isinstance(raw_structured, Sequence):
            for entry in raw_structured:
                if isinstance(entry, Mapping):
                    structured_reqs.append(Requirement.from_payload(entry))

        risks = [
            _clean_text(item) for item in payload.get("risks", []) if _clean_text(item)
        ]
        open_questions = [
            _clean_text(item)
            for item in payload.get("open_questions", [])
            if _clean_text(item)
        ]
        user_stories_payload = payload.get("user_stories", [])
        user_stories: list[UserStory] = []
        if isinstance(user_stories_payload, Sequence):
            for entry in user_stories_payload:
                if isinstance(entry, Mapping):
                    user_stories.append(UserStory.from_payload(entry))

        return cls(
            functional_summary=_clean_text(payload.get("functional_summary")),
            key_requirements=requirements,
            structured_requirements=structured_reqs,
            user_stories=user_stories,
            risks=risks,
            open_questions=open_questions,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "functional_summary": self.functional_summary,
            "key_requirements": list(self.key_requirements),
            "structured_requirements": [
                req.to_dict() for req in self.structured_requirements
            ],
            "user_stories": [story.to_dict() for story in self.user_stories],
            "risks": list(self.risks),
            "open_questions": list(self.open_questions),
        }
