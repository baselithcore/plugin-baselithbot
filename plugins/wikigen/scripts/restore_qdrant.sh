#!/usr/bin/env bash
# =========================================================================
# restore_qdrant.sh — Restore Qdrant collection da snapshot file
#
# DESTRUCTIVE: la collection esistente con stesso nome viene rimpiazzata
# (Qdrant fa drop+create internamente al recover).
#
# Env vars:
#   QDRANT_URL              (default: http://localhost:6333)
#   QDRANT_API_KEY          (opzionale)
#   FORCE=1 per skip prompt
#
# Uso:
#   ./scripts/restore_qdrant.sh insurance-wiki ./backups/qdrant/insurance-wiki-20260502T120000Z.snapshot
# =========================================================================
set -euo pipefail

COLLECTION="${1:-}"
SNAP_FILE="${2:-}"

if [[ -z "$COLLECTION" || -z "$SNAP_FILE" ]]; then
    echo "Uso: $0 <collection> <snapshot-file>" >&2
    exit 2
fi
if [[ ! -f "$SNAP_FILE" ]]; then
    echo "[ERROR] file non trovato: $SNAP_FILE" >&2
    exit 2
fi

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
QDRANT_API_KEY="${QDRANT_API_KEY:-}"

curl_qdrant() {
    if [[ -n "$QDRANT_API_KEY" ]]; then
        curl -fsS -H "api-key: $QDRANT_API_KEY" "$@"
    else
        curl -fsS "$@"
    fi
}

# Verifica integrità
if [[ -f "${SNAP_FILE}.sha256" ]]; then
    echo "[restore_qdrant] verifying sha256"
    (cd "$(dirname "$SNAP_FILE")" && sha256sum -c "$(basename "$SNAP_FILE").sha256")
fi

echo "[restore_qdrant] target: ${COLLECTION}@${QDRANT_URL}"
echo "[restore_qdrant] source: $SNAP_FILE"
echo "[restore_qdrant] WARNING: rimpiazzo collection esistente"

if [[ "${FORCE:-0}" != "1" ]]; then
    read -r -p "Confermi (yes)? " ANS
    if [[ "$ANS" != "yes" ]]; then
        echo "abort"
        exit 1
    fi
fi

# Upload snapshot al server (multipart). Qdrant lo accetta come file
# locale via /collections/{name}/snapshots/upload?priority=snapshot.
echo "[restore_qdrant] uploading snapshot"
curl_qdrant -X POST \
    -H "Content-Type: multipart/form-data" \
    -F "snapshot=@${SNAP_FILE}" \
    "${QDRANT_URL}/collections/${COLLECTION}/snapshots/upload?priority=snapshot"

echo
echo "[restore_qdrant] done. Verifica: curl ${QDRANT_URL}/collections/${COLLECTION}"
