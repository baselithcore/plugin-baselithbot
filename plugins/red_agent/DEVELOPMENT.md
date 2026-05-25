# Red Agent — Development Guide

How to extend the Red Agent plugin: scanners, daemon, UI, dev compose.

> **Status:** Phase 1 complete (orchestrator, fleet, signed-policy
> bundles, host targets, endpoint daemon `v0.1.0`). See
> [README.md](README.md) §Status and
> [daemon/CHANGELOG.md](daemon/CHANGELOG.md) for the shipped surface.

## 1. Adding a New Scanner

Every scanner in the Red Agent is implemented as a Python adapter that executes a binary within a hardened Docker sandbox.

### Step 1: Create the Scanner Adapter

Create a new file in `plugins/red_agent/scanners/[name].py`.

```python
from plugins.red_agent.models import Finding, ScanIntensity, Target, Severity
from plugins.red_agent.scanners.base import Scanner, ScannerKind

class MyScanner(Scanner):
    name = "myscanner"
    kind = ScannerKind.DAST
    image = "my-docker-repo/myscanner:latest"
    supports_intensity = (ScanIntensity.PASSIVE, ScanIntensity.ACTIVE)

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        # 1. Prepare arguments
        argv = ["myscanner", "--url", target.value]
        if intensity == ScanIntensity.ACTIVE:
            argv.append("--aggressive")

        # 2. Execute via SandboxRunner (never use subprocess directly!)
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            requires_network=self.requires_network
        )

        # 3. Parse output and return Finding objects
        findings = self._parse(result.stdout)
        return findings

    def _parse(self, output: str) -> list[Finding]:
        # Implement parsing logic here
        return []
```

### Step 2: Register the Scanner

Add your scanner to the registry in `plugins/red_agent/scanners/__init__.py`.

```python
from plugins.red_agent.scanners.nmap import NmapScanner
from plugins.red_agent.scanners.myscanner import MyScanner

REGISTRY = {
    "nmap": NmapScanner,
    "myscanner": MyScanner,
    # ...
}
```

## 2. Working with the Daemon (Rust)

The endpoint daemon is a Cargo workspace under
[daemon/](daemon/) with seven crates:

| Crate | Purpose |
| --- | --- |
| `daemon` | binary entrypoint, tokio runtime, reconnect loop |
| `proto` | tonic-generated stubs (client by default; `server` feature for tests) |
| `transport` | mTLS gRPC client + pinned-root rustls verifier |
| `keystore` | Keychain / kernel-keyring / encrypted-file identity store |
| `collector` | host inventory (proc, pkg, users, listeners) |
| `executor` | sandboxed scanner runner (landlock / sandbox-exec) |
| `policy` | ed25519 signed-bundle verifier |

### Prerequisites

- Rust toolchain `>= 1.88` (workspace `rust-version`)
- `protoc` + the well-known `.proto` files (Debian:
  `apt install protobuf-compiler libprotobuf-dev`; macOS Homebrew:
  `brew install protobuf` — already covers `/opt/homebrew/include`)

### Build & test

```bash
cd plugins/red_agent/daemon
cargo build --release
cargo test --workspace        # unit + integration tests
cargo clippy --workspace --all-targets -- -D warnings
```

The integration test
[`crates/transport/tests/mtls_handshake.rs`](daemon/crates/transport/tests/mtls_handshake.rs)
spins up an in-process tonic AgentChannel server bound to a random
loopback port, generates a fresh ed25519 PKI per run, and asserts
both the pinned-root happy path and a wrong-pin negative path. It
enables the `server` feature on the `proto` crate; production daemon
binaries stay client-only.

### Local end-to-end stack

`daemon/dev/docker-compose.yml` brings up the full daemon ↔ envoy ↔
backend chain on a developer box:

```bash
cd plugins/red_agent/daemon
docker compose -f dev/docker-compose.yml up -d --build
docker compose -f dev/docker-compose.yml logs -f daemon
```

The `pki-init` container (alpine + openssl) generates an ed25519 dev
CA, a backend service cert signed by the CA, and the SPKI fingerprint
pinned by the daemon. Bringing the backend fully online additionally
needs Redis + FalkorDB — those are out of scope for the daemon's
smoke harness.

### CA configuration for the backend

The Python `RedAgentPlugin` reads:

- `RED_AGENT_CA_CERT_PATH` — PEM cert
- `RED_AGENT_CA_KEY_PATH` — PEM ed25519 PKCS#8 key

When unset, enrollment endpoints return 503 and startup logs
`red_agent.ca.unconfigured`. Generate a dev CA quickly:

