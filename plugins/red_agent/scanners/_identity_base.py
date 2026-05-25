"""Shared helpers for identity scanners.

Every identity scanner walks the same pattern:

1. Refuse to run if the master toggle is off, the target type is wrong,
   or the intensity is below ``ACTIVE`` (none of these tools are safe
   to "preview" with passive traffic).
2. Resolve the operator-bound credential reference.
3. Hand a redacted argv to the sandbox runner. **No credentials must
   ever appear in argv** — we always pipe them through environment
   variables consumed by the tool's wrapper script (or stdin where
   the tool supports it). This avoids leaking secrets into ``ps``,
   docker run logs, and Sentry breadcrumbs.
4. Parse JSON / SQLite output into ``Finding`` records.

The helpers below cover the credential plumbing; per-tool argv and
parsing live in the concrete scanner modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.red_agent.models import ScanIntensity

if TYPE_CHECKING:
    from plugins.red_agent._credential_resolver import IdentityCredential


def passive_blocked(intensity: ScanIntensity) -> bool:
    """Identity tools require auth; passive runs are nonsensical."""

    return intensity == ScanIntensity.PASSIVE


def credentials_to_env(cred: "IdentityCredential") -> dict[str, str]:
    """Render an :class:`IdentityCredential` as the env-var contract
    consumed by every identity scanner image.

    The variable names are stable across the three built-ins so the
    ``SandboxRunner`` only has to know one mapping. Empty fields are
    intentionally omitted — leaving ``RA_PASSWORD=""`` set lets some
    tools fall through to anonymous bind, which we never want.
    """

    env: dict[str, str] = {}
    if cred.username:
        env["RA_USERNAME"] = cred.username
    if cred.password is not None:
        env["RA_PASSWORD"] = cred.password.get_secret_value()
    if cred.domain:
        env["RA_DOMAIN"] = cred.domain
    if cred.refresh_token is not None:
        env["RA_REFRESH_TOKEN"] = cred.refresh_token.get_secret_value()
    return env
