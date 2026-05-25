# Red Agent — Endpoint Daemon Architecture

> Authoritative design for `baselith-redagent-daemon`, the on-host agent
> that complements the server-side `red_agent` plugin. The daemon is
> deployed on customer assets and production servers to perform
> on-target reconnaissance, telemetry collection, and policy-driven
> scanning that cannot be done remotely.

## 1. Mission

The endpoint daemon is the **on-host extension** of the Red Agent:

- Collects host telemetry (process exec, file integrity, network, user
  events) for asset inventory and baseline drift detection.
- Executes scanners locally (SCA on installed packages, host
  configuration audits, secret discovery on disk) without exposing the
  asset to remote network traversal.
- Receives signed policy bundles and command stream from the
  `red_agent` plugin via a single mTLS gRPC channel.
- Streams findings and telemetry back to the backend, which persists
  them in Postgres + FalkorDB through the existing pipeline.

The daemon **never** opens listening sockets, never accepts inbound
connections, and never holds cloud credentials. It is reachable only
through the long-lived outbound gRPC stream it initiates.

## 2. Why a separate native daemon

| Concern | Python plugin (server) | Native daemon (host) |
| --- | --- | --- |
| Footprint idle | irrelevant | < 10 MB RAM, single static binary |
| Kernel telemetry | n/a | eBPF (linux), ESF (macOS) |
| GC pause on syscall | n/a | unacceptable → no Go for hot path |
| Memory safety w/ root | n/a | mandatory → Rust |
| Cross-compile | n/a | Rust + `cross`/`zigbuild` matrix |
| Distribution | wheel | signed pkg/deb/rpm + notarized |

**Language: Rust.** Single static binary, no runtime, kernel-grade
ecosystem (`aya` for eBPF, `objc2` for ESF), memory safety mandatory
for a daemon that may run with elevated privileges.

## 3. Repository model

The daemon follows the same **dual-hosted, single-sourced** pattern
used by `baselithbot`: source of truth in this monorepo, output-only
mirror in a standalone GitHub repo for distribution.

```text
baselithcore-prod/                         (source of truth)
└── plugins/red_agent/
    ├── proto/agent.proto                  (canonical wire schema)
    ├── proto/_generated/                  (Python gRPC stubs, committed)
    ├── grpc/                              (Python AgentChannel servicer)
    ├── docs/agent_daemon.md               (this file)
    └── daemon/                            (Rust Cargo workspace)
        ├── Cargo.toml
        ├── crates/
        │   ├── daemon/                    (binary entrypoint)
        │   ├── proto/                     (tonic-build of agent.proto)
        │   ├── transport/                 (mTLS gRPC client)
        │   ├── collector/                 (telemetry sources)
        │   ├── executor/                  (sandboxed scanner runner)
        │   ├── policy/                    (signed bundle verification)
        │   └── keystore/                  (OS keychain abstraction)
        └── platform/                      (systemd / launchd assets)

baselith-redagent-daemon/                  (output-only)
└── populated each release via:
    git subtree split -P plugins/red_agent/daemon
```

The `agent.proto` schema is consumed by both sides via the same file:
the Python backend regenerates stubs with
`plugins/red_agent/proto/build.sh` (committed output under
`proto/_generated/`); the Rust workspace runs `tonic-build` against
the same proto via `crates/proto/build.rs`. Edits land here first —
the standalone repo is overwritten each release and any direct commit
to it is lost.

Tooling configuration:

- `pyproject.toml` `[tool.ruff].exclude` skips
  `plugins/red_agent/proto/_generated/` (generated code) and
  `plugins/red_agent/daemon/` (Rust, not Python).
