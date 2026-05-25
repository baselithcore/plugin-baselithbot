---
global:
  scrape_interval: 15s
  scrape_timeout: 10s
  evaluation_interval: 30s
  external_labels:
    environment: prod
    service: dbview

rule_files:
  - /etc/prometheus/alerts.yml

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]

  # /metrics is admin-protected on dbview. Prometheus 2.43+ supports
  # arbitrary HTTP headers; the service-to-service API key bypasses JWT.
  # Target:
  #   - docker:     "dbview-api:3001"
  #   - mac-native: "host.docker.internal:3001"
  - job_name: dbview
    metrics_path: /api/metrics
    scheme: http
    static_configs:
      - targets: ["${DBVIEW_TARGET}"]
        labels:
          service: dbview
          component: backend
    http_headers:
      X-API-Key:
        values:
          - "${DBVIEW_METRICS_TOKEN}"
    scrape_interval: 30s
    scrape_timeout: 20s

  - job_name: node
    static_configs:
      - targets: ["node-exporter:9100"]
        labels:
          component: host

  - job_name: otelcol-docker
    static_configs:
      - targets: ["otel-collector:8889"]
        labels:
          component: containers

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

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]
      scheme: http
      timeout: 10s
      api_version: v2
