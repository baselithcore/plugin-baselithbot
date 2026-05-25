# OSINT / EASM

The Red Agent ships two passive discovery scanners and a connector
interface so externally-managed EASM products can feed into the same
target catalog.

## Built-in scanners

| Scanner | Source | Network footprint |
| --- | --- | --- |
| `subfinder` | Aggregates passive sources (CT logs, public DNS, search engines). | None to the target — only third-party sources are queried. |
| `crtsh` | Certificate Transparency logs via `crt.sh`. | Single HTTPS GET to `crt.sh`. |

Both produce `INFO`-severity findings of `ScannerKind.OSINT`. The
discovered hostname lives in `Finding.endpoint`; the apex is
preserved in `Finding.target` so the operator can pivot from a
discovery back to its seed.

## Master toggle

`RED_AGENT_OSINT_ENABLED` is `false` by default. The two reasons:

1. The scope allowlist in `_ScopeConfig` is intentionally strict.
   Auto-discovered hosts must enter through a controlled gate.
2. Many enterprise customers operate a dedicated EASM (Defender ASM,
   Tenable ASM, Cycognito, Randori). Built-in scanners are a
   fallback, not a competitor.

## External EASM connectors

`integrations/easm.py` defines:

- `DiscoveredAsset` — the canonical record (host, source,
  discovered_at, confidence, apex, metadata).
- `EASMConnector` — ABC with a single `discover(*, apex)` method.
- `register_easm_connector(name, cls)` — extension point for
  built-in or plugin-supplied connectors.
- `get_easm_connector(name)` — resolver used by the orchestrator
  with no-op fallback for unknown / unset providers.

No third-party connectors ship today; `RED_AGENT_OSINT_EXTERNAL_EASM_PROVIDER`
defaults to `none`. Future built-ins (`defender_easm`, `tenable_asm`,
`cycognito`) plug in via `register_easm_connector`.

## Ingestion

`integrations/osint_ingestion.py` orchestrates the per-scan
discovery flow:

1. `findings_to_assets(findings, apex=…)` lifts OSINT findings
   into `DiscoveredAsset` records.
2. `merge_external(connector, apex, builtin)` appends connector
   output (fail-open).
3. `select_for_promotion(assets, …)` applies dedup vs. existing
   targets, scope policy, and the per-run cap.

`select_for_promotion` is pure: scope membership is injected as a
predicate so the engagement's allowlist regex / bug-bounty program
stays in the orchestrator and the ingestion path remains testable
without DB fixtures.

## Auto-promotion

`RED_AGENT_OSINT_AUTO_PROMOTE_TO_TARGETS` is `false` by default.
When set, eligible discoveries are inserted into
`red_agent_targets` with `state=discovered`. This **never** auto-
launches a scan; operators must approve the candidate from the
Targets tab — the same control plane that backs the manual New
Target wizard.

Recommended deployment pattern:

| Mode | `OSINT_ENABLED` | `AUTO_PROMOTE` | Notes |
| --- | --- | --- | --- |
| Strict allowlist | false | false | Discovery off; targets only via wizard. |
| Manual review | true | false | Discoveries surface as findings; operator copies into wizard. |
| Bug bounty | true | true | Scope is the program's domain regex; discoveries auto-queue for review. |
| Active engagement | true | true | Per-engagement allowlist; discoveries auto-queue. |

## Per-run cap

`RED_AGENT_OSINT_MAX_RESULTS_PER_RUN` (default 500) bounds a single
scan. Exceeding the cap silently truncates the lowest-confidence
results, with the truncation captured in the audit event.

## Future work

- Connectors: `defender_easm`, `tenable_asm`, `cycognito`,
  `randori`, `shodan_seeds`.
- ASN/CIDR enumeration scanner (BGP-driven).
- GitHub dorking scanner for public secret leaks under tenant orgs
  (extends the existing `gitleaks` adapter).
- Target-tab "Discovered" filter and bulk-approve UI action.