- `[tool.mypy].exclude` already covers all of `plugins/`.
- `plugins/red_agent/daemon/.gitignore` keeps `target/` and
  `Cargo.lock` out of git (workspace is a library workspace; lockfile
  ships with the binary crate's release process).

## 4. Threat model

The daemon defends against:

1. **Network adversary**: cannot read or forge agent ↔ backend traffic.
   → mTLS 1.3 with ed25519 client certs and root CA pinning.
2. **Compromised neighbor service on host**: cannot impersonate the
   agent or inject commands. → private key in OS keystore (Keychain /
   kernel keyring), unix-socket control plane authenticated via
   `SO_PEERCRED`.
3. **Compromised backend tenant boundary**: a tenant cannot inject
   commands into another tenant's agent. → SPIFFE-style workload
   identity, server enforces `tenant_id` from peer cert SAN.
4. **Replay**: a captured RPC cannot be replayed. → monotonic counter
   - nonce per envelope, server tracks last counter per agent.
5. **Stale agent**: an agent kicked out of fleet cannot rejoin
   silently. → server-issued `Disconnect{reason=REVOKED}` + cert CRL
   checked at every TLS handshake.
6. **Supply-chain on policy / scanner bundle**: a tampered bundle
   cannot be executed. → bundles signed with backend ed25519 key,
   agent verifies before any `exec`.

Out of scope: physical host compromise (root on box owns the agent),
kernel rootkits below eBPF/ESF observability surface.

## 5. Wire protocol

Single bidirectional gRPC stream over HTTP/2, mTLS, port 443.

```proto
service AgentChannel {
  // One stream per agent. Lives for the agent's lifetime.
  rpc OpenStream(stream AgentMessage) returns (stream ServerMessage);
}
```

Framing rationale:

- **Bidirectional stream**: backend pushes commands without polling;
  agent pushes telemetry continuously. Zero added latency.
- **Outbound only from agent**: passes through corporate firewalls
  unchanged. No port forwarding, no inbound rules.
- **HTTP/2 not HTTP/3**: enterprise firewalls still block UDP. Revisit
  in 2027.
- **Single multiplexed channel**: avoids connection storms; HTTP/2
  flow control natively handles backpressure.

See [`plugins/red_agent/proto/agent.proto`](../proto/agent.proto) for
the full schema. Highlights:

- `AgentHello` carries `protocol_version` and `capabilities` for
  capability negotiation. Backend's `ServerHello` returns the
  intersection of supported features. This enables rolling upgrades
  across a heterogeneous fleet.
- `Telemetry` events are typed and self-describing; new event kinds
  can be added without bumping `protocol_version` (forward-compat via
  `oneof` `unknown` fallback handling).
- `Command` carries an `idempotency_key`; agent dedupes within a
  sliding window to make at-least-once delivery safe.

## 6. Identity & PKI

### 6.1 Workload identity (SPIFFE-style)

Agents are identified by a URI SAN in their certificate:

```text
spiffe://baselith.io/tenant/{tenant_id}/agent/{agent_uuid}
```

The `tenant_id` and `agent_uuid` are extracted server-side from the
peer certificate during the gRPC interceptor — never from request
headers, never from a self-asserted field. Trust flows from PKI down
to RLS row filters in Postgres.

### 6.2 PKI hierarchy

```text
Root CA "agent"     (offline, HSM/KMS, 10y, ed25519)
└─ Intermediate CA "agent-issuer"   (online, 1y, rotation)
   └─ Tenant Sub-CA "tenant-{id}"   (per tenant, 1y)
      └─ Agent leaf cert            (ed25519, 90d, rotate at 60d)

Root CA "backend"   (separate trust chain)
└─ Backend service cert             (1y)
```

Justification:

- Two roots: compromise of one chain does not break the other.
- Per-tenant Sub-CA: revoking a tenant is a single CA revocation, not
  a per-agent CRL update.
- 90-day agent certs: short enough that a leaked key rolls itself off,
  long enough that rotation noise stays manageable.
- ed25519 over RSA/ECDSA: smaller keys, faster handshakes, modern.

### 6.3 Enrollment flow

```text
1. Operator (UI) generates enrollment_token for tenant T.
   Token = JWT { tenant_id: T, scope: enroll, single_use: true,
                 exp: now+24h }, signed with backend enrollment key.

2. Token bundled into installer (env var, /etc/baselith/enroll.token,
   or MDM payload).

3. Agent first start:
   a. Generate ed25519 keypair on-device (private key never leaves).
   b. POST /v1/enroll  (no mTLS — token-authenticated only)
      body: { csr, agent_uuid, platform, version }
   c. Backend validates token, signs CSR with tenant Sub-CA.
   d. Response: { cert, chain, agent_uuid, root_ca_fingerprint,
                  backend_endpoint, config_url }

4. Agent persists:
   - cert in /var/lib/baselith/agent/cert.pem
   - private key in OS keystore (macOS Keychain, linux kernel keyring,
     fallback: encrypted file with `age` keyed to host TPM if present)
   - root_ca_fingerprint pinned for all subsequent TLS handshakes.

5. Token discarded.

6. Agent opens AgentChannel.Connect and stays connected.
```

### 6.4 Cert rotation

- Agent monitors `notAfter`. At T-30d, sends `RotationRequest` over
  the existing stream (already mTLS-authenticated with old cert).
- Backend issues new cert, agent atomically swaps in keystore, old
  cert rotated out.
- Stream is **not** torn down: HTTP/2 keeps the original connection
  open, the new cert applies on next reconnect.

## 7. Multi-tenancy enforcement

Every server-side operation derives `tenant_id` from the peer cert.
Application code receives `TenantContext { tenant_id, agent_uuid }`
via FastAPI dependency injection.

Persistence:

- **Postgres**: row-level security on every agent table.
  `current_setting('app.tenant_id')::uuid` is set by an interceptor
  before any query downstream of an agent RPC.
- **FalkorDB**: graph-per-tenant (`tenant_{uuid}`). Existing graph
  helpers are parameterized on the active tenant. No cross-tenant
  Cypher is constructible at the driver level.
- **Telemetry table**: partitioned monthly, indexed on
  `(tenant_id, agent_id, ts)`. Partition pruning gives O(month) scans
  even at fleet scale.

This design generalizes the existing `tenant_id TEXT` column on
`red_agent_targets` (migration 003) — the same convention applies
across all daemon-related tables.

## 8. Crypto & connection profile

| Property | Value | Rationale |
| --- | --- | --- |
| TLS version | 1.3 only | No downgrade. Fail closed. |
| ALPN | `h2` | gRPC over HTTP/2. |
| Cipher | `TLS_AES_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256` | Modern AEADs. |
| KEX | X25519; hybrid ML-KEM-768 once `rustls` ≥ 0.24 stabilizes | PQ readiness. |
| Cert algo | ed25519 | Smallest, fastest, modern. |
| Cert validity | 90 days | Forces rotation discipline. |
| Pinning | root CA fingerprint, baked at install | Defends against rogue intermediate. |
| OCSP | stapling required, must-staple flag on agent cert | Online revocation, no soft-fail. |
| Replay | monotonic counter + nonce per envelope | Server rejects replays per agent. |
| Keepalive | HTTP/2 PING every 20 s | Detect dead peer fast. |
| Reconnect | exponential backoff with jitter, cap 5 min | Avoid thundering herd. |

Proxy support:

- Honors `HTTPS_PROXY` env var (HTTP CONNECT). Required for corporate
  egress through Zscaler / Bluecoat / Squid.
- TLS terminates end-to-end (proxy is CONNECT tunnel, never sees
  cleartext).

## 9. Backend integration points

The daemon binds to two new server-side surfaces:

1. **REST**: `POST /red-agent/agents/enroll` — token-authenticated,
   one-shot, returns signed cert. Implemented in
   `plugins/red_agent/routers/agents.py`.
2. **gRPC**: `AgentChannel.Connect` — mTLS-authenticated streaming
   service. Implemented in
   `plugins/red_agent/grpc/agent_channel.py` using `grpcio` mounted
   on a separate port (e.g. 50443) behind the same Envoy gateway.

The gRPC service is wired into the existing plugin DI container so it
shares persistence, audit, and graph helpers with the REST layer.

Telemetry events flow into a new partitioned table
`red_agent_agent_telemetry` (see migration 004). Findings produced by
on-host scanners reuse the existing `red_agent_findings` table with
`source='endpoint'` discriminator.

## 10. Roadmap

### Phase 1 — MVP (tens of agents, 0–3 months) — **shipped as `v0.1.0`**

- ✅ Skeleton Rust workspace, tonic gRPC client, mTLS handshake (TLS
  1.3 only, ed25519 client cert, pinned-root SPKI verifier).
- ✅ Enrollment flow (REST `POST /red-agent/agents/enroll` + cert
  issuance), persisted in OS-native keystore.
- ✅ Basic collector: process list, package inventory, file hashing
  on-demand. **No eBPF/ESF yet.**
- ✅ Local executor: standalone scanner binaries (no Docker), confined
  by `landlock` (linux) / `sandbox-exec` (macOS).
- ✅ Signed policy bundle verifier (ed25519, monotonic version pin).
- ✅ Backend: Envoy public LB, single grpc gateway, direct writes to
  Postgres + FalkorDB.
- ✅ Fleet UI: agents tab in `plugins/red_agent/ui/` listing
  agents, status, recent telemetry, enrollment-token generator.
- ✅ End-to-end mTLS handshake regression test
  (`crates/transport/tests/mtls_handshake.rs`) and dev compose stack
  (`daemon/dev/docker-compose.yml`) for local smoke runs.

### Phase 2 — hundreds (3–9 months)

- NATS JetStream between gRPC gateway and backend (telemetry buffer +
  replay on backend restart).
- Automated cert rotation pipeline (smallstep-CA backed).
- Policy targeting via labels (`os=linux`, `env=prod`, `region=eu`).
- Telemetry rollup (hourly aggregations, 30 d retention on hot tier).
- eBPF process exec tracer (linux), ESF process events (macOS).

### Phase 3 — thousands (9 + months)

- ClickHouse / Loki for hot+warm telemetry tier.
- Stateless backend replicas behind LB (sticky session per stream).
- Regional NATS leaf nodes if WAN latency hurts.
- SPIRE for workload identity once fleet > 1 k.
- Multi-region deploy with data residency routing.

## 11. Decisions deferred (do **not** prematurely build)

- ❌ Kafka pipeline — not until > 500 agents.
- ❌ Backend sharding — single FastAPI scales to ~ 1 k agents on the
  reverse-proxy fan-in pattern.
- ❌ Hierarchical fleet groups — flat labels suffice through phase 2.
- ❌ HTTP/3 / QUIC — enterprise firewalls still block UDP.
- ❌ Self-hosted SPIRE — smallstep CA is sufficient through phase 2.
- ❌ Custom kernel modules — eBPF + ESF cover every observability
  need we have on the roadmap.

## 12. Operational definition of done (Phase 1)

The daemon is considered MVP-complete when:

1. A fresh host runs the installer with an enrollment token, obtains
   a tenant-scoped cert, and connects to the backend within 30 s.
2. The Fleet tab in the UI shows the agent online with platform
   metadata and last heartbeat.
3. The backend issues a `RunInventory` command; the agent returns a
   complete package inventory which lands as `host`-kind targets in
   `red_agent_targets`.
4. Pulling the agent's cert from the keystore and rotating it
   succeeds without dropping the gRPC stream.
5. The agent's outbound traffic, captured at the perimeter, contains
   only TLS 1.3 to port 443 — no inbound listeners, no extra ports.

## 13. Distribution (Phase 1)

Pre-built binaries are produced by
[`.github/workflows/red-agent.yml`](../../../.github/workflows/red-agent.yml)
on every `daemon-v*` tag. Five targets ship per release:

| Target | Tooling | Notes |
| --- | --- | --- |
| `aarch64-apple-darwin` | native rustup on `macos-latest` | Apple Silicon |
| `x86_64-apple-darwin`  | native rustup on `macos-latest` | Intel Mac |
| `universal-apple-darwin` | `lipo` of the two darwin builds | Mac-mixed fleets |
| `x86_64-unknown-linux-musl`  | `cargo-zigbuild` on `ubuntu-latest` | static-pie ELF, any distro |
| `aarch64-unknown-linux-musl` | `cargo-zigbuild` | static ELF, ARM64 |

`SHA256SUMS` covers all binaries plus
[`daemon/scripts/install.sh`](../daemon/scripts/install.sh), the
operator-facing installer. The installer auto-detects OS+arch,
verifies the SHA-256, writes config + the pinned CA fingerprint,
optionally redeems an enrollment token, and registers a hardened
systemd unit (Linux) or launchd plist (macOS). `BINARY=` env
supports air-gapped installs from a previously-`scp`'d binary.

Operator one-liner:

```bash
curl -fsSL https://baselithcore.xyz/dev/install.sh \
    | sudo bash -s -- \
        --backend     https://red-agent.example.com:443 \
        --fingerprint <SPKI-SHA256-HEX> \
        --token       <ENROLLMENT_TOKEN>
```

Per-target download URLs (rolling-release endpoint, always serves
the latest tagged build):

- `https://baselithcore.xyz/dev/aarch64-apple-darwin`
- `https://baselithcore.xyz/dev/x86_64-apple-darwin`
- `https://baselithcore.xyz/dev/universal-apple-darwin`
- `https://baselithcore.xyz/dev/x86_64-unknown-linux-musl`
- `https://baselithcore.xyz/dev/aarch64-unknown-linux-musl`
- `https://baselithcore.xyz/dev/SHA256SUMS`

Phase 2 distribution adds: SBOM via `cargo about`, signed `.deb` /
`.rpm`, notarized macOS `.pkg`, and an in-place `SelfUpdateCmd`
channel (the verification primitives are already in
`crates/policy`).
