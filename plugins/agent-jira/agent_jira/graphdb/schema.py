import logging
import re
from typing import Any, Dict, List, Optional

from .inference import _flatten_strings, _infer_group_from_properties
from .styles import LABEL_PRIORITY

logger = logging.getLogger(__name__)

_JIRA_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
_DETERMINISTIC_KB_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]*-[0-9a-f]{6}$")
_KNOWN_TECH_IDS = {
    "salesforce",
    "jira",
    "pdq",
    "nsi",
    "redis",
    "oracle",
    "adabas",
    "marketing-cloud",
    "salesforce-service-cloud",
    "salesforce-marketing-cloud",
    "customer-space",
    "miles",
    "file-transfer-flussi-giornalieri",
}


def _get_id(node_obj: Any, prop_map: Dict[int, str] = None) -> Optional[str]:
    """Helper to reliably extract 'id' property from node in RedisGraph compact format."""
    # Handle object-based format (if client returns objects)
    if hasattr(node_obj, "properties") and "id" in node_obj.properties:
        return node_obj.properties["id"]
    if isinstance(node_obj, dict) and "id" in node_obj:
        return node_obj["id"]

    # Handle RedisGraph compact format: [node_type, [internal_id, [label_ids], [[prop_id, prop_type, prop_value], ...]]]
    if isinstance(node_obj, list) and len(node_obj) >= 2:
        node_data = node_obj[1]  # Get the node data part
        if isinstance(node_data, list) and len(node_data) >= 3:
            properties = node_data[2]  # Get properties array
            if isinstance(properties, list):
                # Properties are [[prop_id, prop_type, prop_value], ...]
                # We search for property name "id" using prop_map if available
                id_prop_idx = -1
                if prop_map:
                    for idx, name in prop_map.items():
                        if name == "id":
                            id_prop_idx = idx
                            break

                # Fallback: Property ID 0 is OFTEN the 'id' field, but dynamic mapping is safer
                target_idx = id_prop_idx if id_prop_idx != -1 else 0

                for prop in properties:
                    if isinstance(prop, list) and len(prop) >= 3:
                        prop_id, _, prop_value = prop[0], prop[1], prop[2]
                        if prop_id == target_idx:  # ID property
                            return prop_value

    return None


def _extract_properties(node_obj: Any, prop_map: Dict[int, str]) -> Dict[str, Any]:
    """Extract all properties from RedisGraph compact format node."""
    props = {}

    # Handle object-based format
    if hasattr(node_obj, "properties"):
        return node_obj.properties
    if isinstance(node_obj, dict):
        return node_obj

    # Handle RedisGraph compact format
    if isinstance(node_obj, list) and len(node_obj) >= 2:
        node_data = node_obj[1]
        if isinstance(node_data, list) and len(node_data) >= 3:
            properties = node_data[2]
            if isinstance(properties, list):
                for prop in properties:
                    if isinstance(prop, list) and len(prop) >= 3:
                        prop_id, _, prop_value = prop[0], prop[1], prop[2]
                        # Use dynamic mapping, or fallback to default map for backward compat or if mapping failed
                        prop_name = prop_map.get(prop_id)

                        # Fallback hardcoded map if header parsing failed
                        if not prop_name:
                            # EXPANDED PROP MAP from verification
                            prop_names_fallback = {
                                0: "id",
                                1: "name",  # General name/title
                                2: "type",
                                3: "path",
                                5: "label",  # Display label (e.g. Risk: ...) - maps to node label
                                12: "content",
                                20: "description",
                                25: "title",
                                34: "role",
                                36: "description",  # Risk description
                                37: "status",
                                38: "summary",
                                40: "description",
                                41: "benefit",
                                42: "priority",
                            }
                            prop_name = prop_names_fallback.get(
                                prop_id, f"prop_{prop_id}"
                            )

                        props[prop_name] = prop_value

    return props


def _extract_labels(node_obj: Any, label_map: Dict[int, str]) -> List[str]:
    """Extract labels from RedisGraph compact format node."""
    # Handle object-based format
    if hasattr(node_obj, "labels"):
        return node_obj.labels

    # Handle RedisGraph compact format: [node_type, [internal_id, [label_ids], ...]]
    if isinstance(node_obj, list) and len(node_obj) >= 2:
        node_data = node_obj[1]
        if isinstance(node_data, list) and len(node_data) >= 2:
            label_ids = node_data[1]
            if isinstance(label_ids, list):
                # FIXED: Merge dynamic map (if present) with Verified ID fallback
                # This ensures that even if label_map is partial, we don't get Label_5

                resolved_labels = []

                # Verified fallback map
                label_names_fallback = {
                    0: "Document",
                    1: "Story",  # Was UserStory, aliased to Story for UI consistency
                    2: "Epic",
                    3: "TestCase",
                    4: "Requirement",
                    5: "Topic",
                    6: "Analysis",
                    7: "KnowledgeBase",
                    8: "Stakeholder",
                    9: "Milestone",
                    10: "Technology",
                    11: "Risk",
                    12: "Story",
                    13: "JiraIssue",
                }

                for lid in label_ids:
                    l_val = None
                    # Try dynamic provided by header first
                    if label_map:
                        l_val = label_map.get(lid)

                    # If failed, try Verified fallback
                    if not l_val:
                        l_val = label_names_fallback.get(lid)

                    # Last resort
                    if not l_val:
                        l_val = f"Label_{lid}"

                    resolved_labels.append(l_val)

                return resolved_labels

    return []


