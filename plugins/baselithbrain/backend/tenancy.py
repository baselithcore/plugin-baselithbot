"""Per-tenant vault scoping for BaselithBrain.

Resolves the on-disk vault root for the *current request's* tenant, honouring the
plugin's manifest-declared tenancy and any runtime admin override through the
core seam (``core.context``). The default / unbound scope maps to the bare vault
root, so existing single-vault deployments, anonymous requests, and background
tasks are byte-for-byte unchanged — only an authenticated request under a
per-user (``personal``) scope gets its own sub-directory.
"""

from __future__ import annotations

from pathlib import Path

from core.context import resolve_plugin_tenancy_mode, resolve_plugin_tenant

#: Must equal the plugin directory / manifest ``name`` so a runtime override set
#: from the auth console keys to this plugin.
PLUGIN_NAME = "baselithbrain"

#: Manifest-declared tenancy (kept in sync with ``manifest.yaml``). ``personal``
#: → a private vault per user; an admin may override to ``shared`` at runtime.
DECLARED_TENANCY = "personal"


def tenant_scope_key() -> str:
    """Effective scope key for the current request (honours runtime override)."""
    mode = resolve_plugin_tenancy_mode(PLUGIN_NAME, DECLARED_TENANCY)
    return resolve_plugin_tenant(mode)


def scoped_vault_root(base: Path) -> Path:
    """Vault root for the current scope under ``base``.

    The unbound / deployment-default scope (``"default"``) maps to ``base``
    itself — preserving the historical single-vault layout and keeping anonymous
    and background access unchanged. Any concrete tenant/user key gets a
    sanitised sub-directory ``base/<key>`` (1 user = 1 vault under ``personal``).
    """
    key = tenant_scope_key()
    if not key or key == "default":
        return base
    safe = key.replace("/", "_").replace("\\", "_").replace("..", "_")
    return base / safe


__all__ = ["PLUGIN_NAME", "DECLARED_TENANCY", "tenant_scope_key", "scoped_vault_root"]
