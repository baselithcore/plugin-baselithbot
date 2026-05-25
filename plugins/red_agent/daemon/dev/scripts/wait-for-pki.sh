#!/usr/bin/env bash
# Bootstrap the dev PKI: provision the agent CA + backend service
# cert from step-ca, write the pinned-fingerprint file, and exit.
# Intended to run as a one-shot init step inside the backend
# container before `python backend.py` starts.

set -euo pipefail

PKI_DIR=${PKI_DIR:-/etc/baselith/ca}
STEP_CA=${STEP_CA:-https://step-ca:9000}
PROVISIONER_PASSWORD=${STEPCA_PASSWORD:-dev-password-change-me}

mkdir -p "${PKI_DIR}"

if [[ ! -f "${PKI_DIR}/agent-ca.crt" ]]; then
    echo "fetching root CA from step-ca"
    until step ca root --ca-url "${STEP_CA}" "${PKI_DIR}/agent-ca.crt"; do
        echo "step-ca not ready, retrying"
        sleep 2
    done
fi

if [[ ! -f "${PKI_DIR}/agent-ca.key" ]]; then
    echo "warning: agent-ca.key not present — production deployments fetch from KMS"
fi

if [[ ! -f "${PKI_DIR}/agent-ca.fingerprint" ]]; then
    echo "computing pinned fingerprint"
    openssl x509 -in "${PKI_DIR}/agent-ca.crt" -pubkey -noout \
        | openssl pkey -pubin -outform DER \
        | sha256sum \
        | awk '{print $1}' \
        > "${PKI_DIR}/agent-ca.fingerprint"
fi

echo "PKI ready under ${PKI_DIR}"
