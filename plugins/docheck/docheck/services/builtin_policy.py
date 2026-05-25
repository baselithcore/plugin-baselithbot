"""Synthetic exposure of DocCheck_Builtin as a read-only system policy.

Built-in deterministic rules live in `agents/technical/rules/` (no DB rows).
This module surfaces them via the same shape `services.policies` returns,
so the policies endpoint is the single source of truth for the UI.
"""

from __future__ import annotations

from typing import Any

from ..agents.technical._base import POLICY_ID, POLICY_VERSION
from ..agents.technical.rules import all_rules
from ..agents.technical.severity import disabled_rules, severity_overrides

BUILTIN_POLICY_ID: str = POLICY_ID
BUILTIN_POLICY_VERSION: str = POLICY_VERSION


def is_system_policy(pid: str) -> bool:
    return pid == BUILTIN_POLICY_ID


def policy_entry() -> dict[str, Any]:
    """Synthetic PolicyOut row for the system policy."""
    rules = all_rules()
    enabled = [r for r in rules if r.spec.rule_id not in disabled_rules()]
    return {
        "id": BUILTIN_POLICY_ID,
        "version": BUILTIN_POLICY_VERSION,
        "title": "doCheck Built-in (deterministic baseline)",
        "scope": "global_default",
        "lang": "it",
        "active": True,
        "rule_count": len(enabled),
        "system": True,
    }


def rule_entries() -> list[dict[str, Any]]:
    """Synthetic RuleOut rows derived from the rule registry."""
    overrides = severity_overrides()
    disabled = disabled_rules()
    out: list[dict[str, Any]] = []
    for r in all_rules():
        rid = r.spec.rule_id
        sev = overrides.get(rid, r.spec.default_severity)
        out.append(
            {
                "id": rid,
                "policy_id": BUILTIN_POLICY_ID,
                "policy_version": BUILTIN_POLICY_VERSION,
                "rule_type": "format",
                "severity": sev.lower(),
                "excerpt": r.spec.excerpt,
                "matcher": None,
                "system": True,
                "enabled": rid not in disabled,
                "title": r.spec.title,
                "default_confidence": r.spec.default_confidence,
            }
        )
    return out
