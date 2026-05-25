#!/usr/bin/env bash
# baselith-redagent-daemon — one-shot installer.
#
# Downloads the right release binary for this host from the public
# distribution endpoint, verifies its SHA-256, installs it to
# /usr/local/bin, writes a minimal config, pins the backend CA
# fingerprint, optionally enrolls the daemon with a token, and
# registers a systemd/launchd unit.
#
# Default download base: https://baselithcore.xyz/dev
# Per-target URL:        https://baselithcore.xyz/dev/<TARGET>
# Checksum file:         https://baselithcore.xyz/dev/SHA256SUMS
#
# Usage (interactive):
#   curl -fsSL https://baselithcore.xyz/dev/install.sh \
#       | sudo bash -s -- \
#           --backend https://red-agent.example.com:443 \
#           --fingerprint 46b1...3770 \
#           --token <ENROLLMENT_TOKEN>
#
# Usage (offline / from a copied binary):
#   sudo BINARY=./baselith-redagent-daemon-x86_64-unknown-linux-musl \
#        ./install.sh --backend ... --fingerprint ... --token ...
#
# Required:
#   --backend URL          gRPC endpoint (https://host:port)
#   --fingerprint HEX      SPKI SHA-256 of the backend CA (64 hex chars)
#
# Optional:
#   --token TOKEN          one-shot enrollment token (skip to enroll later)
#   --no-service           install binary + config, skip service unit
#   --prefix PATH          install prefix (default: /usr/local/bin)
#   --base-url URL         download base (default: https://baselithcore.xyz/dev)
#   --no-checksum          skip SHA256SUMS verification (NOT for production)
#
# Environment overrides:
#   BINARY=/path/to/file   use a local binary instead of downloading
#   BASE_URL=https://...   same as --base-url

set -euo pipefail

# ─── defaults ────────────────────────────────────────────────────────
BINARY=${BINARY:-}
BASE_URL=${BASE_URL:-https://baselithcore.xyz/dev}
PREFIX=/usr/local/bin
BACKEND=
FINGERPRINT=
TOKEN=
INSTALL_SERVICE=1
VERIFY_CHECKSUM=1

# ─── arg parsing ─────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --backend)     BACKEND="$2"; shift 2 ;;
        --fingerprint) FINGERPRINT="$2"; shift 2 ;;
        --token)       TOKEN="$2"; shift 2 ;;
        --no-service)  INSTALL_SERVICE=0; shift ;;
        --prefix)      PREFIX="$2"; shift 2 ;;
        --base-url)    BASE_URL="$2"; shift 2 ;;
        --no-checksum) VERIFY_CHECKSUM=0; shift ;;
        -h|--help)
            sed -n '2,38p' "$0"
            exit 0
            ;;
        *)
            echo "unknown arg: $1" >&2
            exit 2
            ;;
    esac
done

if [[ -z "${BACKEND}" || -z "${FINGERPRINT}" ]]; then
    echo "ERROR: --backend and --fingerprint are required" >&2
    exit 2
fi

if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: must run as root (or via sudo)" >&2
    exit 2
fi

if ! [[ "${FINGERPRINT}" =~ ^[0-9a-f]{64}$ ]]; then
    echo "ERROR: --fingerprint must be 64 lowercase hex chars" >&2
    exit 2
fi

# Cross-platform SHA-256 helper: linux ships `sha256sum`, macOS ships
# `shasum -a 256`. Returns just the hex digest, no filename column.
_sha256() {
    if command -v sha256sum >/dev/null; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

# ─── target detection ────────────────────────────────────────────────
uname_s="$(uname -s)"
uname_m="$(uname -m)"
case "${uname_s}-${uname_m}" in
    Linux-x86_64)   TARGET=x86_64-unknown-linux-musl ;;
    Linux-aarch64)  TARGET=aarch64-unknown-linux-musl ;;
    Linux-arm64)    TARGET=aarch64-unknown-linux-musl ;;
    Darwin-arm64)   TARGET=aarch64-apple-darwin ;;
    Darwin-x86_64)  TARGET=x86_64-apple-darwin ;;
    *)
        echo "ERROR: unsupported platform: ${uname_s}-${uname_m}" >&2
        exit 1
        ;;
esac
echo "[install] detected target: ${TARGET}"

# ─── obtain binary ───────────────────────────────────────────────────
TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

if [[ -n "${BINARY}" ]]; then
    echo "[install] using local binary: ${BINARY}"
    cp "${BINARY}" "${TMPDIR}/baselith-redagent-daemon"
