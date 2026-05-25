#!/usr/bin/env bash
# =========================================================================
# drill_qdrant_down.sh — Qdrant outage.
#
# Scenario: qdrant container stop. Verifica:
#   - /health/ready torna 503 (qdrant required=true)
#   - Auth + DB endpoints continuano 200
#   - Recovery automatico
# =========================================================================
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
QDRANT_CONTAINER="${QDRANT_CONTAINER:-llm-wiki-qdrant}"
DOWN_DURATION="${DOWN_DURATION:-30}"
PASS=0; FAIL=0

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
check() {
    local name="$1"; shift
    if "$@"; then log "OK   $name"; PASS=$((PASS+1)); else log "FAIL $name"; FAIL=$((FAIL+1)); fi
}

log "=== drill_qdrant_down ==="
check "baseline ready" curl -fsS "$BASE_URL/health/ready" -o /dev/null

log "stopping $QDRANT_CONTAINER"
docker stop "$QDRANT_CONTAINER" >/dev/null
sleep 3

check "live still 200"     curl -fsS "$BASE_URL/health/live" -o /dev/null
check "ready returns 503"  bash -c "[[ \$(curl -s -o /dev/null -w '%{http_code}' '$BASE_URL/health/ready') == 503 ]]"
ready_body=$(curl -s "$BASE_URL/health/ready")
check "qdrant reported not-ready" bash -c "echo '$ready_body' | grep -q '\"qdrant\".*\"ready\":false'"

sleep "$DOWN_DURATION"

log "starting $QDRANT_CONTAINER"
docker start "$QDRANT_CONTAINER" >/dev/null

log "wait for recovery"
for i in $(seq 1 60); do
    if curl -fsS "$BASE_URL/health/ready" -o /dev/null 2>&1; then
        log "recovery in ${i}s"; break
    fi
    sleep 1
done

check "post-recovery ready" curl -fsS "$BASE_URL/health/ready" -o /dev/null

log "=== summary: $PASS passed, $FAIL failed ==="
exit $FAIL
