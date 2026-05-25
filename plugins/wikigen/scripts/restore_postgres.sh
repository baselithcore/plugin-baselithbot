#!/usr/bin/env bash
# =========================================================================
# restore_postgres.sh — Restore Postgres dump (formato custom -Fc)
#
# DESTRUCTIVE: --clean droppa oggetti esistenti prima del restore.
# Conferma esplicita richiesta a meno di FORCE=1.
#
# Env vars:
#   POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
#   FORCE=1 per skip prompt
#
# Uso:
#   ./scripts/restore_postgres.sh ./backups/postgres/llm_wiki-20260502T120000Z.dump
#   ./scripts/restore_postgres.sh ./backups/postgres/latest.dump
# =========================================================================
set -euo pipefail

DUMP_FILE="${1:-}"
if [[ -z "$DUMP_FILE" ]]; then
    echo "Uso: $0 <path-to-dump>" >&2
    exit 2
fi
if [[ ! -f "$DUMP_FILE" ]]; then
    echo "[ERROR] file non trovato: $DUMP_FILE" >&2
    exit 2
fi

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"
POSTGRES_DB="${POSTGRES_DB:-llm_wiki}"
POSTGRES_USER="${POSTGRES_USER:-llm_wiki}"

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
    echo "[ERROR] POSTGRES_PASSWORD non valorizzato" >&2
    exit 2
fi

# Verifica integrità se .sha256 presente
if [[ -f "${DUMP_FILE}.sha256" ]]; then
    echo "[restore_postgres] verifying sha256"
    (cd "$(dirname "$DUMP_FILE")" && sha256sum -c "$(basename "$DUMP_FILE").sha256")
fi

echo "[restore_postgres] target: ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "[restore_postgres] source: $DUMP_FILE"
echo "[restore_postgres] WARNING: DROP CASCADE su tutti gli oggetti esistenti prima del restore"

if [[ "${FORCE:-0}" != "1" ]]; then
    read -r -p "Confermi (yes)? " ANS
    if [[ "$ANS" != "yes" ]]; then
        echo "abort"
        exit 1
    fi
fi

PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --jobs=4 \
    "$DUMP_FILE"

echo "[restore_postgres] done. Esegui: alembic current   per verificare versione schema."
