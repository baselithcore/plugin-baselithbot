# CI/CD red team

The CI/CD pipeline is the most leveraged attack surface in modern
infrastructure: a single compromised workflow can mint package
signatures, push to production, and pivot to cloud credentials.
Three scanners cover the majority of real-world attack patterns
seen in the field today.

| Scanner | Network | Auth | Surfaces |
| --- | --- | --- | --- |
| `gato` | Yes | GitHub PAT | Self-hosted runner abuse, ``pull_request_target`` exploits, secret exfiltration paths, OIDC trust weaknesses. |
| `workflow_audit` | No | None | Static analysis of `.github/workflows/*.yml` for the same classes of issue Gato finds — but offline against a repo checkout. |
| `dependency_confusion` | Yes (registry only) | None | Internal-package names that an attacker could squat on npm / PyPI. |

## Master toggle

`RED_AGENT_CICD_ENABLED` is `false` by default. Each scanner has a
per-scanner enable flag underneath so operators can run e.g. only
the workflow auditor on every commit while reserving the Gato run
for engagement windows.

## `workflow_audit`

Network-free. Operates on a `REPO`-typed target whose
`metadata['repo_path']` (or `Target.value`) points at a clone. Walks
`.github/workflows/*.y*ml` and emits findings for:

- **Critical** — `pull_request_target` workflow that checks out the
  PR head ref *and* runs code. Every external contributor gets
  arbitrary code execution in the privileged context. CWE-913.
- **High** — `run` step that interpolates an untrusted
  `github.event.*` field directly into the shell. Script injection.
  CWE-78.
- **Medium** — Third-party action referenced by tag/branch instead
  of a 40-char commit SHA. Tag-move attack vector. First-party
  `actions/*` and `github/*` actions are explicitly allowlisted.
  CWE-829.
- **Medium** — `secrets.*` interpolated into `run` commands. Leaks
  via process listings, build logs, downstream tools. CWE-532.

## `dependency_confusion`

Reads package manifests:

| Ecosystem | Files |
| --- | --- |
| npm | `package.json` (`dependencies` + `devDependencies` + `peerDependencies`). |
| PyPI | `requirements.txt`, `requirements-dev.txt`, PEP-621 `[project]`, Poetry `[tool.poetry.dependencies]`. |

For every declared package whose name starts with one of the
operator-supplied internal namespaces
(`Target.metadata['internal_package_namespaces']`, e.g.
`["@acme/", "acme_"]`) the scanner queries the public registry's
JSON metadata endpoint:

- **404** → confusion vector, High severity. Attacker who registers
  the name hijacks installs on every build that resolves public
  ahead of internal.
- 5xx / timeout → low-confidence "lookup failed" path; never
  produces a high-severity finding.

Without internal namespaces configured the scanner returns nothing —
there is no safe way to distinguish a typo from an intentional
internal reference.

## `gato`

Sandboxed wrapper around the Praetorian `gato enumerate` CLI. The
GitHub PAT comes from the credential resolver
(`Target.metadata['credentials_ref']` → vault) or, for development,
the `RED_AGENT_CICD_GATO_PAT` config. The token reaches the
container via `--env-file` (`GH_TOKEN=…`) — never via argv — so it
does not show up in the structured run log.

Severity ladder:

| Gato category | Severity | Notes |
| --- | --- | --- |
| `pwn_request` | Critical | PR-driven RCE in privileged workflow context. |
| `self_hosted_runner` | High | Runner reachable from forked PRs. |
| `actions_oidc_trust` | High | Cloud trust policy accepts the wrong subject claim. |
| `secrets_in_logs` | Medium | Secret value reachable via build log. |

## Wiring residues

- Routers: `/red-agent/scans` should accept the new
  `internal_package_namespaces` and `repo_path` metadata for REPO
  targets in the New Target wizard.
- UI: a "CI/CD" facet in the Findings tab grouped by category
  (gato/workflow/confusion).
- The orchestrator already builds scanners from `RedAgentConfig`;
  registering the three new ones is the only outstanding wiring.

## Roadmap

- GitLab CI auditor (`.gitlab-ci.yml`).
- Jenkins job-DSL / pipeline auditor.
- Maven / NuGet / Go ecosystems for dependency confusion.
- OIDC trust policy diff against a known-good baseline.
- Self-hosted runner takeover dynamic check (gated INTRUSIVE).
