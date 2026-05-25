#!/usr/bin/env bash
# =========================================================================
# backup_postgres.sh — Postgres logical backup (pg_dump custom format)
#
# Strategia: pg_dump -Fc (custom) per ripristino selettivo + parallelo.
# Compresso. Retention configurabile via env.
#
# Env vars (override via .env o ambiente shell):
#   POSTGRES_HOST       (default: localhost)
#   POSTGRES_PORT       (default: 5433)
#   POSTGRES_DB         (default: llm_wiki)
#   POSTGRES_USER       (default: llm_wiki)
#   POSTGRES_PASSWORD   (richiesto)
#   BACKUP_DIR          (default: ./backups/postgres)
#   BACKUP_RETENTION_DAYS  (default: 14)
#   BACKUP_S3_BUCKET    (opzionale, sync via aws-cli se configurato)
#
# Uso:
#   ./scripts/backup_postgres.sh
#   BACKUP_RETENTION_DAYS=30 ./scripts/backup_postgres.sh
#
# Cron / systemd timer: vedi deploy/systemd/llm-wiki-backup.{service,timer}.
# =========================================================================
set -euo pipefail

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"
POSTGRES_DB="${POSTGRES_DB:-llm_wiki}"
POSTGRES_USER="${POSTGRES_USER:-llm_wiki}"
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
RETENTION="${BACKUP_RETENTION_DAYS:-14}"
S3_BUCKET="${BACKUP_S3_BUCKET:-}"

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
    echo "[ERROR] POSTGRES_PASSWORD non valorizzato" >&2
    exit 2
fi

mkdir -p "$BACKUP_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/llm_wiki-${TS}.dump"
LATEST="$BACKUP_DIR/latest.dump"

echo "[backup_postgres] dumping ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT} -> $OUT"
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -Fc \
    --compress=9 \
    --no-owner \
    --no-privileges \
    --file="$OUT"

# SHA256 checksum per integrity check
sha256sum "$OUT" > "${OUT}.sha256"
ln -sf "$(basename "$OUT")" "$LATEST"

SIZE="$(du -h "$OUT" | awk '{print $1}')"
echo "[backup_postgres] OK $SIZE -> $OUT"

# Retention
echo "[backup_postgres] cleanup files older than ${RETENTION}d in $BACKUP_DIR"
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'llm_wiki-*.dump' -mtime "+${RETENTION}" -print -delete
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'llm_wiki-*.dump.sha256' -mtime "+${RETENTION}" -print -delete

# Optional S3 sync
if [[ -n "$S3_BUCKET" ]] && command -v aws >/dev/null 2>&1; then
    echo "[backup_postgres] uploading to s3://${S3_BUCKET}/postgres/"
    aws s3 cp "$OUT" "s3://${S3_BUCKET}/postgres/$(basename "$OUT")" --only-show-errors
    aws s3 cp "${OUT}.sha256" "s3://${S3_BUCKET}/postgres/$(basename "$OUT").sha256" --only-show-errors
fi

echo "[backup_postgres] done"