else
    # The distribution endpoint serves one binary per target under
    # ${BASE_URL}/<target> and an aggregated SHA256SUMS at the same
    # level. URL is constant; latest version is whatever the server
    # currently exposes (rolling-release model).
    URL="${BASE_URL%/}/${TARGET}"
    SUMS_URL="${BASE_URL%/}/SHA256SUMS"

    echo "[install] downloading from ${URL}"
    if ! curl -fSL --retry 3 -o "${TMPDIR}/baselith-redagent-daemon" "${URL}"; then
        echo "ERROR: download failed for ${URL}" >&2
        exit 1
    fi

    if [[ "${VERIFY_CHECKSUM}" -eq 1 ]]; then
        echo "[install] fetching ${SUMS_URL}"
        if ! curl -fSL --retry 3 -o "${TMPDIR}/SHA256SUMS" "${SUMS_URL}"; then
            echo "ERROR: SHA256SUMS download failed; rerun with --no-checksum to skip" >&2
            exit 1
        fi
        echo "[install] verifying SHA-256 for target ${TARGET}"
        # SHA256SUMS lines look like: "<hex>  <TARGET>" or
        # "<hex>  baselith-redagent-daemon-<TARGET>" depending on how
        # the upload pipeline names files. Match either.
        actual="$(_sha256 "${TMPDIR}/baselith-redagent-daemon")"
        expected="$(awk -v t="${TARGET}" '
            $2 == t || $2 == "baselith-redagent-daemon-" t { print $1; exit }
        ' "${TMPDIR}/SHA256SUMS")"
        if [[ -z "${expected}" ]]; then
            echo "ERROR: no SHA-256 entry for ${TARGET} in SHA256SUMS" >&2
            exit 1
        fi
        if [[ "${actual}" != "${expected}" ]]; then
            echo "ERROR: checksum mismatch (expected ${expected}, got ${actual})" >&2
            exit 1
        fi
        echo "[install] SHA-256 verified"
    else
        echo "[install] WARNING: --no-checksum set, skipping SHA-256 verification"
    fi
fi

# ─── install binary + config ─────────────────────────────────────────
echo "[install] writing binary to ${PREFIX}/baselith-redagent-daemon"
install -m 0755 "${TMPDIR}/baselith-redagent-daemon" \
    "${PREFIX}/baselith-redagent-daemon"

# macOS: strip quarantine if present (no-op on Linux).
if [[ "${uname_s}" == "Darwin" ]]; then
    xattr -d com.apple.quarantine "${PREFIX}/baselith-redagent-daemon" 2>/dev/null || true
fi

install -d -m 0755 /etc/baselith /var/lib/baselith

echo "${FINGERPRINT}" > /etc/baselith/agent-ca.fingerprint
chmod 0644 /etc/baselith/agent-ca.fingerprint

cat > /etc/baselith/redagent.toml <<EOF
# Generated by baselith-redagent-daemon installer.
backend_endpoint = "${BACKEND}"
protocol_version = 1
root_ca_fingerprint_path = "/etc/baselith/agent-ca.fingerprint"
keystore_id = "baselith-redagent-default"
telemetry_buffer_path = "/var/lib/baselith/telemetry.sqlite"
EOF
chmod 0644 /etc/baselith/redagent.toml

echo "[install] daemon version: $("${PREFIX}/baselith-redagent-daemon" --version 2>/dev/null || echo unknown)"

# ─── enroll (optional) ───────────────────────────────────────────────
if [[ -n "${TOKEN}" ]]; then
    echo "[install] redeeming enrollment token"
    "${PREFIX}/baselith-redagent-daemon" enroll --token "${TOKEN}"
else
    echo "[install] skipping enrollment (no --token); run later:"
    echo "          ${PREFIX}/baselith-redagent-daemon enroll --token <TOKEN>"
fi

# ─── service unit ────────────────────────────────────────────────────
if [[ "${INSTALL_SERVICE}" -eq 0 ]]; then
    echo "[install] --no-service set, skipping service registration"
    exit 0
fi

case "${uname_s}" in
    Linux)
        if ! command -v systemctl >/dev/null; then
            echo "[install] systemctl not found, skipping service unit"
            exit 0
        fi
        echo "[install] writing systemd unit"
        cat > /etc/systemd/system/baselith-redagent.service <<'EOF'
[Unit]
Description=Baselith Red Agent endpoint daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/baselith-redagent-daemon run
Restart=on-failure
RestartSec=5
User=root
Environment=BASELITH_REDAGENT_CONFIG=/etc/baselith/redagent.toml
Environment=RUST_LOG=info,baselith_redagent=info
# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/baselith /etc/baselith
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
        systemctl daemon-reload
        if [[ -n "${TOKEN}" ]]; then
            systemctl enable --now baselith-redagent.service
            echo "[install] service started — tail with:"
            echo "          journalctl -u baselith-redagent -f"
        else
            systemctl enable baselith-redagent.service
            echo "[install] service enabled but not started (no token)."
            echo "          enroll first, then: systemctl start baselith-redagent"
        fi
        ;;
    Darwin)
        echo "[install] writing launchd plist"
        cat > /Library/LaunchDaemons/com.baselith.redagent.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.baselith.redagent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/baselith-redagent-daemon</string>
        <string>run</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>BASELITH_REDAGENT_CONFIG</key>
        <string>/etc/baselith/redagent.toml</string>
        <key>RUST_LOG</key>
        <string>info,baselith_redagent=info</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>/var/log/baselith-redagent.log</string>
    <key>StandardErrorPath</key><string>/var/log/baselith-redagent.log</string>
</dict>
</plist>
EOF
        chmod 0644 /Library/LaunchDaemons/com.baselith.redagent.plist
        if [[ -n "${TOKEN}" ]]; then
            launchctl load /Library/LaunchDaemons/com.baselith.redagent.plist
            echo "[install] service loaded — tail with:"
            echo "          tail -f /var/log/baselith-redagent.log"
        else
            echo "[install] plist installed, not loaded (no token)."
            echo "          enroll first, then:"
            echo "          launchctl load /Library/LaunchDaemons/com.baselith.redagent.plist"
        fi
        ;;
    *)
        echo "[install] unknown OS, skipping service unit"
        ;;
esac

echo "[install] done."
