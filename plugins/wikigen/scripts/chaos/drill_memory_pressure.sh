#!/usr/bin/env bash
# =========================================================================
# drill_memory_pressure.sh — Memory pressure / OOM kill.
#
# Scenario: limita memoria del container app via docker update --memory.
# Verifica:
#   - Sotto pressione, requests grandi falliscono o lentezza
#   - OOM kill triggera restart container (se restart=unless-stopped)
#   - Health torna green dopo restart
#
# Richiede: app gira come container con CONTAINER nominale.
# =========================================================================
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
APP_CONTAINER="${APP_CONTAINER:-llm-wiki-app}"
LIMIT="${LIMIT:-512m}"     # memoria massima durante drill
DURATION="${DURATION:-30}"
PASS=0; FAIL=0

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
check() {
    local name="$1"; shift
    if "$@"; then log "OK   $name"; PASS=$((PASS+1)); else log "FAIL $name"; FAIL=$((FAIL+1)); fi
}

if ! docker ps --format '{{.Names}}' | grep -q "^${APP_CONTAINER}$"; then
    log "[skip] container '$APP_CONTAINER' non in esecuzione"
    exit 0
fi

log "=== drill_memory_pressure ==="
ORIG_LIMIT=$(docker inspect "$APP_CONTAINER" --format '{{.HostConfig.Memory}}')
log "baseline mem limit: ${ORIG_LIMIT} bytes"

check "baseline ready" curl -fsS "$BASE_URL/health/ready" -o /dev/null

log "applying memory limit $LIMIT to $APP_CONTAINER"
docker update --memory "$LIMIT" --memory-swap "$LIMIT" "$APP_CONTAINER" >/dev/null

log "stress test: 5x parallel large requests for ${DURATION}s"
for i in $(seq 1 5); do
    (curl -s -m "$DURATION" -X POST "$BASE_URL/api/chat" \
        -H 'Content-Type: application/json' \
        -d '{"message":"prova","limit":3}' >/dev/null 2>&1) &
done

sleep "$DURATION"
wait

# Container potrebbe essere stato OOM-killed e ristartato.
log "wait for container/health to settle"
for i in $(seq 1 30); do
    if curl -fsS "$BASE_URL/health/live" -o /dev/null 2>&1; then
        log "live recovered in ${i}s after pressure"; break
    fi
    sleep 1
done
check "live recovered" curl -fsS "$BASE_URL/health/live" -o /dev/null

log "restoring original mem limit (0 = unlimited)"
docker update --memory "${ORIG_LIMIT:-0}" --memory-swap -1 "$APP_CONTAINER" >/dev/null 2>&1 || \
    docker update --memory 0 "$APP_CONTAINER" >/dev/null

check "post-restore ready" curl -fsS "$BASE_URL/health/ready" -o /dev/null

log "=== summary: $PASS passed, $FAIL failed ==="
exit $FAIL
