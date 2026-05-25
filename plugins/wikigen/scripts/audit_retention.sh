#!/usr/bin/env bash
# =========================================================================
# audit_retention.sh — prune audit_events oltre retention.
#
# Chiama la stored function `prune_audit_events(retention_days)` (mig 010).
# La funzione è SECURITY DEFINER e log se stessa in audit_events come
# evento `audit.prune` (chain of custody).
#
# Env vars:
#   POSTGRES_HOST/PORT/DB/USER/PASSWORD
#   AUDIT_RETENTION_DAYS  (default: 730 = 2 anni)
#
# Uso:
#   ./scripts/audit_retention.sh
#   AUDIT_RETENTION_DAYS=1825 ./scripts/audit_retention.sh   # 5 anni
#
# Schedule: settimanale via systemd timer
# (deploy/systemd/llm-wiki-audit-retention.{service,timer}).
# =========================================================================
set -euo pipefail

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"
POSTGRES_DB="${POSTGRES_DB:-llm_wiki}"
POSTGRES_USER="${POSTGRES_USER:-llm_wiki}"
RETENTION="${AUDIT_RETENTION_DAYS:-730}"

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
    echo "[ERROR] POSTGRES_PASSWORD non valorizzato" >&2
    exit 2
fi

if [[ "$RETENTION" -lt 30 ]]; then
    echo "[ERROR] AUDIT_RETENTION_DAYS deve essere >= 30 (got $RETENTION)" >&2
    exit 2
fi

echo "[audit_retention] pruning audit_events older than ${RETENTION} days"
REMOVED=$(PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -tAc "SELECT prune_audit_events(${RETENTION})")

echo "[audit_retention] removed ${REMOVED} rows"
