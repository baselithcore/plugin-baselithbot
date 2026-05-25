# Authenticated scans + credential vault

Unauthenticated DAST surfaces only the public-facing attack surface.
Most real applications hide their interesting endpoints behind a
login, an API key, or an OAuth token. This module brings two pieces
together:

1. A vault-backed credential resolver shared with the identity
   scanners (`_credential_resolver.py`).
2. A target-bound :class:`AuthProfile` that the DAST adapters render
   into wire-format auth context (`scanners/_auth_helpers.py`).

## Vault credential backend

`RED_AGENT_IDENTITY_CREDENTIALS_BACKEND=vault` swaps the default
`metadata` backend out for a HashiCorp Vault KV v2 reader.

| Setting | Purpose |
| --- | --- |
| `RED_AGENT_IDENTITY_VAULT_ADDR` | Vault server URL (e.g. `https://vault.internal:8200`). |
| `RED_AGENT_IDENTITY_VAULT_KV_MOUNT` | KV v2 mount path. Defaults to `kv`. |
| `VAULT_TOKEN` (env) | Token used to authenticate; expected to come from AppRole/Kubernetes auth out-of-process. |

`Target.metadata['credentials_ref']` is the relative path under the
mount (e.g. `red-agent/engagements/acme/ad`). The backend reads the
latest version and expects the secret payload to carry
`username`/`password`/`domain`/`refresh_token` keys.

If `addr` or `token` is missing the resolver logs
`red_agent.credentials.vault_misconfigured` and falls back to the
metadata backend so the scan keeps running with whatever the
operator wrote into `Target.metadata['credentials']`. Production
operators who want hard-fail semantics should pin the backend with
`identity_credentials_backend=vault` plus a startup health check
that resolves a sentinel path during `baselith doctor`.

## AuthProfile

`AuthProfile` is a small Pydantic model attached to the target's
metadata under `auth_profile`. Five flows are covered today:

| Kind | Required fields | Wire result |
| --- | --- | --- |
| `none` | — | `extra_headers` only. |
| `basic` | `username`, `password` | `Authorization: Basic …` header. |
| `bearer` | `token` | `Authorization: Bearer …` header. |
| `cookie` | `token`, optional `cookie_name` | Cookie jar entry. |
| `form_login` | `username`, `password`, `login_url` | POSTs to `login_url`, captures `Set-Cookie`. |
| `oauth2_client_credentials` | `oauth2_token_url`, `oauth2_client_id`, `oauth2_client_secret` | Token endpoint POST → bearer header. |

`AuthProfile.to_redacted_dict()` produces an audit-safe view: every
`SecretStr` is replaced with `"<redacted>"`, structural fields are
preserved so the operator can confirm the right kind of profile ran.

## Rendering

`render_auth(profile)` returns a :class:`RenderedAuth` with
``headers``, ``cookies``, and an optional ``basic_auth`` tuple. The
adapter then maps those onto its argv:

| Scanner | Mapping |
| --- | --- |
| `nuclei` | `-H "K: V"` per header; cookies collapsed into a single `Cookie:` header. |
| `zap` | Authentication context file emitted into the ZAP workdir. |
| `schemathesis` | `--header K=V` and `--auth user:pass` for BASIC. |

A profile that fails validation raises
:class:`AuthProfileError`; the adapter never silently degrades to an
unauthenticated scan. This is deliberate — under-specified auth
configurations have historically caused customers to ship reports
that look "clean" only because the scanner never reached the
authenticated surface.

## Wiring example

```python
target = Target(
    type=TargetType.URL,
    value="https://app.example.com",
    metadata={
        "credentials_ref": "red-agent/engagements/acme/web-admin",
        "auth_profile": {
            "kind": "oauth2_client_credentials",
            "oauth2_token_url": "https://idp.example.com/oauth2/token",
            "oauth2_client_id": "scanner-bot",
            # secret resolved separately via the credential resolver.
        },
    },
)
```

The orchestrator pulls the secret via the resolver, splices it into
the profile, and hands the merged profile to each DAST adapter
through `target.metadata['auth_profile']`.

## Threat model

- **Argv exfiltration.** Credentials never appear in argv. Identity
  scanners use `--env-file` workdir-local 0600; DAST adapters use
  `-H` flags with already-rendered headers (the secret is not in the
  argv as a discrete token; it ends up inside the header value, which
  docker-run logs do still capture). Operators who need to defend
  against an attacker reading the local docker daemon log should
  prefer the env-file path.
- **Secret reuse across scans.** The resolver returns a fresh
  :class:`IdentityCredential` per call; nothing is cached at the
  module level. Vault rotation / lease revocation works as expected.
- **Misconfigured backend.** Falling back from `vault` to `metadata`
  is logged at WARNING. Operators are expected to alert on
  `red_agent.credentials.vault_misconfigured` so a silent downgrade
  cannot persist.

## Roadmap

- AWS Secrets Manager / Akeyless backends.
- Vault auth bootstrap (AppRole) inside the plugin instead of
  relying on a pre-mounted `VAULT_TOKEN`.
- ZAP auth-context script generation from `form_login` profiles.
- Schemathesis `--header` integration.
- Refresh-token rotation hook for OAuth `refresh_token` flow on
  long-lived scans.
