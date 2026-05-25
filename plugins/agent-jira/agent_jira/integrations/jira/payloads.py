from typing import Any, Dict, Mapping, Optional, Sequence, Union

from agent_jira.project_manager import TestCase

from .adf import build_user_story_description
from .utils import extract_kb_label, sanitize_priority


def build_user_story_payload(
    *,
    project_key: str,
    issue_type: str,
    title: str,
    description: str,
    acceptance_criteria: Sequence[str],
    business_value: Sequence[str],
    priority: Any,
    story_points: Optional[int],
    labels: Sequence[str],
    default_labels: Sequence[str],
    story_points_field: Optional[str],
    kb_label_field: Optional[str],
    test_cases: Optional[Sequence[Union[TestCase, Mapping[str, Any]]]],
    default_priority_name: str,
    priority_mapping: Mapping[str, str],
) -> Dict[str, Any]:
    labels_payload: list[str] = list(default_labels)
    labels_payload.extend(label for label in labels if label)
    deduped_labels = list(dict.fromkeys(labels_payload))

    priority_name = sanitize_priority(
        priority,
        default_priority_name=default_priority_name,
        priority_mapping=priority_mapping,
    )

    kb_label_value: Optional[str] = None
    effective_labels = deduped_labels
    if kb_label_field:
        kb_label_value = extract_kb_label(deduped_labels)
        if kb_label_value:
            # Manteniamo comunque la label in lista per consentire ricerche anche
            # quando il custom field non è valorizzato o in configurazioni miste.
            effective_labels = deduped_labels

    # Limitiamo il business value a massimo 3 punti per la descrizione Jira.
    business_value_for_description = list(business_value)[:3] if business_value else []

    payload: Dict[str, Any] = {
        "fields": {
            "project": {"key": project_key},
            "summary": title[:254],
            "issuetype": {"name": issue_type},
            "description": build_user_story_description(
                description=description,
                acceptance_criteria=[],  # evitiamo di replicare gli scenari/BDD dentro la US
                business_value=business_value_for_description,
                test_cases=None,  # gli scenari/test case sono creati come issue dedicate
            ),
            "priority": {"name": priority_name},
            "labels": effective_labels,
        }
    }
    if story_points is not None and story_points_field:
        payload["fields"][story_points_field] = story_points
    if kb_label_field and kb_label_value:
        payload["fields"][kb_label_field] = [kb_label_value]
    return payload


__all__ = ["build_user_story_payload"]
