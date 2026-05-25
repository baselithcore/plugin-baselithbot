"""Identity attack-surface configuration mixin.

Identity scanners enumerate Active Directory and Entra ID. Unlike
unauthenticated DAST/recon, every tool in this family requires
credentials to talk to a domain controller, an LDAP endpoint, or
the Microsoft Graph API. Three properties follow:

1. **Off by default.** Real DC traffic with valid creds is the most
   blue-team-detectable thing the Red Agent does. Operators must opt
   in per engagement.
2. **Credentials live in a vault.** The plugin never accepts cleartext
   creds in the scan request body. Each scan references a
   ``credentials_ref`` key resolved at run-time by the credential
   resolver (see ``_credential_resolver.py``). For development,
   ``Target.metadata['credentials']`` is honoured as a fallback.
3. **Read-only by default.** Tools run in collection mode; payloads
   that mutate (e.g. Certipy ``account create``) are gated behind a
   separate ``allow_mutating`` flag and INTRUSIVE intensity.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class _IdentityConfig(BaseModel):
    identity_enabled: bool = Field(
        default=False,
        description=(
            "Master toggle for identity scanners (BloodHound, Certipy, "
            "ROADrecon). When false, all three refuse to run."
        ),
    )
    identity_allow_mutating_actions: bool = Field(
        default=False,
        description=(
            "When true, identity scanners may invoke sub-commands that "
            "modify directory state (e.g. Certipy account/template "
            "creation). Requires INTRUSIVE intensity and an explicit "
            "engagement-level grant. Off by default."
        ),
    )
    identity_credentials_backend: str = Field(
        default="metadata",
        description=(
            "Where the resolver looks up credentials for a scan. "
            "``metadata`` reads from ``Target.metadata['credentials']`` "
            "(dev / single-tenant). ``vault`` defers to a Vault KV v2 "
            "path; the path is the value of ``credentials_ref`` on the "
            "scan request. Future backends: ``akeyless``, ``aws_secrets``."
        ),
    )
    identity_vault_addr: str | None = Field(
        default=None,
        description="Vault address (e.g. https://vault.internal:8200). Required when backend is ``vault``.",
    )
    identity_vault_kv_mount: str = Field(
        default="kv",
        description="KV v2 mount where ``credentials_ref`` paths resolve.",
    )
    identity_bloodhound_image: str = Field(
        default="ghcr.io/dirkjanm/bloodhound.py:latest",
        description="Container image for the bloodhound.py collector.",
    )
    identity_certipy_image: str = Field(
        default="ghcr.io/ly4k/certipy:latest",
        description="Container image for the Certipy ADCS scanner.",
    )
    identity_roadrecon_image: str = Field(
        default="ghcr.io/dirkjanm/roadrecon:latest",
        description="Container image for the ROADrecon Entra ID collector.",
    )
    identity_collection_timeout_seconds: int = Field(
        default=1800,
        description=(
            "Wall-clock cap per identity scan. Big AD forests can take "
            "20+ minutes; default is 30 minutes. Tune per engagement."
        ),
    )
