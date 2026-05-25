# Multi-source threat intel

GreyNoise (already shipping) covers internet-wide noise. Four
additional enrichers add the reputation / exposure context
operators ask for in the field:

| Enricher | Source | Anchor | Adds to evidence |
| --- | --- | --- | --- |
| `VirusTotalEnricher` | VirusTotal v3 | Public IP / bare domain | `vt_malicious`, `vt_suspicious`, `vt_total_engines`, `vt_categories` |
| `ShodanEnricher` | Shodan host lookup | Public IP | `shodan_open_ports`, `shodan_vulns`, `shodan_tags`, `shodan_org` |
| `CensysEnricher` | Censys v2 hosts | Public IP | `censys_services`, `censys_open_ports`, `censys_autonomous_system` |
| `OTXEnricher` | AlienVault OTX | Public IP / CVE | `otx_pulse_count`, `otx_pulses`, `otx_adversaries` |

## Off by default

Each toggle defaults to `false`. Most customers already pay one or
two of these vendors and don't want unnecessary egress. Operators
flip per-engagement: `RED_AGENT_VIRUSTOTAL_ENRICHER_ENABLED=true`,
`RED_AGENT_SHODAN_ENRICHER_ENABLED=true`, etc.

The VirusTotal and Censys enrichers also disable themselves
silently when their credentials are missing — `enabled=true` plus
no `api_key` / `api_id` collapses to a no-op enricher rather than a
hard error, so a misconfigured deployment never breaks scans.

## Anchor selection

- **VirusTotal** — `Finding.target` parsed first as a public IP,
  then as a bare domain. URL targets that don't normalise to either
  are skipped.
- **Shodan** + **Censys** — public IPs only. Private / loopback /
  link-local / multicast / reserved addresses are filtered out.
- **OTX** — both public IPs *and* `Finding.cve` (`CVE-YYYY-NNNN`).
  A single finding may be enriched on either anchor, often both.

The `_BaseTIClient` base class deduplicates anchors per scan: an
IP referenced by ten findings hits the upstream once, and the
result fans out to each finding's evidence dict.

## Severity is untouched

None of the enrichers modify `Finding.severity` directly. They
augment evidence so the existing `RiskScoringEnricher` can fold the
new signals into the unified VPR-style score. This keeps every
severity bump auditable through one chokepoint.

## Wiring residues

- Orchestrator: instantiate the four enrichers from `RedAgentConfig`
  and slot them after `EpssKevEnricher` in the post-pipeline.
- UI: surface the new evidence keys in the Finding detail panel
  (vt categories, shodan vulns list, OTX adversary chips).
- Risk scorer: extend the multiplier chain to bump score when
  `vt_malicious >= 5`, `shodan_vulns` is non-empty, or
  `otx_adversaries` is non-empty.

## Roadmap

- Mandiant / Recorded Future / IntelOwl connectors.
- File-hash enrichment (VT) for SCA findings carrying a
  `pkg.sha256`.
- URL-scan enrichment (urlscan.io) for DAST findings.
- Cache TTL configurable per enricher (today: process lifetime).
