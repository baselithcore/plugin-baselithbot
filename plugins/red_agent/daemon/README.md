# baselith-redagent-daemon

Endpoint daemon that runs on customer hosts and production servers,
talking to the `red_agent` plugin in BaselithCore via a single mTLS
gRPC stream on port 443.

## Status

**Phase 1 (MVP) — feature-complete on this branch.** All crates are
wired and tested:

* `transport` — pinned-root mTLS 1.3 channel (rustls + hyper-rustls,
  custom `ServerCertVerifier`); covered by an in-process integration
  test that issues a fresh ed25519 PKI per run, spins up a tonic
  server bound to a random loopback port, and asserts both the happy
  path *and* a wrong-pin negative case fail closed
  (`crates/transport/tests/mtls_handshake.rs`).
* `keystore` — OS-native (Keychain / kernel keyring) with an
  argon2id + chacha20-poly1305 file fallback for headless boxes.
* `collector` — process / package / users / listeners inventory
  collectors (eBPF / ESF arrive in Phase 2).
* `executor` — sandboxed local-scanner runner (landlock /
  sandbox-exec).
* `policy` — ed25519 signed-bundle verifier with monotonic version
  pinning + clock-skew tolerance.
* `daemon` — connect → enroll → heartbeat → telemetry loop with
  exponential backoff and identity persistence.

Smoke validation is automated end-to-end via the dev compose stack
under [`dev/`](dev/) — see *Local development stack* below.

## Repository model

This directory is the **source of truth**. The standalone repo
`baselith-redagent-daemon` is populated on each release via
`git subtree split -P plugins/red_agent/daemon` and force-pushed.
All edits land here first — never commit directly to the standalone
repo (any non-subtree commit there will be overwritten on the next
release).

The `agent.proto` schema lives at
`plugins/red_agent/proto/agent.proto` (one level up). Both the
Python backend (`grpcio-tools`) and this Rust workspace
(`tonic-build`) consume the same file so the wire contract cannot
drift.

## Layout

```text
daemon/
├── Cargo.toml              # workspace
├── crates/
│   ├── daemon/             # binary entrypoint, tokio runtime, lifecycle
│   ├── proto/              # tonic-build output for agent.proto
│   ├── transport/          # mTLS gRPC client + reconnect/backoff
│   ├── collector/          # telemetry sources (eBPF linux, ESF macOS)
│   ├── executor/           # local scanner runner, sandboxed
│   ├── policy/             # signed-bundle verification + rule eval
│   └── keystore/           # OS-keychain / kernel-keyring abstraction
├── platform/
│   ├── linux/systemd/      # baselith-redagent.service + apparmor profile
│   └── macos/launchd/      # com.baselith.redagent.plist + entitlements
└── README.md (this file)
```

## Install on a host (operators)

One-shot installer auto-detects OS+arch, downloads the matching
binary from the GitHub Release, verifies SHA-256, writes config +
pinned CA fingerprint, redeems the enrollment token, and registers
a systemd / launchd unit:

```sh
curl -fsSL https://baselithcore.xyz/dev/install.sh \
    | sudo bash -s -- \
        --backend     https://red-agent.example.com:443 \
        --fingerprint <SPKI-SHA256-HEX> \
        --token       <ENROLLMENT_TOKEN>
```

The installer downloads the right per-target binary from
`https://baselithcore.xyz/dev/<TARGET>` (rolling-release endpoint
maintained by the `red-agent` CI), verifies its SHA-256 against
`https://baselithcore.xyz/dev/SHA256SUMS`, and proceeds. Override
the base URL with `--base-url https://internal.example.com/redagent`
or `BASE_URL=` env for self-hosted mirrors.

Air-gapped hosts: `scp` the binary first, then point the installer
at it via `BINARY=` env:

```sh
sudo BINARY=./baselith-redagent-daemon-x86_64-unknown-linux-musl \
    ./install.sh \
        --backend     https://red-agent.example.com:443 \
        --fingerprint <SPKI-SHA256-HEX> \
        --token       <ENROLLMENT_TOKEN>
```

Flags: `--no-service` (skip systemd/launchd), `--prefix` (custom
install path, default `/usr/local/bin`), `--version vX.Y.Z` (pin a
specific release). The installer is dual-source-of-truth — shipped
alongside the binaries in every GH Release and tracked in this
repo at [`scripts/install.sh`](scripts/install.sh).

Tail logs:

* Linux — `journalctl -u baselith-redagent -f`
* macOS — `tail -f /var/log/baselith-redagent.log`

## Build (developers)

```sh
cd plugins/red_agent/daemon
cargo build --release
cargo test --workspace        # runs unit + integration tests
```

The integration tests under `crates/transport/tests/` enable the
proto crate's `server` feature so a tonic AgentChannel server can be
spun up in-process. Production builds keep the proto crate
client-only — the daemon binary never links the server stubs.

## Local development stack

`dev/docker-compose.yml` brings up the full daemon ↔ envoy ↔ backend
chain end-to-end on a developer box:

