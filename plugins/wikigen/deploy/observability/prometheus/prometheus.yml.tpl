---
global:
  scrape_interval: 15s
  scrape_timeout: 10s
  evaluation_interval: 30s
  external_labels:
    environment: prod
    service: llm-wiki

rule_files:
  - /etc/prometheus/alerts.yml

scrape_configs:
  # === Self ===
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]

  # === llm-wiki app ===
  # /metrics gating: bearer admin OR X-API-Key=$WIKI_METRICS_TOKEN OR loopback.
  # Target tipico: "llm-wiki:8000" (stessa rete obs) o
  # "host.docker.internal:8000" (mac-native).
  - job_name: llm-wiki
    metrics_path: /metrics
    scheme: http
    static_configs:
      - targets: ["${LLM_WIKI_TARGET}"]
        labels:
          service: llm-wiki
          component: backend
    http_headers:
      X-API-Key:
        values:
          - "${WIKI_METRICS_TOKEN}"
    scrape_interval: 30s
    scrape_timeout: 20s

  # === Host metrics (node-exporter) ===
  - job_name: node
    static_configs:
      - targets: ["node-exporter:9100"]
        labels:
          component: host

  # === Container metrics (OTel docker_stats receiver) ===
  - job_name: otelcol-docker
    static_configs:
      - targets: ["otel-collector:8889"]
        labels:
          component: containers

  # === Self-monitoring obs stack ===
  - job_name: loki
    static_configs:
      - targets: ["loki:3100"]
        labels:
          component: logs
  - job_name: tempo
    static_configs:
      - targets: ["tempo:3200"]
        labels:
          component: traces
  - job_name: alertmanager
    static_configs:
      - targets: ["alertmanager:9093"]
        labels:
          component: alerting

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]
      scheme: http
      timeout: 10s
      api_version: v2
