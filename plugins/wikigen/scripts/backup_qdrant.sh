#!/usr/bin/env bash
# =========================================================================
# backup_qdrant.sh — Qdrant collection snapshot via REST API
#
# Snapshot creato side-server, scaricato in $BACKUP_DIR. Retention.
#
# Env vars:
#   QDRANT_URL              (default: http://localhost:6333)
#   QDRANT_API_KEY          (opzionale; iniettato come header)
#   QDRANT_COLLECTIONS      (CSV; vuoto -> tutte le collection)
#   BACKUP_DIR              (default: ./backups/qdrant)
#   BACKUP_RETENTION_DAYS   (default: 14)
#   BACKUP_S3_BUCKET        (opzionale)
#
# Uso:
#   ./scripts/backup_qdrant.sh
#   QDRANT_COLLECTIONS=insurance-wiki,legal-wiki ./scripts/backup_qdrant.sh
# =========================================================================
set -euo pipefail

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
QDRANT_API_KEY="${QDRANT_API_KEY:-}"
COLLECTIONS_CSV="${QDRANT_COLLECTIONS:-}"
BACKUP_DIR="${BACKUP_DIR:-./backups/qdrant}"
RETENTION="${BACKUP_RETENTION_DAYS:-14}"
S3_BUCKET="${BACKUP_S3_BUCKET:-}"

mkdir -p "$BACKUP_DIR"

curl_qdrant() {
    if [[ -n "$QDRANT_API_KEY" ]]; then
        curl -fsS -H "api-key: $QDRANT_API_KEY" "$@"
    else
        curl -fsS "$@"
    fi
}

# Risolvi lista collection
if [[ -z "$COLLECTIONS_CSV" ]]; then
    COLLECTIONS=$(curl_qdrant "${QDRANT_URL}/collections" \
        | python3 -c 'import sys,json; r=json.load(sys.stdin); print("\n".join(c["name"] for c in r["result"]["collections"]))')
else
    COLLECTIONS=$(echo "$COLLECTIONS_CSV" | tr ',' '\n')
fi

if [[ -z "$COLLECTIONS" ]]; then
    echo "[backup_qdrant] nessuna collection trovata"
    exit 0
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"

for COLL in $COLLECTIONS; do
    echo "[backup_qdrant] snapshot collection: $COLL"
    SNAP_RESP=$(curl_qdrant -X POST "${QDRANT_URL}/collections/${COLL}/snapshots")
    SNAP_NAME=$(echo "$SNAP_RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["name"])')
    OUT="$BACKUP_DIR/${COLL}-${TS}.snapshot"
    echo "[backup_qdrant] downloading $SNAP_NAME -> $OUT"
    curl_qdrant -o "$OUT" "${QDRANT_URL}/collections/${COLL}/snapshots/${SNAP_NAME}"
    sha256sum "$OUT" > "${OUT}.sha256"
    # Pulisci snapshot remoto (Qdrant li tiene su disco indefinitamente)
    curl_qdrant -X DELETE "${QDRANT_URL}/collections/${COLL}/snapshots/${SNAP_NAME}" >/dev/null || true

    SIZE="$(du -h "$OUT" | awk '{print $1}')"
    echo "[backup_qdrant] OK $COLL $SIZE"

    if [[ -n "$S3_BUCKET" ]] && command -v aws >/dev/null 2>&1; then
        aws s3 cp "$OUT" "s3://${S3_BUCKET}/qdrant/$(basename "$OUT")" --only-show-errors
        aws s3 cp "${OUT}.sha256" "s3://${S3_BUCKET}/qdrant/$(basename "$OUT").sha256" --only-show-errors
    fi
done

# Retention
echo "[backup_qdrant] cleanup files older than ${RETENTION}d"
find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.snapshot' -mtime "+${RETENTION}" -print -delete
find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.snapshot.sha256' -mtime "+${RETENTION}" -print -delete

echo "[backup_qdrant] done"
