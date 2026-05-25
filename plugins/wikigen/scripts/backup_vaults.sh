#!/usr/bin/env bash
# =========================================================================
# backup_vaults.sh — Tarball di vaults/ + domains/ (filesystem stato)
#
# Cattura tutti i vault (wiki + raw) + domain pack (config + prompts +
# .synth.meta.json). Esclude .git/ e __pycache__.
#
# Env vars:
#   VAULTS_DIR              (default: ./vaults)
#   DOMAINS_DIR             (default: ./domains)
#   BACKUP_DIR              (default: ./backups/vaults)
#   BACKUP_RETENTION_DAYS   (default: 14)
#   BACKUP_S3_BUCKET        (opzionale)
# =========================================================================
set -euo pipefail

VAULTS_DIR="${VAULTS_DIR:-./vaults}"
DOMAINS_DIR="${DOMAINS_DIR:-./domains}"
BACKUP_DIR="${BACKUP_DIR:-./backups/vaults}"
RETENTION="${BACKUP_RETENTION_DAYS:-14}"
S3_BUCKET="${BACKUP_S3_BUCKET:-}"

mkdir -p "$BACKUP_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/vaults-${TS}.tar.zst"

echo "[backup_vaults] archiving ${VAULTS_DIR} + ${DOMAINS_DIR} -> $OUT"

# zstd preferito (alta compressione + velocità). Fallback gzip.
if command -v zstd >/dev/null 2>&1; then
    tar --exclude='.git' --exclude='__pycache__' --exclude='.DS_Store' \
        -cf - "$VAULTS_DIR" "$DOMAINS_DIR" 2>/dev/null \
        | zstd -19 -T0 -o "$OUT"
else
    OUT="${OUT%.zst}.gz"
    tar --exclude='.git' --exclude='__pycache__' --exclude='.DS_Store' \
        -czf "$OUT" "$VAULTS_DIR" "$DOMAINS_DIR" 2>/dev/null
fi

sha256sum "$OUT" > "${OUT}.sha256"
SIZE="$(du -h "$OUT" | awk '{print $1}')"
echo "[backup_vaults] OK $SIZE -> $OUT"

# Retention
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'vaults-*.tar.zst' -o -name 'vaults-*.tar.gz' \) -mtime "+${RETENTION}" -print -delete
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'vaults-*.sha256' -mtime "+${RETENTION}" -print -delete

if [[ -n "$S3_BUCKET" ]] && command -v aws >/dev/null 2>&1; then
    aws s3 cp "$OUT" "s3://${S3_BUCKET}/vaults/$(basename "$OUT")" --only-show-errors
    aws s3 cp "${OUT}.sha256" "s3://${S3_BUCKET}/vaults/$(basename "$OUT").sha256" --only-show-errors
fi

echo "[backup_vaults] done"
