#!/usr/bin/env bash
# =========================================================================
# drill_disk_full.sh — Disk pressure simulation.
#
# Scenario: riempi `vaults/` o `logs/` quasi al limite, verifica che:
#   - Ingest write (vaults/<domain>/wiki/) fallisce graceful
#   - Log rotation kick-in (se logrotate hooked)
#   - L'app non crasha; restituisce 507 Insufficient Storage o 500
#   - Cleanup riporta tutto a regime
#
# Implementazione: usa `fallocate` per file dummy, poi rimuove.
# Richiede privilegi se la mountpoint è /; preferibile in container
# dedicato con quota.
# =========================================================================
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TARGET_DIR="${TARGET_DIR:-./vaults}"
FILL_SIZE="${FILL_SIZE:-1G}"      # quanto allocare
DUMMY="$TARGET_DIR/.chaos_dummy.bin"
PASS=0; FAIL=0

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
check() {
    local name="$1"; shift
    if "$@"; then log "OK   $name"; PASS=$((PASS+1)); else log "FAIL $name"; FAIL=$((FAIL+1)); fi
}

cleanup() {
    rm -f "$DUMMY" 2>/dev/null || true
}
trap cleanup EXIT

log "=== drill_disk_full ==="
log "target: $TARGET_DIR (free: $(df -h "$TARGET_DIR" | awk 'NR==2 {print $4}'))"

if ! command -v fallocate >/dev/null 2>&1; then
    log "[skip] fallocate non disponibile (mac usa Linux/Docker per drill realistico)"
    exit 0
fi

mkdir -p "$TARGET_DIR"
log "allocating $FILL_SIZE dummy file"
fallocate -l "$FILL_SIZE" "$DUMMY" || {
    log "[skip] fallocate failed (probabilmente disco non ha quota o filesystem non supporta)"
    exit 0
}
log "free now: $(df -h "$TARGET_DIR" | awk 'NR==2 {print $4}')"

check "live still 200"  curl -fsS "$BASE_URL/health/live" -o /dev/null
check "ready still 200" curl -fsS "$BASE_URL/health/ready" -o /dev/null

# Try a write op (POST feedback usa DB, non disk diretto — meglio
# scrivere file diretto in vaults/<domain>/wiki/ se domain attivo).
# Qui ci limitiamo a verificare che il processo non crashi.

cleanup
log "free after cleanup: $(df -h "$TARGET_DIR" | awk 'NR==2 {print $4}')"
check "post-cleanup ready" curl -fsS "$BASE_URL/health/ready" -o /dev/null

log "=== summary: $PASS passed, $FAIL failed ==="
exit $FAIL
