# Cloud red team

The existing CSPM coverage (Prowler, Checkov) audits cloud
configuration posture. This module adds the post-exploit layer:
which IAM paths actually escalate to admin, which custom Azure role
hides a wildcard, which cross-cloud principal is the real blast
radius.

| Scanner | Cloud | Surface |
| --- | --- | --- |
| `pmapper` | AWS | IAM privesc graph; emits per-path findings with risky-action evidence. |
| `scoutsuite` | AWS / Azure / GCP / Aliyun / OCI | Multi-cloud misconfig sweep; complements Prowler on Azure + GCP. |
| `azurehound` | Azure / Entra ID | Resource graph; flags privileged role assignments + wildcard custom roles. |

## Master toggle

`RED_AGENT_CLOUD_RED_TEAM_ENABLED` is `false` by default. Each
scanner has a per-scanner enable flag (`pmapper_enabled`,
`scoutsuite_enabled`, `azurehound_enabled`) so operators can run
ScoutSuite on every account on a daily cadence and reserve the
PMapper graph build for engagement windows.

## Credentials

All three scanners use the standard credential resolver.
`Target.metadata['credentials_ref']` resolves through the
configured backend (`metadata` for dev, `vault` for production) to
an :class:`IdentityCredential` whose fields are reinterpreted per
provider:

| Provider | Field map |
| --- | --- |
| AWS | `username` → AWS access key id, `password` → secret access key, `domain` → STS session token. |
| Azure | `username` → AZURE_CLIENT_ID, `password` → AZURE_CLIENT_SECRET, `refresh_token` → AZURE_REFRESH_TOKEN. |
| GCP | `password` → JSON service-account key body. |

Secrets reach the container through the `--env-file` mechanism on
the sandbox runner (workdir-local 0600), so they never appear in
argv, host `ps`, or the structured run log.

## `pmapper`

Wraps `pmapper graph create --account <id>` and parses the resulting
JSON for two finding classes:

- **Privesc paths** (`privesc_paths`) — every (source, destination)
  chain. Severity is **Critical** when the path includes one of the
  high-impact actions (`*`, `iam:*`, `sts:AssumeRole`) and **High**
  otherwise.
- **Admin-attached principals** — any node that holds
  `AdministratorAccess`, `PowerUserAccess`, or `IAMFullAccess`
  directly. Severity **High** because compromise of the principal
  is a full account takeover regardless of edges.

CWE-269 (improper privilege assignment) on every emit so the
compliance mapper picks them up.

## `scoutsuite`

Wraps `scout <provider> --report-dir /workspace --no-browser
--result-format json`. The provider is read from
`Target.metadata['cloud_provider']` and falls back to the configured
default. ScoutSuite's report is a JS module with a leading variable
assignment (`scoutsuite_results = …;`); the parser strips the wrapper
before JSON-decoding.

Severity mapping mirrors the upstream `level` field:

- `danger` → High.
- `warning` → Medium.
- `info` → Info.

Empty-`items` rules are dropped so the noise floor stays low.

## `azurehound`

Wraps `azurehound list --tenant <tenant> --output …jsonl` and parses
the JSON-Lines stream. Two finding classes today:

- **Privileged role assignment** — any assignment whose `roleName`
  is in {`Owner`, `Contributor`, `User Access Administrator`,
  `Role Based Access Control Administrator`}. High severity.
- **Wildcard custom role** — custom role whose `permissions[].actions`
  include `*` or `Microsoft.Authorization/*`. High severity.

The same JSONL feeds BloodHound CE for graph analysis when the
customer runs one. The Red Agent's own findings are independent of
that — they trigger on shape alone.

## Wiring residues

- Orchestrator: register the three scanners in the factory.
- Wizard: `cloud_provider` field on the New Target wizard for
  `CLOUD_ACCOUNT` targets so ScoutSuite picks the right provider.
- UI: "Cloud" facet on the Findings tab grouped by provider.
- Path narrative renderer: render the `edges` evidence on PMapper
  findings as a graph thumbnail.

## Roadmap

- GCP path solver (custom — the upstream PMapper-equivalent for GCP
  is sparse).
- Pacu integration for active post-exploit modules (gated INTRUSIVE,
  dual-control approval).
- Cross-account IAM trust analysis for AWS Organizations.
- BloodHound CE ingestion endpoint for the AzureHound output to feed
  the existing FalkorDB graph view.
