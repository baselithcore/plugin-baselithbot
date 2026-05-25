"""Runtime severity policy: parse settings overrides, apply per rule."""

from __future__ import annotations

from ...core.config import settings
from ...core.logging import log
from ...schemas.finding import Severity

_VALID: set[str] = {"FAIL", "WARN", "INFO", "PASS"}


def disabled_rules() -> set[str]:
    raw = (settings.builtin_disabled_rules or "").strip()
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip()}


def severity_overrides() -> dict[str, Severity]:
    raw = (settings.builtin_severity_overrides or "").strip()
    if not raw:
        return {}
    out: dict[str, Severity] = {}
    for pair in raw.split(","):
        if "=" not in pair:
            continue
        rid, sev = pair.split("=", 1)
        rid_s = rid.strip()
        sev_s = sev.strip().upper()
        if not rid_s or sev_s not in _VALID:
            log.warning(
                "builtin.severity_override.invalid", rule_id=rid_s, severity=sev_s
            )
            continue
        out[rid_s] = sev_s  # type: ignore[assignment]
    return out


def resolve_severity(rule_id: str, default: Severity) -> Severity:
    return severity_overrides().get(rule_id, default)


def is_enabled(rule_id: str) -> bool:
    return rule_id not in disabled_rules()
