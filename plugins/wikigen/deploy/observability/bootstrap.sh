#!/usr/bin/env bash
# Bootstrap stack di observability per llm-wiki.
#
# Uso:
#   ./deploy/observability/bootstrap.sh [up|down|logs|status|reload|render]
#
# Pre-requisiti:
#   - Docker + Docker Compose v2
#   - File .env (copia da .env.example e personalizza)
#   - L'app llm-wiki avviata dopo questo stack (eventualmente con override)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$SCRIPT_DIR"

if [[ ! -f .env ]]; then
    echo "[bootstrap] .env mancante. Copia da .env.example e personalizza:"
    echo "    cp .env.example .env"
    exit 1
fi

# shellcheck disable=SC1091
set -a && source .env && set +a

if [[ -z "${WIKI_METRICS_TOKEN:-}" ]] || [[ "${WIKI_METRICS_TOKEN:-}" == "change-me" ]]; then
    echo "[bootstrap] ATTENZIONE: WIKI_METRICS_TOKEN non configurato in .env"
    echo "    Imposta lo stesso valore in llm-wiki .env per autenticare lo scrape Prometheus."
fi

ACTION="${1:-up}"

render_templates() {
    if ! command -v envsubst >/dev/null 2>&1; then
        echo "[bootstrap] envsubst non trovato. Installa:"
        echo "    brew install gettext   # macOS"
        echo "    apt install gettext    # debian/ubuntu"
        exit 1
    fi

    local vars='$WIKI_METRICS_TOKEN $LLM_WIKI_TARGET $SLACK_WEBHOOK_URL'
    vars="$vars \$SMTP_HOST \$SMTP_FROM \$SMTP_USER \$SMTP_PASSWORD"
    vars="$vars \$ONCALL_EMAIL \$BILLING_EMAIL"

    for tpl in prometheus/prometheus.yml.tpl alertmanager/alertmanager.yml.tpl; do
        local out="${tpl%.tpl}"
        envsubst "$vars" < "$tpl" > "$out"
        echo "[bootstrap] rendered $out"
    done
}

case "$ACTION" in
    up)
        render_templates
        echo "[bootstrap] avvio stack observability..."
        docker compose --env-file .env up -d
        echo
        echo "[bootstrap] stack pronto:"
        echo "    Grafana     → http://localhost:3000 (user: ${GRAFANA_ADMIN_USER:-admin})"
        echo "    Prometheus  → http://localhost:9090"
        echo "    Loki        → http://localhost:3100"
        echo "    Tempo       → http://localhost:3200"
        echo
        echo "[bootstrap] ora avvia llm-wiki con OTLP endpoint:"
        echo "    cd $REPO_ROOT"
        echo "    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4319 \\"
        echo "      WIKI_METRICS_TOKEN=\"\$WIKI_METRICS_TOKEN\" \\"
        echo "      python -m llm_wiki serve"
        ;;
    down)
        docker compose --env-file .env down
        ;;
    restart)
        docker compose --env-file .env restart
        ;;
    logs)
        docker compose --env-file .env logs -f --tail=100 "${2:-}"
        ;;
    status)
        docker compose --env-file .env ps
        echo
        echo "[bootstrap] verifica scrape Prometheus (target up):"
        curl -s "http://localhost:9090/api/v1/targets?state=active" \
            | python3 -c "import json,sys; \
targets=json.load(sys.stdin)['data']['activeTargets']; \
[print(f\"  {t['labels'].get('job','?'):20} {t['health']:8} {t['lastError'] or ''}\") for t in targets]"
        ;;
    reload)
        render_templates
        curl -s -X POST http://localhost:9090/-/reload && echo "[bootstrap] Prometheus config reloaded"
        curl -s -X POST http://localhost:9093/-/reload && echo "[bootstrap] Alertmanager config reloaded"
        ;;
    render)
        render_templates
        ;;
    *)
        cat <<EOF
Uso: $0 [up|down|restart|logs|status|reload|render]

Esempi:
  $0 up                  # avvia stack obs
  $0 status              # ps + scrape targets
  $0 reload              # ricarica config Prom + Alertmanager (no restart)
  $0 down
EOF
        exit 1
        ;;
esac