def _extract_relationship_type(rel_obj: Any) -> str:
    """Extract relationship type from object or compact format."""
    if hasattr(rel_obj, "relation"):
        return str(rel_obj.relation)
    if isinstance(rel_obj, dict):
        return str(rel_obj.get("type") or rel_obj.get("relationship_type") or "RELATED")
    if isinstance(rel_obj, list) and len(rel_obj) > 1:
        return str(rel_obj[1])
    return "RELATED"


def _extract_relationship_properties(
    rel_obj: Any, prop_map: Dict[int, str]
) -> Dict[str, Any]:
    """Extract relationship properties from object or compact format."""
    if hasattr(rel_obj, "properties"):
        return rel_obj.properties
    if isinstance(rel_obj, dict):
        return rel_obj.get("properties", rel_obj)
    if isinstance(rel_obj, list) and len(rel_obj) >= 2:
        rel_data = rel_obj[1]
        if isinstance(rel_data, list) and len(rel_data) >= 4:
            properties = rel_data[3]
            if isinstance(properties, list):
                props: Dict[str, Any] = {}
                for prop in properties:
                    if isinstance(prop, list) and len(prop) >= 3:
                        prop_id, _, prop_value = prop[0], prop[1], prop[2]
                        prop_name = prop_map.get(prop_id, f"prop_{prop_id}")
                        props[prop_name] = prop_value
                return props
    return {}


def _process_node(
    node_obj: Any,
    nodes_map: Dict[str, Any],
    label_map: Dict[int, str],
    prop_map: Dict[int, str],
    is_center: bool = False,
) -> None:
    """Helper to parse node object and add to map."""
    node_id = _get_id(node_obj, prop_map)
    if not node_id:
        logger.warning("[_process_node] Could not extract ID from node_obj")
        return

    if node_id not in nodes_map:
        props = _extract_properties(node_obj, prop_map)
        labels = _extract_labels(node_obj, label_map)

        if labels:
            sorted_labels = sorted(
                labels, key=lambda label: LABEL_PRIORITY.get(label, 99)
            )
            group = sorted_labels[0]
        else:
            group = "Unknown"

        if group == "UserStory":
            group = "Story"

        inferred_group = _infer_group_from_properties(props)
        normalized_node_id = str(node_id).strip().lower()
        flattened_values = _flatten_strings(props)
        lowered_values = [value.lower() for value in flattened_values]

        if normalized_node_id.startswith("milestone-"):
            inferred_group = "Milestone"
        elif normalized_node_id.startswith("team-"):
            inferred_group = "Stakeholder"
        elif normalized_node_id in _KNOWN_TECH_IDS:
            inferred_group = "Technology"
        elif _JIRA_KEY_RE.fullmatch(str(node_id).strip()):
            if any(key in props for key in ("benefit", "priority", "role")):
                inferred_group = "Story"
            elif any(key in props for key in ("given", "when", "then")):
                inferred_group = "TestCase"
            elif any("/browse/" in value for value in lowered_values):
                inferred_group = "JiraIssue"
        elif (
            props.get("type") == "Generic"
            and str(props.get("description", "")).strip() == "Planned"
        ):
            inferred_group = "Milestone"

        if inferred_group and (
            group
            in {
                "Unknown",
                "Document",
                "Technology",
                "Stakeholder",
                "Milestone",
                "Risk",
                "JiraIssue",
            }
            or group.startswith("Label_")
            or inferred_group
            in {
                "Risk",
                "Story",
                "TestCase",
                "Epic",
                "Requirement",
                "JiraIssue",
                "Stakeholder",
                "Milestone",
                "Technology",
            }
        ):
            group = inferred_group

        label_text = node_id
        for key in (
            "label",
            "label_display",
            "name",
            "title",
            "summary",
            "description",
            "status",
        ):
            candidate = props.get(key)
            if isinstance(candidate, str) and candidate.strip():
                label_text = candidate
                break

        nodes_map[node_id] = {
            "id": node_id,
            "label": label_text,
            "group": group,
            "is_center": is_center,
            "properties": props,
        }
