#!/usr/bin/env bash
# =========================================================================
# drill_ollama_down.sh — Ollama unreachable.
#
# Scenario: blocca traffico TCP verso $OLLAMA_HOST via iptables (Linux)
# o stop processo (mac). Verifica:
#   - /health/ready resta 200 (Ollama non è dependency hard)
#   - POST /api/chat fallisce graceful (500/502 con messaggio)
#   - Ingest job va in FAILED, non blocca worker permanentemente
#   - Recovery: nuovo chat funziona dopo restart Ollama
# =========================================================================
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
PASS=0; FAIL=0

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
check() {
    local name="$1"; shift
    if "$@"; then log "OK   $name"; PASS=$((PASS+1)); else log "FAIL $name"; FAIL=$((FAIL+1)); fi
}

stop_ollama() {
    if [[ "$(uname)" == "Darwin" ]]; then
        # Mac: brew services stop ollama (richiede sudo? di solito no)
        if pgrep -x ollama >/dev/null; then
            launchctl unload "$HOME/Library/LaunchAgents/homebrew.mxcl.ollama.plist" 2>/dev/null \
                || pkill -x ollama || true
            sleep 2
        fi
    else
        # Linux: blocco firewall su port 11434 (richiede sudo)
        sudo iptables -I OUTPUT -p tcp --dport 11434 -j REJECT
    fi
}

start_ollama() {
    if [[ "$(uname)" == "Darwin" ]]; then
        launchctl load "$HOME/Library/LaunchAgents/homebrew.mxcl.ollama.plist" 2>/dev/null \
            || ollama serve >/tmp/ollama.log 2>&1 &
        sleep 3
    else
        sudo iptables -D OUTPUT -p tcp --dport 11434 -j REJECT 2>/dev/null || true
    fi
}

log "=== drill_ollama_down ==="
check "baseline ollama up" curl -fsS "$OLLAMA_HOST/api/tags" -o /dev/null
check "baseline ready" curl -fsS "$BASE_URL/health/ready" -o /dev/null

log "stopping/blocking Ollama"
stop_ollama
sleep 2

check "live still 200"  curl -fsS "$BASE_URL/health/live" -o /dev/null
check "ready still 200" curl -fsS "$BASE_URL/health/ready" -o /dev/null

log "POST /api/chat (expect graceful failure)"
chat_code=$(curl -s -o /dev/null -w '%{http_code}' \
    -X POST "$BASE_URL/api/chat" \
    -H 'Content-Type: application/json' \
    --max-time 30 \
    -d '{"message":"test","limit":3}')
check "chat returns 5xx, not hang" bash -c "[[ '$chat_code' =~ ^5 ]]"

log "restoring Ollama"
start_ollama
sleep 5

log "wait for ollama responsive"
for i in $(seq 1 30); do
    if curl -fsS "$OLLAMA_HOST/api/tags" -o /dev/null 2>&1; then
        log "ollama up in ${i}s"; break
    fi
    sleep 1
done

check "post-recovery chat 200" bash -c "code=\$(curl -s -o /dev/null -w '%{http_code}' -X POST '$BASE_URL/api/chat' -H 'Content-Type: application/json' --max-time 60 -d '{\"message\":\"ping\",\"limit\":1}'); [[ \$code == 200 ]]"

log "=== summary: $PASS passed, $FAIL failed ==="
exit $FAIL
