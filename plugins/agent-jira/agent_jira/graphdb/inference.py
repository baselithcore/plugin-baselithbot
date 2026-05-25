import re
from typing import Any, Dict, List, Optional

_DETERMINISTIC_KB_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]*-[0-9a-f]{6}$")


def _flatten_strings(value: Any) -> List[str]:
    """Flatten nested lists/dicts and return all string leaves."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        flattened: List[str] = []
        for nested in value.values():
            flattened.extend(_flatten_strings(nested))
        return flattened
    if isinstance(value, list):
        flattened = []
        for nested in value:
            flattened.extend(_flatten_strings(nested))
        return flattened
    return []


def _infer_group_from_properties(props: Dict[str, Any]) -> Optional[str]:
    """Infer node group from stable display/property signatures."""
    if not props:
        return None

    string_values = _flatten_strings(props)
    for val in string_values:
        if val.startswith("Risk:"):
            return "Risk"
        if val.startswith("Story:"):
            return "Story"
        if val.startswith("Epic:"):
            return "Epic"
        if val.startswith("Requirement:"):
            return "Requirement"
        if (
            val.startswith("Test ")
            or val.startswith("Test:")
            or val.startswith("Test (")
        ):
            return "TestCase"
        if val.startswith("Ticket"):
            return "JiraIssue"

    lowered_values = [val.lower() for val in string_values]
    if "severity" in props or any(text.startswith("risk:") for text in lowered_values):
        return "Risk"
    if "fingerprint" in props or "chunk_ids" in props:
        return "Document"

    path_val = str(props.get("path", ""))
    if path_val.endswith((".md", ".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx")):
        return "Document"
    if "email" in props and "role" in props:
        return "Stakeholder"
    if "target_date" in props:
        return "Milestone"
    if "version" in props and "category" in props:
        return "Technology"

    return None


def _extract_kb_labels_from_props(props: Dict[str, Any]) -> List[str]:
    labels: List[str] = []
    for value in props.values():
        for text in _flatten_strings(value):
            normalized = text.strip().lower()
            if _DETERMINISTIC_KB_LABEL_RE.fullmatch(normalized):
                labels.append(normalized)
    return list(dict.fromkeys(labels))


def _should_include_neighbor(
    center_node: Dict[str, Any], neighbor_node: Dict[str, Any]
) -> bool:
    center_group = center_node.get("group")
    neighbor_group = neighbor_node.get("group")
    if center_group not in {"Document", "KnowledgeBase", "Analysis"}:
        return True
    if neighbor_group not in {"Story", "TestCase", "JiraIssue"}:
        return True

    center_id = str(center_node.get("id", "")).strip().lower()
    neighbor_props = neighbor_node.get("properties") or {}
    kb_labels = _extract_kb_labels_from_props(neighbor_props)
    if not kb_labels:
        return True
    return center_id in kb_labels
