from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Mapping, Sequence

from agent_jira.llm import generate_response
from agent_jira.project_manager import TestCase
from agent_jira.config import OLLAMA_MODEL

if TYPE_CHECKING:
    from agent_jira.project_manager import ProjectPlan

logger = logging.getLogger(__name__)

TEST_CASE_SYSTEM_PROMPT = (
    "Sei un QA Lead esperto incaricato di progettare casi di test manuali "
    "utilizzabili come issue Jira dedicate. Devi usare uno stile tecnico, "
    "essere sintetico ma completo e mantenere tutte le informazioni in italiano."
)

TEST_CASE_RESPONSE_TEMPLATE = """{
  "stories": [
    {
      "title": "Titolo esatto della user story fornita",
      "test_cases": [
        {
          "title": "TC-<numero> Nome sintetico",
          "objective": "Obiettivo misurabile del test",
          "preconditions": ["precondizione 1", "precondizione 2"],
          "test_data": ["dati o configurazioni da preparare"],
          "steps": ["1. Azione descritta", "2. Azione successiva"],
          "expected_result": "Risultato osservabile e verificabile",
          "priority": "High|Medium|Low",
          "labels": ["test-case", "qa"],
          "jira_issue_type": "Test Case"
        }
      ]
    }
  ]
}"""


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


class TestCaseGenerator:
    """Genera casi di test strutturati partendo da un piano già analizzato."""

    def __init__(
        self,
        *,
        model: str = OLLAMA_MODEL,
        max_cases_per_story: int = 2,
        system_prompt: str = TEST_CASE_SYSTEM_PROMPT,
        response_template: str = TEST_CASE_RESPONSE_TEMPLATE,
    ) -> None:
        self.model = model
        self.max_cases_per_story = max(1, max_cases_per_story)
        self.system_prompt = system_prompt.strip()
        self.response_template = response_template.strip()

    def generate_for_plan(
        self,
        *,
        plan: "ProjectPlan",
        query: str,
        context: str = "",
        history_text: str = "",
    ) -> Dict[str, Sequence[TestCase]]:
        if not getattr(plan, "user_stories", None):
            return {}

        prompt = self._build_prompt(
            plan=plan,
            query=query,
            context=context,
            history_text=history_text,
        )
        try:
            raw_result = generate_response(prompt, model=self.model)
        except Exception:
            logger.exception("Impossibile generare i casi di test: errore LLM")
            return {}

        payload = self._parse_payload(raw_result)
        if not payload:
            logger.warning("Test case generator ha prodotto un output non valido.")
            return {}
        return self._extract_test_cases(payload)

    def _build_prompt(
        self,
        *,
        plan: "ProjectPlan",
        query: str,
        context: str,
        history_text: str,
    ) -> str:
        history_block = ""
        if history_text.strip():
            history_block = (
                f"### Conversazione precedente utile\n{history_text.strip()}\n\n"
            )

        requirements_block = "- Nessun requisito definito"
        if getattr(plan, "key_requirements", None):
            filtered = [req for req in plan.key_requirements if _clean_text(req)]
            if filtered:
                requirements_block = "\n".join(f"- {req}" for req in filtered if req)

        story_blocks: list[str] = []
        for idx, story in enumerate(plan.user_stories, start=1):
            acceptance = "- Nessun criterio di accettazione"
            if getattr(story, "acceptance_criteria", None):
                filtered_criteria = [
                    criterion
                    for criterion in story.acceptance_criteria
                    if _clean_text(criterion)
                ]
                if filtered_criteria:
                    acceptance = "\n".join(
                        f"- {criterion}" for criterion in filtered_criteria
                    )
            story_blocks.append(
                "\n".join(
                    [
                        f"### User story #{idx}",
                        f"Titolo: {story.title}",
                        f"Descrizione: {story.description}",
                        f"Priorità dichiarata: {story.priority or 'TBD'}",
                        f"Story points stimati: {story.story_points or 'TBD'}",
                        "Acceptance criteria:",
                        acceptance,
                    ]
                )
            )

        stories_block = (
            "\n\n".join(story_blocks) if story_blocks else "Nessuna user story fornita"
        )

        guidelines = [
            f"- Genera al massimo {self.max_cases_per_story} test case per ciascuna user story, coprendo i percorsi critici.",
            "- Il campo `title` di ogni blocco deve coincidere con il titolo della user story fornita per consentire il matching automatico.",
            "- Ogni caso di test deve avere precondizioni, dati, passi numerati e risultato atteso ben definito.",
            "- I passi devono iniziare con un verbo all'infinito e descrivere sia l'azione sia l'output atteso.",
            '- Imposta `jira_issue_type` sempre su "Test Case" e includi almeno le label `test-case` e `qa`.',
            "- Scrivi sempre in italiano professionale e non introdurre user story nuove o modificate.",
        ]
        guidelines_block = "\n".join(guidelines)

        context_summary = _clean_text(plan.functional_summary) or "Non disponibile"
        context_preview = _clean_text(context)
        if context_preview and len(context_preview) > 1200:
            context_preview = f"{context_preview[:1200]}..."

        return (
            f"{self.system_prompt}\n\n"
            f"### Template JSON da rispettare\n{self.response_template}\n\n"
            f"### Regole specifiche\n{guidelines_block}\n\n"
            f"### Sintesi del contesto\n"
            f"- Richiesta dell'utente: {query.strip() or 'Non disponibile'}\n"
            f"- Riassunto funzionale: {context_summary}\n"
            f"- Estratto tecnico (max 1200 caratteri): {context_preview or 'Non disponibile'}\n"
            f"- Requisiti chiave:\n{requirements_block}\n\n"
            f"{history_block}### User stories approvate\n"
            f"{stories_block}\n"
        )

    def _parse_payload(self, raw_result: str) -> Dict[str, Any]:
        candidate = (raw_result or "").strip()
        if not candidate:
            return {}
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if 0 <= start < end:
                snippet = candidate[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    logger.debug("Parsing JSON test case fallito: %s", snippet)
        return {}

    def _extract_test_cases(
        self, payload: Mapping[str, Any]
    ) -> Dict[str, Sequence[TestCase]]:
        stories_payload = payload.get("stories", [])
        if not isinstance(stories_payload, Sequence):
            return {}
        results: Dict[str, list[TestCase]] = {}
        for entry in stories_payload:
            if not isinstance(entry, Mapping):
                continue
            story_title = _clean_text(entry.get("title"))
            if not story_title:
                continue
            key = story_title.lower()
            raw_cases = entry.get("test_cases") or []
            if not isinstance(raw_cases, Sequence):
                continue
            parsed_cases: list[TestCase] = []
            for case_payload in list(raw_cases)[: self.max_cases_per_story]:
                if not isinstance(case_payload, Mapping):
                    continue
                test_case = TestCase.from_payload(case_payload)
                normalized_labels = [label.lower() for label in test_case.labels]
                if "test-case" not in normalized_labels:
                    test_case.labels = list(test_case.labels) + ["test-case"]
                if "qa" not in normalized_labels:
                    test_case.labels = list(test_case.labels) + ["qa"]
                parsed_cases.append(test_case)
            if parsed_cases:
                results[key] = parsed_cases
        return results


__all__ = [
    "TestCaseGenerator",
    "TEST_CASE_SYSTEM_PROMPT",
    "TEST_CASE_RESPONSE_TEMPLATE",
]
