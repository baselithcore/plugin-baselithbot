---
# Alertmanager — routing critical → immediate, warning → digest.
# Renderizzato da bootstrap.sh con envsubst.

global:
  resolve_timeout: 5m
  smtp_smarthost: "${SMTP_HOST}"
  smtp_from: "${SMTP_FROM}"
  smtp_auth_username: "${SMTP_USER}"
  smtp_auth_password: "${SMTP_PASSWORD}"
  smtp_require_tls: true

templates:
  - /etc/alertmanager/templates/*.tmpl

route:
  receiver: default
  group_by: [alertname, service, tenant_id]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - matchers:
        - severity = "critical"
      receiver: critical
      group_wait: 10s
      repeat_interval: 1h
      continue: true

    - matchers:
        - slo =~ ".+"
      receiver: slo-channel
      group_wait: 1m
      repeat_interval: 2h

inhibit_rules:
  - source_matchers:
      - alertname = "ContainerDown"
    target_matchers:
      - alertname =~ "HighErrorRate|ChatLatencyP95High|PostgresDown|QdrantDown"
    equal: [instance]

  - source_matchers:
      - severity = "critical"
    target_matchers:
      - severity = "warning"
    equal: [alertname, service]

receivers:
  - name: default
    slack_configs:
      - api_url: "${SLACK_WEBHOOK_URL}"
        channel: "#llm-wiki-alerts"
        send_resolved: true
        title: '{{ template "slack.default.title" . }}'
        text: '{{ template "slack.default.text" . }}'

  - name: critical
    slack_configs:
      - api_url: "${SLACK_WEBHOOK_URL}"
        channel: "#llm-wiki-incidents"
        send_resolved: true
        title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ template "slack.default.text" . }}'
    email_configs:
      - to: "${ONCALL_EMAIL}"
        send_resolved: true

  - name: slo-channel
    slack_configs:
      - api_url: "${SLACK_WEBHOOK_URL}"
        channel: "#llm-wiki-slo"
        send_resolved: true
        title: 'SLO violation: {{ .GroupLabels.alertname }}'
        text: '{{ template "slack.default.text" . }}'