```sh
cd plugins/red_agent/daemon
docker compose -f dev/docker-compose.yml up -d --build
docker compose -f dev/docker-compose.yml logs -f daemon
```

What the stack does:

1. `pki-init` (alpine + openssl) generates an ed25519 dev CA, a
   backend service cert signed by the CA, and the SPKI fingerprint
   the daemon pins. All three land in the `dev_pki` named volume so
   the backend, envoy, and daemon services consume them on startup.
2. `postgres` boots and `backend` runs alembic migrations against
   it. Bringing the backend fully online additionally needs Redis
   and FalkorDB — those are intentionally out of scope for the
   daemon's smoke harness; running the dev stack against the
   monorepo's full `docker compose up` provides them.
3. `envoy` terminates mTLS on `:443` (TLS 1.3, client cert
   required) and forwards plaintext HTTP/2 to the backend's gRPC
   port `50443`.
4. `daemon` boots, opens its keystore, and either runs (if an
   identity is already persisted) or exits with the documented
   "no enrolled identity" error. The first-run enrollment is a
   manual step:

   ```sh
   # operator action: mint a token via the REST API, then:
   docker compose -f dev/docker-compose.yml exec daemon \
     baselith-redagent-daemon enroll --token <TOKEN>
   ```

Tear down with `docker compose -f dev/docker-compose.yml down -v`.

## Release pipeline

[`.github/workflows/red-agent.yml`](../../../.github/workflows/red-agent.yml)
fires on `daemon-v*` tag push (and on `workflow_dispatch`). Three
jobs cross-compile and bundle:

| Target | Runner | Tooling | Output |
| --- | --- | --- | --- |
| `aarch64-apple-darwin` | macos-latest | native rustup | static Mach-O |
| `x86_64-apple-darwin`  | macos-latest | native rustup | static Mach-O |
| `x86_64-unknown-linux-musl`  | ubuntu-latest | `cargo-zigbuild` (zig 0.16) | static-pie ELF |
| `aarch64-unknown-linux-musl` | ubuntu-latest | `cargo-zigbuild` | static ELF |
| `universal-apple-darwin` | macos-latest | `lipo` of the two darwin binaries | fat Mach-O |

`SHA256SUMS` covers all five binaries plus `install.sh`. On tag
push the bundle is attached to a GitHub Release; on
`workflow_dispatch` it stays as a workflow artifact (90-day
retention) so operators can inspect before promoting.

To cut a release:

```sh
git tag daemon-v0.1.0 -m "Red Agent daemon v0.1.0"
git push origin daemon-v0.1.0
# CI builds 5 binaries + installer + checksums and publishes the GH Release.
# Then mirror to the standalone repo:
scripts/release_redagent_daemon.sh --dry-run    # inspect split SHA
scripts/release_redagent_daemon.sh              # force-push subtree
```

Local cross-compile (no CI):

```sh
# Native macOS (arm64 + intel + universal):
cargo build --release --target aarch64-apple-darwin --bin baselith-redagent-daemon
cargo build --release --target x86_64-apple-darwin  --bin baselith-redagent-daemon
lipo -create \
    target/aarch64-apple-darwin/release/baselith-redagent-daemon \
    target/x86_64-apple-darwin/release/baselith-redagent-daemon \
    -output baselith-redagent-daemon-universal-apple-darwin

# Linux musl from a macOS host (zig + cargo-zigbuild, no docker):
brew install zig protobuf
cargo install cargo-zigbuild --locked
cargo zigbuild --release --target x86_64-unknown-linux-musl  --bin baselith-redagent-daemon
cargo zigbuild --release --target aarch64-unknown-linux-musl --bin baselith-redagent-daemon
```

ESF signing + notarization for the macOS endpoint security entitlement
land in Phase 2 alongside `.deb` / `.rpm` / `.pkg` packaging.

## Security baseline

* TLS 1.3 only, ed25519 client cert, root CA fingerprint pinned at
  install time.
* Single outbound connection on port 443; never listens.
* Private key persisted in the OS keystore (Keychain / kernel
  keyring); never written to disk in plaintext.
* All scanner binaries executed under `landlock` (linux) /
  `sandbox-exec` (macOS) with cgroup v2 / posix_spawn resource caps.
* Self-update bundles verified against an ed25519 backend key
  pinned at install before any `exec`.

## Phase roadmap

| Phase | Scope | Status |
| --- | --- | --- |
| 1 (MVP) | Skeleton, mTLS handshake, `AgentHello`, heartbeat, package inventory, local scanner exec, ed25519 signed-bundle verification | **complete on `red-agent` branch — v0.1.0** |
| 2 | eBPF (linux) `tracepoint:sched:sched_process_exec`, ESF (macOS) `ES_EVENT_TYPE_NOTIFY_EXEC`, NATS JetStream backend buffer, automated cert rotation | planned |
| 3 | ClickHouse / Loki telemetry tier, SPIRE workload identity (>1 k fleet), regional NATS leaf nodes, multi-region routing | planned |

See [`plugins/red_agent/docs/agent_daemon.md`](../docs/agent_daemon.md)
for the full architecture spec.
