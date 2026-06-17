"""
Shared audit helpers for BaselithMed routers.

Kept in a dedicated module so router.py and router_scores.py can both
import _append_audit without creating a circular dependency.
"""

from __future__ import annotations

from typing import Any

from .audit import AuditEventType
from .safety.phi import redact_dict


def _append_audit(
    plugin_instance: Any,
    *,
    event_type: AuditEventType,
    session_id: str,
    actor: str,
    payload: Any,
    summary: dict[str, Any],
) -> None:
    """Best-effort audit append. Never raises into the response path.

    Summaries are PHI-redacted before persistence so the durable ledger
    cannot leak Italian Codice Fiscale / phone / email / DOB even when
    the upstream caller forgot to scrub them.
    """
    ledger = getattr(plugin_instance, "audit_ledger", None)
    if ledger is None:
        return
    try:
        clean_summary = redact_dict(summary)
        if not isinstance(clean_summary, dict):
            clean_summary = summary
        ledger.append(
            event_type=event_type,
            session_id=session_id,
            actor=actor,
            payload=payload,
            summary=clean_summary,
        )
    except Exception:  # noqa: BLE001 — audit must never break the request
        pass
