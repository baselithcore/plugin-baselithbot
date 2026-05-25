#!/usr/bin/env sh
# Bootstrap the dev PKI for the Red Agent compose stack.
#
# Generates an ed25519 agent CA, an ed25519 backend service cert
# signed by the CA, and the SPKI fingerprint the daemon pins. All
# outputs land under $PKI_DIR (defaults to /pki) so the volume is
# already populated before the backend or envoy services start.
#
# This is the dev replacement for the smallstep-CA bootstrap; the
# production path uses Vault PKI / KMS-backed signing instead.

set -eu

PKI_DIR=${PKI_DIR:-/pki}
DOMAIN=${DOMAIN:-localhost}
EXTRA_SAN=${EXTRA_SAN:-DNS:localhost,DNS:envoy,DNS:backend}

mkdir -p "${PKI_DIR}"
cd "${PKI_DIR}"

# Idempotent: leave existing material in place so `docker compose up`
# can be re-run without rotating the agent's pinned trust anchor.
if [ -f agent-ca.crt ] && [ -f agent-ca.key ] && [ -f backend.crt ] \
        && [ -f agent-ca.fingerprint ]; then
    echo "init-pki: PKI already present, nothing to do"
    exit 0
fi

echo "init-pki: generating ed25519 agent CA"
openssl genpkey -algorithm ed25519 -out agent-ca.key
openssl req -x509 -new -key agent-ca.key -days 365 \
    -subj "/CN=BaselithRedAgentDevCA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -out agent-ca.crt

echo "init-pki: generating backend service cert (CN=${DOMAIN})"
openssl genpkey -algorithm ed25519 -out backend.key
openssl req -new -key backend.key -subj "/CN=${DOMAIN}" -out backend.csr
cat > backend.ext <<EOF
subjectAltName = ${EXTRA_SAN}
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
basicConstraints = CA:FALSE
EOF
openssl x509 -req -in backend.csr \
    -CA agent-ca.crt -CAkey agent-ca.key -CAcreateserial \
    -days 365 -extfile backend.ext -out backend.crt
rm -f backend.csr backend.ext agent-ca.srl

echo "init-pki: computing pinned SPKI fingerprint"
openssl x509 -in agent-ca.crt -pubkey -noout \
    | openssl pkey -pubin -outform DER \
    | openssl dgst -sha256 -hex \
    | awk '{print $NF}' > agent-ca.fingerprint

# World-readable so the backend (uid != root in compose) can read.
chmod 0644 agent-ca.crt agent-ca.key agent-ca.fingerprint backend.crt backend.key

echo "init-pki: PKI ready under ${PKI_DIR}"
ls -la "${PKI_DIR}"
