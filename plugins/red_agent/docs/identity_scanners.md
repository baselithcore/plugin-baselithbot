# Identity attack scanners

Three scanners enumerate the identity attack surface of an Active
Directory forest or an Entra ID tenant. They all live behind the
same master toggle, share the same credential resolver, and emit
findings under `ScannerKind.IDENTITY`.

| Scanner | Target type | Tool | Wire protocol |
| --- | --- | --- | --- |
| `bloodhound` | `ad_domain` | `bloodhound-python` (DCOnly collection) | LDAP + SAMR |
| `certipy` | `ad_domain` | `certipy-ad find` | LDAP + RPC |
| `roadrecon` | `entra_tenant` | `roadrecon` | Microsoft Graph |

## Master toggle + intensity

`RED_AGENT_IDENTITY_ENABLED` is `false` by default. AD/Entra traffic
with valid credentials is the most blue-team-detectable activity the
Red Agent performs, so opt-in is mandatory. The scanners refuse
`PASSIVE` intensity outright; passive identity scanning is not a
meaningful operation when every tool needs an authenticated bind.

`RED_AGENT_IDENTITY_ALLOW_MUTATING_ACTIONS` (default false) gates
Certipy sub-commands that change directory state (e.g.
`certipy-ad account create`). Even with `INTRUSIVE` intensity these
remain off until explicitly granted.

## Credentials

The plugin never accepts cleartext credentials in the scan request
body. Each scan references an opaque `credentials_ref` that
`_credential_resolver.py` maps to an :class:`IdentityCredential` at
run-time.

Two backends ship today:

| Backend | Source | Use |
| --- | --- | --- |
| `metadata` | `Target.metadata['credentials']` | Dev / single-tenant labs only. |
| `vault` (planned) | HashiCorp Vault KV v2 mount | Production. |

The resolver is pluggable: `register_backend("akeyless", AkeylessBackend)`
installs additional sources without touching the orchestrator.

`credentials_to_env(cred)` renders the resolved credential into a
stable env-var contract (`RA_USERNAME`, `RA_PASSWORD`, `RA_DOMAIN`,
`RA_REFRESH_TOKEN`) consumed by every identity scanner image. The
sandbox runner writes those into a workdir-local `--env-file` so the
values never appear in argv, `ps`, or the structured run log (the
log records keys only).

## BloodHound

`bloodhound-python` runs in `DCOnly` mode by default — LDAP-only
collection, no SMB session enumeration, no shares scrape. The
adapter parses the resulting `bh-users.json` and surfaces three
attack-path-relevant flags:

| Flag | Severity | Reason |
| --- | --- | --- |
| `kerberoastable` | High | Account has SPNs; TGS-REQ tickets crackable offline. |
| `dontreqpreauth` (AS-REProast) | High | Pre-auth disabled; AS-REP responses crackable. |
| `unconstraineddelegation` | Critical | Chains via printerbug to domain compromise. |

Heavier path computation (shortest path to Domain Admins, ACL
takeover) is left to the BloodHound graph instance — the Red Agent
emits the per-object findings that warrant operator triage on their
own.

## Certipy (ADCS)

`certipy-ad find -vulnerable -json` enumerates ADCS templates and
flags ESC1–ESC11 misconfigurations.

| ESC | Severity | Notes |
| --- | --- | --- |
| ESC1, ESC2, ESC3, ESC4, ESC5 | Critical | Direct DA via cert request / template ACL takeover. |
| ESC6, ESC7, ESC8 | High | EDITF subject SAN, CA admin role abuse, NTLM relay to web enrolment. |
| ESC9, ESC10, ESC11 | High | Schannel / weak StrongCertBinding bypass paths. |

The parser handles both Certipy 4.x (`[!] Vulnerabilities`) and
older (`Vulnerabilities`) JSON shapes.

## ROADrecon (Entra ID)

ROADrecon collects via the Microsoft Graph API using either a
refresh token (preferred — survives MFA) or username/password. The
adapter currently emits two finding classes:

- **Privileged role without MFA** (Critical). Joins
  `directoryroles[].members[]` against `authmethods[].isMfaRegistered`
  and flags any user holding a privileged role template
  (Global Administrator, Privileged Role Administrator, Application
  Administrator, …) with no MFA registration on record.
- **Over-permissioned application** (High). Application
  registrations holding high-impact Graph permissions
  (`Directory.ReadWrite.All`, `RoleManagement.ReadWrite.Directory`,
  `Application.ReadWrite.All`, `AppRoleAssignment.ReadWrite.All`,
  `User.ReadWrite.All`).

## Roadmap

- Certipy mutating mode: gated `account create` + `template create`
  for INTRUSIVE engagements with `allow_mutating_actions=true`.
- ROADrecon Conditional Access policy gap analysis (legacy auth
  allowed, no MFA on cloud admins, etc.).
- BloodHound CommunityEdition (Postgres) ingestion endpoint so
  attack paths land in the existing FalkorDB graph view.
- Vault credential backend implementation (#4).
