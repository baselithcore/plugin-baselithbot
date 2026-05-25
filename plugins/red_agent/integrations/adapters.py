"""Provider-specific inbound webhook adapters.

Each adapter parses a vendor-shaped payload into the canonical dict
that :meth:`WebhookReceiver.parse_event` already understands::

    {
      "external_ref": "...",
      "state": "open|triaged|fixed|wontfix|accepted",
      "notes": "...",
      "assignee": "...",
      "actor": "..."
    }

Vendors covered:

* **Jira Cloud webhook** — ``jira:issue_updated`` event with the
  ``issue`` envelope.
* **ServiceNow** — Business Rule POST with the table-row dict
  (``number``, ``state``, ``work_notes``, ``assigned_to``).
* **Linear** — webhook with ``data`` envelope and ``state.type``.

Adapter authors stay free of any persistence / signature concerns —
those live in :class:`WebhookReceiver` and the router. An adapter that
returns ``None`` signals "not interested" so the router can answer
``200 OK`` without applying anything.
"""

from __future__ import annotations

from typing import Any, Protocol


class WebhookAdapter(Protocol):
    """Vendor parser contract."""

    name: str

    def parse(self, payload: dict[str, Any]) -> dict[str, Any] | None: ...


# --- Jira -----------------------------------------------------------

_JIRA_STATUS_TO_STATE: dict[str, str] = {
    "done": "fixed",
    "closed": "fixed",
    "resolved": "fixed",
    "in progress": "triaged",
    "in review": "triaged",
    "to do": "open",
    "open": "open",
    "wontfix": "wontfix",
    "won't fix": "wontfix",
    "cannot reproduce": "wontfix",
}


class JiraAdapter:
    name = "jira"

    def parse(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        issue = payload.get("issue")
        if not isinstance(issue, dict):
            return None
        key = issue.get("key")
        if not isinstance(key, str) or not key:
            return None
        fields = issue.get("fields") or {}
        if not isinstance(fields, dict):
            fields = {}
        status_obj = fields.get("status") or {}
        status_name = status_obj.get("name") if isinstance(status_obj, dict) else ""
        state = _JIRA_STATUS_TO_STATE.get(str(status_name or "").lower())
        assignee_obj = fields.get("assignee") or {}
        assignee = None
        if isinstance(assignee_obj, dict):
            assignee = (
                assignee_obj.get("emailAddress")
                or assignee_obj.get("displayName")
                or assignee_obj.get("accountId")
            )
        comment = payload.get("comment") or {}
        notes = comment.get("body") if isinstance(comment, dict) else None
        actor = (payload.get("user") or {}).get("displayName") or "jira"
        return {
            "external_ref": key,
            "state": state,
            "notes": notes if isinstance(notes, str) else None,
            "assignee": assignee if isinstance(assignee, str) else None,
            "actor": str(actor),
        }


# --- ServiceNow -----------------------------------------------------

# https://docs.servicenow.com/bundle/sandiego-application-development/page/script/server-scripting/concept/c_IncidentStateModel.html
_SERVICENOW_STATE: dict[str, str] = {
    "1": "open",  # New
    "2": "triaged",  # In Progress
    "3": "triaged",  # On Hold
    "6": "fixed",  # Resolved
    "7": "fixed",  # Closed
    "8": "wontfix",  # Cancelled
}


class ServiceNowAdapter:
    name = "servicenow"

    def parse(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        number = payload.get("number")
        if not isinstance(number, str) or not number:
            return None
        raw_state = payload.get("state")
        state_key = str(raw_state) if raw_state is not None else ""
        state = _SERVICENOW_STATE.get(state_key)
        notes = payload.get("work_notes") or payload.get("comments")
        assignee_obj = payload.get("assigned_to") or {}
        assignee = None
        if isinstance(assignee_obj, dict):
            assignee = (
                assignee_obj.get("display_value")
                or assignee_obj.get("user_name")
                or assignee_obj.get("email")
            )
        elif isinstance(assignee_obj, str):
            assignee = assignee_obj
        actor = payload.get("sys_updated_by") or "servicenow"
        return {
            "external_ref": number,
            "state": state,
            "notes": notes if isinstance(notes, str) else None,
            "assignee": assignee if isinstance(assignee, str) else None,
            "actor": str(actor),
        }


# --- Linear ---------------------------------------------------------

_LINEAR_TYPE_TO_STATE: dict[str, str] = {
    "completed": "fixed",
    "canceled": "wontfix",
    "cancelled": "wontfix",
    "started": "triaged",
    "unstarted": "open",
    "backlog": "open",
    "triage": "triaged",
}


class LinearAdapter:
    name = "linear"

    def parse(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        identifier = data.get("identifier") or data.get("id")
        if not isinstance(identifier, str) or not identifier:
            return None
        state_obj = data.get("state") or {}
        state_type = state_obj.get("type") if isinstance(state_obj, dict) else ""
        state = _LINEAR_TYPE_TO_STATE.get(str(state_type or "").lower())
        assignee_obj = data.get("assignee") or {}
        assignee = None
        if isinstance(assignee_obj, dict):
            assignee = (
                assignee_obj.get("email")
                or assignee_obj.get("name")
                or assignee_obj.get("displayName")
            )
        notes = data.get("description") or data.get("body")
        actor = (
            (payload.get("actor") or {}).get("name")
            if isinstance(payload.get("actor"), dict)
            else "linear"
        )
        return {
            "external_ref": identifier,
            "state": state,
            "notes": notes if isinstance(notes, str) else None,
            "assignee": assignee if isinstance(assignee, str) else None,
            "actor": str(actor or "linear"),
        }


# --- registry -------------------------------------------------------

_REGISTRY: dict[str, WebhookAdapter] = {
    "jira": JiraAdapter(),
    "servicenow": ServiceNowAdapter(),
    "linear": LinearAdapter(),
}


def get_adapter(name: str) -> WebhookAdapter | None:
    return _REGISTRY.get(name.lower())