```bash
mkdir -p ~/.baselith/red-agent-ca && cd ~/.baselith/red-agent-ca
openssl genpkey -algorithm ed25519 -out agent-ca.key
openssl req -x509 -new -key agent-ca.key -days 365 \
    -subj "/CN=BaselithRedAgentDevCA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -out agent-ca.crt
chmod 0600 agent-ca.key
```

Production deployments back the key with Vault PKI / KMS — never
this file path.

### Protocol Changes

The wire contract is defined in `plugins/red_agent/proto/agent.proto`.
If you modify this file:

1. Rebuild the Rust crates: `cargo build` in `daemon/`.
2. Re-generate Python stubs (if necessary, though the plugin usually
   does this dynamically or via a script).
3. Bump `protocol_version` only on wire-incompatible changes (see
   header comment in `agent.proto`).

### Releasing the daemon

The monorepo is the source of truth. The standalone
[`baselith-redagent-daemon`](https://github.com/baselithcore/baselith-redagent-daemon)
GitHub repo is output-only, populated via
`scripts/release_redagent_daemon.sh` (`--dry-run` to inspect the
split SHA without pushing). Never commit directly to the standalone
repo — any non-subtree commit there is overwritten on the next
release.

#### CI release pipeline

[`.github/workflows/red-agent.yml`](../../.github/workflows/red-agent.yml)
gates every PR with `python` + `ui` + `rust` lint/test jobs. On top
of those, three release jobs cross-compile and bundle the daemon
binary:

| Job | Runner | Targets | Tooling |
| --- | --- | --- | --- |
| `daemon-build-macos` | `macos-latest` | `aarch64-apple-darwin`, `x86_64-apple-darwin` | native rustup target |
| `daemon-build-linux` | `ubuntu-latest` | `x86_64-unknown-linux-musl`, `aarch64-unknown-linux-musl` | `cargo-zigbuild` (zig 0.16) |
| `daemon-bundle` | `macos-latest` | combined release dir + `lipo` universal binary + `SHA256SUMS` | `lipo`, `shasum` |

Triggers:

- Tag push matching `daemon-v*` (`daemon-v0.1.0`, `daemon-v0.2.0`, …)
  → builds + uploads artifacts + publishes a GitHub Release with the
  binaries attached.
- Manual `workflow_dispatch` → same builds + artifacts, no Release
  (lets operators inspect the bundle before promoting).
- Pull requests and ordinary branch pushes skip the release jobs to
  keep CI turnaround short — they still run `python` / `ui` / `rust`.

To cut a release locally:

```bash
git tag daemon-v0.1.0 -m "Red Agent daemon v0.1.0"
git push origin daemon-v0.1.0
# CI builds 4 targets + universal lipo, attaches them to the GH Release.
# Then mirror the daemon source to the standalone repo:
scripts/release_redagent_daemon.sh --dry-run    # inspect split SHA
scripts/release_redagent_daemon.sh              # force-push to subtree
```

The aggregated bundle ships as the
`baselith-redagent-daemon-vX.Y.Z` artifact (90-day retention) and
mirrors the layout of `~/dist/` produced by the local build script.

#### Installing on hosts

[`daemon/scripts/install.sh`](daemon/scripts/install.sh) is the
operator-facing one-shot installer. The script:

1. Detects `uname -s` / `uname -m` → resolves to one of the four
   release targets.
2. Downloads the binary from
   `https://baselithcore.xyz/dev/<TARGET>` (rolling-release
   endpoint mirroring the latest CI artifacts) and the aggregated
   `https://baselithcore.xyz/dev/SHA256SUMS`.
3. Verifies SHA-256, fail-closed on mismatch.
4. `install -m 0755` to `/usr/local/bin` (custom path via
   `--prefix`); strips `com.apple.quarantine` xattr on macOS so
   Gatekeeper doesn't block first-run.
5. Writes `/etc/baselith/redagent.toml` and the
   `/etc/baselith/agent-ca.fingerprint` pin file.
6. Redeems an enrollment token if `--token` was passed.
7. Registers a hardened systemd unit (Linux) or launchd plist
   (macOS) and starts the daemon.

Operator invocation:

```bash
curl -fsSL https://baselithcore.xyz/dev/install.sh \
    | sudo bash -s -- \
        --backend     https://red-agent.example.com:443 \
        --fingerprint <SPKI-SHA256-HEX> \
        --token       <ENROLLMENT_TOKEN>
```

Air-gapped path (binary already `scp`'d to the host):

```bash
sudo BINARY=./baselith-redagent-daemon-x86_64-unknown-linux-musl \
    ./install.sh --backend https://… --fingerprint … --token …
```

Useful env / flag overrides:

| Flag / env | Purpose |
| --- | --- |
| `BINARY=PATH` | use a local binary instead of downloading |
| `BASE_URL=URL` / `--base-url URL` | mirror or staging endpoint (default `https://baselithcore.xyz/dev`) |
| `--no-checksum` | skip SHA-256 verification (testing only) |
| `--no-service` | install binary + config only, skip systemd/launchd |
| `--prefix PATH` | override `/usr/local/bin` |

#### Publishing to baselithcore.xyz/dev

The distribution endpoint
[`https://baselithcore.xyz/dev/`](https://baselithcore.xyz/dev/) is
served from
`/Users/giovanni/dev/personale/baselith/baselith-core-web/public/dev/`
in the `baselith-core-web` repo (Vercel auto-deploys on push to main).

[`daemon/scripts/publish_to_web.sh`](daemon/scripts/publish_to_web.sh)
stages the local cargo build artifacts into that directory, including:

- bare-name copies (`aarch64-apple-darwin`, `x86_64-unknown-linux-musl`,
  …) consumed by `install.sh`
- versioned copies (`baselith-redagent-daemon-vX.Y.Z-<TARGET>`) for
  archival / audit
- a `lipo`-merged `universal-apple-darwin` macOS fat binary
- a fresh copy of `install.sh`
- aggregated `SHA256SUMS` over everything above

Local release flow:

```bash
cd plugins/red_agent/daemon
# Build whatever targets you have toolchains for:
cargo build --release --target aarch64-apple-darwin --bin baselith-redagent-daemon
cargo build --release --target x86_64-apple-darwin  --bin baselith-redagent-daemon
cargo zigbuild --release --target x86_64-unknown-linux-musl  --bin baselith-redagent-daemon
cargo zigbuild --release --target aarch64-unknown-linux-musl --bin baselith-redagent-daemon

# Stage into the web repo:
scripts/publish_to_web.sh --version v0.1.0

# Push from the web repo to trigger the Vercel deploy:
cd /Users/giovanni/dev/personale/baselith/baselith-core-web
git add public/dev
git commit -m "chore(dev): publish baselith-redagent-daemon v0.1.0"
git push
```

The endpoint follows a rolling-release model — the bare-name URLs
(`/dev/<TARGET>`) always resolve to the latest published build, so
`install.sh` doesn't need to know the version. Versioned filenames
remain available for explicit pinning.

## 3. Testing

### Mock Mode

During frontend or orchestrator development, you can bypass Docker and real scans by enabling mock mode:

```bash
RED_AGENT_USE_MOCK_SCANNERS=true
```

This uses the `MockSandboxRunner` which returns canned data defined in `mock_sandbox.py`.

### Unit Tests

Run tests using `pytest`:

```bash
pytest plugins/red_agent/tests/
```

## 4. UI Development

The UI is a React + Vite SPA in `plugins/red_agent/ui/`. Tailwind CSS
for styling, Cytoscape.js (`fcose` layout) for the Attack Surface
graph, TanStack Query for server state.

```bash
cd plugins/red_agent/ui
npm install
npm run dev          # dev server (proxy to BaselithCore on :8000)
npm run build        # tsc --noEmit + vite build → ui/dist/ (shipped in wheel)
```

Note: configure the API proxy in `vite.config.ts` to point at your
BaselithCore instance.

### Adding a new target kind

Target kinds live in
[`ui/src/lib/targets.ts`](ui/src/lib/targets.ts) (`KIND_META`,
`KIND_ORDER`) and are wired into the New Target wizard at
[`ui/src/routes/new_target/wizard_steps.tsx`](ui/src/routes/new_target/wizard_steps.tsx).
To add a kind:

1. Append to the `TargetKind` union in `lib/api.ts` and the matching
   backend `TargetKind` enum in `models.py`.
2. Add a `KIND_META` entry (label, accent, description, hint) and
   include the new key in `KIND_ORDER`.
3. Register a `KindIcon` case + extend `ConfigStep` with a branch
   that gathers the kind-specific value.
4. Update `NewTarget.tsx` state, `targetValue` memo, and
   `canContinue(2)` to validate the new branch.
5. Decide whether the value needs structured prefixing (e.g. cloud
   uses `aws:account/<id>@<region>`, host uses `agent:<uuid>`).

The `host` kind is the most recent example — see commits referencing
"feat: implement fleet management UI" + the wizard `HostConfig`
component for the canonical pattern.
