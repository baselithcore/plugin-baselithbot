"""NIS2 incident-trail hooks for the auth plugin.

Bridges auth security events to the central :mod:`core.incidents` reporting
subsystem so they land in the NIS2 Art. 21(2)(b) incident-handling trail. Opt-in
and default-off: nothing is recorded unless ``INCIDENT_REPORTING_ENABLED`` is
set, so existing auth behaviour is unchanged. Every hook is best-effort — a
failure here must never affect the login flow.
"""

from __future__ import annotations

from typing import Optional

from core.config.incidents import get_incident_config
from core.incidents import IncidentSeverity, get_incident_service
from core.observability.logging import get_logger

logger = get_logger(__name__)


async def report_account_lockout(
    user_id: str, attempts: int, *, source_ip: Optional[str] = None
) -> None:
    """Record an account-lockout event (repeated failed logins) in the trail.

    A single lockout is logged as a *non-significant* incident: it belongs to the
    incident-handling trail (Art. 21(2)(b)), not the 24h/72h regulatory reporting
    clock (Art. 23) — so it carries no reporting deadlines. No-op unless incident
    reporting is enabled.

    Args:
        user_id: The locked-out account's id.
        attempts: Consecutive failed-login count that triggered the lockout.
        source_ip: Best-effort client IP (may be ``None`` / spoofable).
    """
    try:
        if not get_incident_config().enabled:
            return
        await get_incident_service().open_incident(
            title="Account lockout after repeated failed logins",
            severity=IncidentSeverity.MEDIUM,
            significant=False,
            description=(
                f"Account {user_id} was locked after {attempts} consecutive "
                "failed login attempts."
            ),
            affected_systems=["auth"],
            affected_subjects=1,
            details={
                "event": "account_lockout",
                "user_id": user_id,
                "failed_attempts": attempts,
                "source_ip": source_ip,
            },
        )
    except Exception as exc:  # noqa: BLE001 — incident trail must never break login
        logger.warning("auth lockout incident not recorded: %s", exc)


__all__ = ["report_account_lockout"]
