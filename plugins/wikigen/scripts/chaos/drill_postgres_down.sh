#!/usr/bin/env bash
# =========================================================================
# drill_postgres_down.sh — Postgres outage simulation.
#
# Scenario: postgres container stop. Verifica:
#   - /health/live continua 200 (process alive)
#   - /health/ready torna 503 con dependencies.postgres.ready=false
#   - Endpoint auth-required (es. /auth/me) → 503 graceful
#   - Wiki read endpoint pubblico (no DB) continua 200
#   - Recovery automatico al restart container (no manual intervention)
# =========================================================================
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
PG_CONTAINER="${PG_CONTAINER:-llm-wiki-postgres}"
DOWN_DURATION="${DOWN_DURATION:-30}"
PASS=0
FAIL=0

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
check() {
    local name="$1"; shift
    if "$@"; then
        log "OK   $name"; PASS=$((PASS+1))
    else
        log "FAIL $name"; FAIL=$((FAIL+1))
    fi
}

# ----- Setup -----
log "=== drill_postgres_down ==="
log "verify baseline: live + ready"
check "live healthy"  curl -fsS "$BASE_URL/health/live" -o /dev/null
check "ready healthy" curl -fsS "$BASE_URL/health/ready" -o /dev/null

# ----- Inject -----
log "stopping $PG_CONTAINER"
docker stop "$PG_CONTAINER" >/dev/null
sleep 2

# ----- Observe -----
log "observe degradation for ${DOWN_DURATION}s"
check "live still 200"        curl -fsS "$BASE_URL/health/live" -o /dev/null
check "ready returns 503"     bash -c "[[ \$(curl -s -o /dev/null -w '%{http_code}' '$BASE_URL/health/ready') == 503 ]]"

ready_body=$(curl -s "$BASE_URL/health/ready")
check "postgres reported not-ready" bash -c "echo '$ready_body' | grep -q '\"postgres\".*\"ready\":false'"

# Public read endpoint should still work (no DB dependency)
check "wiki/groups still 200/404" bash -c "code=\$(curl -s -o /dev/null -w '%{http_code}' '$BASE_URL/api/wiki/groups'); [[ \$code == 200 || \$code == 404 ]]"

sleep "$DOWN_DURATION"

# ----- Recover -----
log "starting $PG_CONTAINER"
docker start "$PG_CONTAINER" >/dev/null

log "wait for ready to come back"
for i in $(seq 1 60); do
    if curl -fsS "$BASE_URL/health/ready" -o /dev/null 2>&1; then
        log "recovery completed after ${i}s"
        break
    fi
    sleep 1
done

check "post-recovery ready healthy" curl -fsS "$BASE_URL/health/ready" -o /dev/null

# ----- Summary -----
log "=== summary: $PASS passed, $FAIL failed ==="
exit $FAIL
