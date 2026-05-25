from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from agent_jira.project_manager import UserStory


def slugify(value: str, fallback: str = "project-plan") -> str:
    text = value.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or fallback


def safe_sequence(raw: Any) -> list[str]:
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def jira_link_for_story(
    story: UserStory, jira_results: Sequence[Mapping[str, Any]]
) -> str:
    title = getattr(story, "title", "") or ""
    key = getattr(story, "jira_issue_key", None)
    if key:
        url = next(
            (entry.get("url") for entry in jira_results if entry.get("key") == key),
            None,
        )
        if url:
            return f"[{key}]({url})"
        return key
    match = next(
        (
            entry
            for entry in jira_results
            if entry.get("summary") == title and entry.get("key")
        ),
        None,
    )
    if match and match.get("key"):
        url = match.get("url")
        return f"[{match['key']}]({url})" if url else str(match["key"])
    return "—"


__all__ = ["slugify", "safe_sequence", "jira_link_for_story"]
