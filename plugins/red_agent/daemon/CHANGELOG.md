# Changelog

All notable changes to `baselith-redagent-daemon` are recorded here.
This file lives in the monorepo (source of truth) and is mirrored
into the standalone `baselith-redagent-daemon` repo on each release
via `scripts/release_redagent_daemon.sh`.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is [SemVer](https://semver.org/spec/v2.0.0.html); the
daemon's `protocol_version` is bumped independently and only on
wire-incompatible changes (see `proto/agent.proto`).

## [0.1.0] — 2026-04-26

First Phase 1 / MVP cut. End-to-end skeleton from cargo workspace
through to a real handshake against a backend gRPC server. Targets
the **tens-of-agents** scale described in
`plugins/red_agent/docs/agent_daemon.md` §10.

### Added

- **Workspace skeleton** with seven crates: `daemon` (binary
  entrypoint), `proto` (tonic-built stubs from
  `plugins/red_agent/proto/agent.proto`), `transport` (mTLS gRPC
  channel), `collector` (host inventory), `executor` (sandboxed
  scanner runner), `policy` (signed bundle verifier), `keystore`
  (OS-native identity persistence).
- **Pinned-root mTLS transport.** TLS 1.3 only, ed25519 client cert,
  custom `rustls::ServerCertVerifier` that walks the presented chain
  for a SHA-256 SPKI match against the install-time pin. Standard CA
  trust path is intentionally bypassed so a public-CA-signed rogue
  intermediate cannot satisfy the pin.
- **Persistent identity keystore.** Linux kernel keyring, macOS
  Keychain, and an argon2id + chacha20-poly1305 encrypted-file
  fallback for headless hosts. Private keys are zeroized on drop.
- **Enrollment flow.** `baselith-redagent-daemon enroll --token <T>`
  redeems a one-shot operator-issued token at the backend's REST
  surface (`POST /red-agent/agents/enroll`) and persists the
  resulting cert + key to the keystore.
- **Connect → heartbeat → telemetry runtime.** Bidirectional
  AgentChannel stream, configurable heartbeat interval echoed by the
  server, exponential reconnect with jitter (cap 5 minutes).
- **Inventory collector.** Process list, package inventory (apt /
  rpm / brew / pip), local users and listening sockets, batched
  every 5 minutes by default.
- **Sandboxed local executor.** Scanner binaries run under
  `landlock` (linux ≥ 5.13) or `sandbox-exec` (macOS) with cgroup v2
  / posix_spawn resource caps applied per scanner profile.
- **Signed policy bundle verifier** (`crates/policy`). Backend signs
  policy bundles with ed25519; daemon refuses bundles with version
  ≤ the last accepted, with skewed timestamps, or with an invalid
  signature. The verifier survives reconnects so a session-drop
  attacker cannot replay an older bundle.
- **Telemetry persistence pipeline.** Events flow into the
  partitioned `red_agent_agent_telemetry` table on the backend
  (migration 004) via the gRPC servicer's batch handler.
- **Fleet UI tab.** `plugins/red_agent/ui/src/routes/FleetList.tsx`
  lists agents, status, recent telemetry, and exposes the
  enrollment-token generator.
- **Local development stack.** `daemon/dev/docker-compose.yml`
  brings up postgres + a one-shot openssl PKI bootstrap container +
  the backend + envoy (mTLS termination) + the daemon. Used for
  manual smoke runs and as the substrate for the Phase 2 NATS
  experiments.
- **One-shot installer** (`daemon/scripts/install.sh`). Detects
  OS+arch, downloads the right binary from the GitHub Release,
  verifies SHA-256, writes `/etc/baselith/redagent.toml` +
  `/etc/baselith/agent-ca.fingerprint`, optionally redeems an
  enrollment token, and registers a hardened systemd unit on Linux
  (`NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`) or a
  launchd plist on macOS. Supports `BINARY=` env for air-gapped
  installs, `--no-service` for testing, and `--prefix` for custom
  install paths. Shipped as a release asset alongside the binaries
  so `curl … | bash` works against a tagged Release URL.
- **End-to-end mTLS handshake regression test**
  (`crates/transport/tests/mtls_handshake.rs`). Spins up an
  in-process tonic AgentChannel server bound to a random loopback
  port, with a per-test ed25519 PKI, and asserts both the
  pinned-root happy path and the wrong-pin negative path. Replaces
  the testcontainers-based plan because the in-process harness is
  faster, deterministic, and runs in CI without docker.

### Fixed (production bugs surfaced by the new harness)

- **ALPN was double-set under hyper-rustls 0.27.** The transport
  client config pre-loaded `h2` into `rustls::ClientConfig.alpn_protocols`
  and *then* called `HttpsConnectorBuilder::enable_http2()`. The
  newer hyper-rustls panics with "ALPN protocols should not be
  pre-defined" in that case. ALPN is now installed exclusively by
  `enable_http2()`. Without the integration test, this would have
  panicked the daemon on first connect post-deploy.
- **tonic 0.12 rejected the custom mTLS connector.** tonic wraps
  every custom connector in its own TLS gate that refuses
  `https://` URIs unless `Endpoint::tls_config(...)` is set — but
  tonic's own `ClientTlsConfig` exposes no hook for injecting a
  custom rustls `ServerCertVerifier`, which is non-negotiable for
  the daemon's pinning model. The transport now hands tonic an
  `http://` URI and wraps the underlying hyper-rustls connector in
  a `ForceHttps` adapter that rewrites the scheme back to `https`
  before dispatch — net effect: tonic believes the connection is
  plaintext, hyper-rustls always TLS-upgrades, and our pinned
  verifier runs on every handshake.
- **Better connect-error reporting.** `tonic::transport::Error`'s
  `Display` collapses to a generic "transport error". The transport
  client now walks the `std::error::Error::source` chain so the
  underlying TLS / IO reason makes it into logs and audit records.

### Changed

- Workspace `rust-version` raised from `1.82` to `1.88` to track
  the floors imposed by transitive dependencies (`clap_lex@1.1.0`
  needs edition2024, `time@0.3.47` needs rustc 1.88).
- Dev `Dockerfile.daemon` upgraded to `rust:1.88-slim-bookworm`
  and now installs `libprotobuf-dev` so the well-known
  `google/protobuf/*.proto` files are visible to `protoc`.
- `crates/proto`'s `build.rs` searches `/usr/include`,
  `/usr/local/include`, and `/opt/homebrew/include` for the
  well-known proto files in addition to the local proto directory,
  so builds succeed on Linux containers, Debian/Ubuntu hosts, and
  Homebrew-equipped macOS without manual `PROTOC_INCLUDE` tuning.
- The proto crate gained a `server` cargo feature (off by default)
  that compiles the tonic server stubs. Production daemon binaries
  stay client-only; integration tests opt in.
- Dev compose stack swapped the smallstep-CA bootstrap for a
  one-shot `pki-init` container (alpine + openssl). Removes the
  step-CA dependency, eliminates the read-only-mount-but-write
  contradiction in the original `wait-for-pki.sh`, and reduces
  bring-up time.

### Security

- TLS minimum version is enforced as 1.3 on both ends; downgrade
  attempts fail closed (`verify_tls12_signature` returns an error
  rather than silently accepting).
- Pinning targets the SubjectPublicKeyInfo SHA-256 of the *root*
  CA in the presented chain — leaf-only pins cause the verifier to
  reject, matching the production trust model documented in
  `docs/agent_daemon.md` §6.1.
- The dev compose `SECRET_KEY` and `step-ca` provisioner password
  are committed values and are ignored by every code path that
  refuses to start outside dev mode (the production
  `SecurityConfig` validator rejects them when
  `BASELITH_PROFILE=production`).

### Operational notes

- The daemon binary is a single static ELF / Mach-O. The
  `red-agent` GitHub Actions workflow now builds four release
  targets on every `daemon-v*` tag:

  | Target | Runner | Tooling |
  | --- | --- | --- |
  | `aarch64-apple-darwin` | macos-latest | native rustup target |
  | `x86_64-apple-darwin`  | macos-latest | native rustup target |
  | `x86_64-unknown-linux-musl`  | ubuntu-latest | `cargo-zigbuild` |
  | `aarch64-unknown-linux-musl` | ubuntu-latest | `cargo-zigbuild` |

  Plus a `lipo`-merged `universal-apple-darwin` binary and an
  aggregated `SHA256SUMS`. Artifacts are attached to the GitHub
  Release on tag push, or kept as workflow artifacts (90-day
  retention) on manual `workflow_dispatch`. SBOM generation
  (`cargo about`) and signed `.deb` / `.rpm` / notarized `.pkg`
  installers land in Phase 2.
- Subtree publish: `scripts/release_redagent_daemon.sh --dry-run`
  to inspect the split SHA without pushing,
  `scripts/release_redagent_daemon.sh` (no args) to publish to the
  default `git@github.com:baselithcore/baselith-redagent-daemon.git`
  on `main`.

### Deferred to Phase 2

- eBPF process-exec / file-open / connect tracers (linux).
- ESF process events (macOS).
- Self-update bundle pipeline (signature verification primitives
  are already present in `crates/policy`; the orchestration is
  not).
- NATS JetStream backend buffer + replay-on-restart.
- Automated cert rotation pipeline (smallstep-CA backed).

[0.1.0]: https://github.com/baselithcore/baselith-redagent-daemon/releases/tag/v0.1.0
