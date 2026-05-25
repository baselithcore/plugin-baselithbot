#!/usr/bin/env bash
# Sync built daemon binaries + installer to the baselith-core-web
# repo's public/dev/ directory so they reach baselithcore.xyz/dev/*
# via the next Vercel deploy.
#
# Workflow:
#
#   1. Build the binaries locally (or pull the CI artifacts):
#        cd plugins/red_agent/daemon
#        cargo build --release --target aarch64-apple-darwin --bin baselith-redagent-daemon
#        cargo build --release --target x86_64-apple-darwin  --bin baselith-redagent-daemon
#        cargo zigbuild --release --target x86_64-unknown-linux-musl  --bin baselith-redagent-daemon
#        cargo zigbuild --release --target aarch64-unknown-linux-musl --bin baselith-redagent-daemon
#
#   2. Run this script — it stages bare-name + version-prefixed
#      copies, the installer, and the SHA256SUMS file under
#      public/dev/ in the web repo.
#
#   3. From the web repo: commit + push (Vercel auto-deploys on push
#      to main).
#
# Required:
#   --version vX.Y.Z       daemon version label (used in versioned filenames)
#
# Optional:
#   --web PATH             path to the baselith-core-web repo
#                          (default: ../../../baselith/baselith-core-web)
#   --target-dir PATH      override the destination dir
#                          (default: <web>/public/dev)
#   --dry-run              print actions without copying

set -euo pipefail

DAEMON_VERSION=
WEB_REPO="${WEB_REPO:-/Users/giovanni/dev/personale/baselith/baselith-core-web}"
TARGET_DIR=
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version)    DAEMON_VERSION="$2"; shift 2 ;;
        --web)        WEB_REPO="$2"; shift 2 ;;
        --target-dir) TARGET_DIR="$2"; shift 2 ;;
        --dry-run)    DRY_RUN=1; shift ;;
        -h|--help)
            sed -n '2,28p' "$0"
            exit 0
            ;;
        *)
            echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "${DAEMON_VERSION}" ]]; then
    echo "ERROR: --version vX.Y.Z is required" >&2
    exit 2
fi
if ! [[ "${DAEMON_VERSION}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
    echo "ERROR: --version must look like vX.Y.Z (got '${DAEMON_VERSION}')" >&2
    exit 2
fi

DAEMON_ROOT="$(cd "$(dirname "$0")/.." && pwd)"     # plugins/red_agent/daemon
TARGET_DIR="${TARGET_DIR:-${WEB_REPO}/public/dev}"

if [[ ! -d "${WEB_REPO}" ]]; then
    echo "ERROR: web repo not found at ${WEB_REPO}" >&2
    exit 1
fi

TARGETS=(
    aarch64-apple-darwin
    x86_64-apple-darwin
    x86_64-unknown-linux-musl
    aarch64-unknown-linux-musl
)

echo "[publish] staging into ${TARGET_DIR}"
[[ "${DRY_RUN}" -eq 0 ]] && mkdir -p "${TARGET_DIR}"

# Per-target binaries: bare name (used by install.sh) + versioned copy
# (archival / SHA256SUMS audit).
for tgt in "${TARGETS[@]}"; do
    src="${DAEMON_ROOT}/target/${tgt}/release/baselith-redagent-daemon"
    if [[ ! -f "${src}" ]]; then
        echo "ERROR: missing artifact: ${src}" >&2
        echo "       run: cargo build --release --target ${tgt} --bin baselith-redagent-daemon" >&2
        exit 1
    fi
    bare="${TARGET_DIR}/${tgt}"
    versioned="${TARGET_DIR}/baselith-redagent-daemon-${DAEMON_VERSION}-${tgt}"
    echo "  ${tgt}"
    if [[ "${DRY_RUN}" -eq 0 ]]; then
        install -m 0755 "${src}" "${bare}"
        install -m 0755 "${src}" "${versioned}"
    fi
done

# Universal macOS via lipo (only if both darwin builds present).
if [[ -f "${DAEMON_ROOT}/target/aarch64-apple-darwin/release/baselith-redagent-daemon" \
   && -f "${DAEMON_ROOT}/target/x86_64-apple-darwin/release/baselith-redagent-daemon" ]]; then
    universal_bare="${TARGET_DIR}/universal-apple-darwin"
    universal_v="${TARGET_DIR}/baselith-redagent-daemon-${DAEMON_VERSION}-universal-apple-darwin"
    echo "  universal-apple-darwin (lipo)"
    if [[ "${DRY_RUN}" -eq 0 ]]; then
        lipo -create \
            "${DAEMON_ROOT}/target/aarch64-apple-darwin/release/baselith-redagent-daemon" \
            "${DAEMON_ROOT}/target/x86_64-apple-darwin/release/baselith-redagent-daemon" \
            -output "${universal_bare}"
        chmod 0755 "${universal_bare}"
        cp "${universal_bare}" "${universal_v}"
    fi
fi

# Installer is the source of truth — copy fresh every time.
echo "  install.sh"
[[ "${DRY_RUN}" -eq 0 ]] && \
    install -m 0755 "${DAEMON_ROOT}/scripts/install.sh" "${TARGET_DIR}/install.sh"

# Aggregate SHA256SUMS over every staged file.
if [[ "${DRY_RUN}" -eq 0 ]]; then
    (cd "${TARGET_DIR}" && \
        shasum -a 256 \
            aarch64-apple-darwin \
            x86_64-apple-darwin \
            universal-apple-darwin \
            x86_64-unknown-linux-musl \
            aarch64-unknown-linux-musl \
            "baselith-redagent-daemon-${DAEMON_VERSION}-"* \
            install.sh \
        > SHA256SUMS)
    echo "[publish] SHA256SUMS:"
    sed 's/^/  /' "${TARGET_DIR}/SHA256SUMS"
fi

echo "[publish] done."
echo "next:"
echo "  cd ${WEB_REPO}"
echo "  git add public/dev"
echo "  git commit -m 'chore(dev): publish baselith-redagent-daemon ${DAEMON_VERSION}'"
echo "  git push   # vercel auto-deploys on push"
