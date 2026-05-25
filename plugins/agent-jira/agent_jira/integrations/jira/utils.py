import re
from typing import Any, Mapping, Optional, Sequence

import httpx

from agent_jira.kb_labels import is_canonical_document_label, is_supported_document_label

_DETERMINISTIC_KB_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]*-[0-9a-f]{6}$")


def sanitize_priority(
    priority: Any,
    *,
    default_priority_name: str,
    priority_mapping: Mapping[str, str],
) -> str:
    raw_value = coerce_priority_value(priority)
    if not raw_value:
        return default_priority_name
    normalized = raw_value.lower()
    mapped = priority_mapping.get(normalized)
    return mapped or raw_value


def coerce_priority_value(priority: Any) -> str:
    if isinstance(priority, str):
        return priority.strip()
    if isinstance(priority, Mapping):
        for key in ("name", "value", "label"):
            value = priority.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(priority, Sequence) and not isinstance(priority, (str, bytes)):
        for item in priority:
            name = coerce_priority_value(item)
            if name:
                return name
    if priority is not None:
        text = str(priority).strip()
        if text:
            return text
    return ""


def coerce_http_error_message(exc: httpx.HTTPStatusError) -> str:
    response = exc.response
    if response is None:
        return str(exc)
    try:
        return response.text.strip() or str(exc)
    except Exception:
        return str(exc)


def extract_error_detail(response: Optional[httpx.Response]) -> str:
    if response is None:
        return ""
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()

    parts = []
    error_messages = payload.get("errorMessages") or []
    parts.extend(error_messages)
    field_errors = payload.get("errors") or {}
    parts.extend(f"{field}: {message}" for field, message in field_errors.items())
    if not parts:
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            parts.append(message.strip())
    if not parts:
        parts.append(str(payload))
    return "; ".join(filter(None, parts))


def extract_kb_label(labels: Sequence[str]) -> Optional[str]:
    fallback_match: Optional[str] = None
    for label in labels:
        if not isinstance(label, str):
            continue
        candidate = label.strip()
        normalized = candidate.lower()
        if candidate and is_canonical_document_label(candidate):
            return candidate
        if candidate and (
            normalized.startswith(("knowledge-base-", "kb-"))
            or is_supported_document_label(candidate)
            or bool(_DETERMINISTIC_KB_LABEL_RE.fullmatch(normalized))
        ):
            fallback_match = fallback_match or candidate
    return fallback_match


def build_kb_label_clause(label: str, kb_label_field: Optional[str]) -> str:
    if not kb_label_field:
        return f'labels = "{label}"'
    field_name = kb_label_field
    field_identifier = None
    cf_identifier = None
    if field_name.startswith("customfield_"):
        field_identifier = field_name
        cf_id = field_name.replace("customfield_", "")
        if cf_id.isdigit():
            cf_identifier = f"cf[{cf_id}]"
    else:
        field_identifier = f'"{field_name}"'
    parts = [f'labels = "{label}"']
    if field_identifier:
        parts.append(f'{field_identifier} = "{label}"')
    if cf_identifier:
        parts.append(f'{cf_identifier} = "{label}"')
    return "(" + " OR ".join(parts) + ")"


__all__ = [
    "sanitize_priority",
    "coerce_priority_value",
    "coerce_http_error_message",
    "extract_error_detail",
    "extract_kb_label",
    "build_kb_label_clause",
]
