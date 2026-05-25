# Deep web-app scanners

Schemathesis covers REST OpenAPI fuzzing. Three additional scanners
extend depth into areas the OpenAPI fuzzer cannot reach.

| Scanner | Surface | Network | Anchors |
| --- | --- | --- | --- |
| `graphql_audit` | GraphQL endpoint misconfigurations | yes (read-only) | `Target.metadata['graphql_path']` (default `/graphql`) |
| `jwt_audit` | JWT structural attacks | no | `Target.metadata['jwt_samples']` (list of token strings) |
| `waf_evasion` | WAF fingerprint + payload-encoding bypass | yes (intrusive) | URL / hostname target |

## `graphql_audit`

Network-light. Probes:

- **Introspection enabled** — POST `__schema` query; non-empty type
  list → Medium severity (CWE-200).
- **Field-suggestion leakage** — POST a query with a deliberately
  misspelt field; `Did you mean ...?` errors leak schema. Low.
- **Alias overload** — single document with 100 `__typename`
  aliases. 200 OK means no alias-count limit. Low (DoS surface,
  CWE-770).
- **Batch attack** — JSON-array body with two operations. 200 OK
  with two responses indicates batched operations are accepted.
  Low (rate-limit amplification).

The probes use `__typename` against the root, never mutating
operations.

## `jwt_audit`

Static analyser — never sends traffic to the target. Reads sample
tokens from `Target.metadata['jwt_samples']` and emits findings for:

- **`alg=none`** — Critical (CWE-347).
- **Weak HS256 secret** — verifies the signature against a 32-entry
  built-in wordlist (override via `RED_AGENT_JWT_AUDIT_HS256_WORDLIST_PATH`).
  A match yields a Critical finding (CWE-326).
- **`kid` path traversal** — header `kid` containing `../` or
  starting with `/`. High (CWE-22).
- **`jku` / `x5u` external** — header references an external HTTP/S
  URL. High (CWE-918).

The auditor never persists raw signatures; finding evidence carries
header + a redacted summary of standard claims (iss, sub, aud, exp).

## `waf_evasion`

INTRUSIVE only — every probe is intentionally suspicious traffic.

1. **Fingerprint** — `wafw00f`-style header / banner regex match
   for Cloudflare, AWS WAF, Akamai, F5 BIG-IP ASM, Imperva,
   ModSecurity. Emits an Info finding identifying the vendor.
2. **Evasion** — three baseline payloads (`sqli`, `xss`,
   `path-traversal`). For each baseline that the WAF blocks
   (status in {403, 406, 429, 501}), retries with three encoders:

   | Encoder | Effect |
   | --- | --- |
   | `url_double_encode` | `' OR 1=1` → `%2527%2520OR%25201%253D1` |
   | `mixed_case` | `admin` → `aDmIn` |
   | `fullwidth_unicode` | ASCII letters → fullwidth Unicode equivalents |

   A 200 response on the encoded variant produces a High-severity
   finding (CWE-693, "Protection Mechanism Failure") tagging the
   baseline class and the encoding that bypassed.

## Wiring residues

- Orchestrator: register the three scanners in the factory.
- Wizard: add `graphql_path` and `jwt_samples` fields to URL/HOSTNAME
  target metadata.
- UI: surface the WAF vendor + evasion mix on the target detail
  page; chip the JWT alg/severity on each token sample.

## Roadmap

- GraphQL: depth-limit + cost-attack heuristics, gateway-specific
  fingerprints (Hasura, Apollo Studio).
- JWT: ECDSA r/s zero-byte attack, public-key confusion (RS256 →
  HS256 trick), refresh-token rotation check.
- WAF: per-vendor rule fingerprint, ML-suggested encoder chains
  beyond the three built-in ones.
