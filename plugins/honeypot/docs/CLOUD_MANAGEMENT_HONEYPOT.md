# Cloud Management API Honeypot - Technical Documentation

## Overview

The Cloud Management Honeypot is a **high-interaction** deception system simulating AWS-like cloud management APIs. It is designed to detect and analyze:

- **Advanced Persistent Threats (APT)** targeting cloud infrastructure
- **Privilege escalation** attempts via IAM policy manipulation
- **Data exfiltration** through S3 and Secrets Manager abuse
- **SSRF attacks** via EC2 metadata service (IMDS) exploitation
- **Zero-day attack patterns** through behavioral heuristics

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    CloudManagementHandler                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Request   │  │   Session   │  │   Pattern   │  │  Heuristic │ │
│  │   Parser    │──│   State     │──│  Detector   │──│   Engine   │ │
│  │             │  │   Machine   │  │             │  │            │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│         │                │                │                │        │
│         ▼                ▼                ▼                ▼        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  CloudResponseGenerator                      │   │
│  │  (Realistic AWS-like responses with version-specific errors) │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Event Emission                            │   │
│  │        (Integration with HoneyDOC Captor & EventBus)         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. CloudManagementHandler (`handler.py`)

The main HTTP handler implementing:

- AWS Signature Version 4 parsing
- Multi-service API routing (IAM, S3, STS, Secrets Manager)
- IMDS simulation for SSRF detection
- Credential extraction and capture
- Integration with existing `BaseHandler`

```python
from plugins.honeypot.engine.cloud import CloudManagementHandler

handler = CloudManagementHandler(config, provider=CloudProvider.AWS)
await handler.start(port=8443)
```

### 2. SessionStateMachine (`state_machine.py`)

Finite state machine tracking attacker session progression:

```text
DISCOVERY → PRE_AUTH → AUTHENTICATED → EXPLORING
                              │              │
                              ▼              ▼
                    PRIVILEGE_ESCALATION ← LATERAL_MOVEMENT
                              │              │
                              ▼              ▼
                         EXFILTRATING → BLOCKED/EXPIRED
```

**State Transitions:**

- `probe_endpoint`: Service discovery
- `auth_attempt`: Credential submission
- `list_resources`: Enumeration activity
- `download_attempt`: Data exfiltration
- `iam_action`: Privilege escalation

### 3. CloudPatternDetector (`patterns.py`)

Cloud-specific attack pattern detection with 50+ regex patterns:

| Category | Patterns | Severity |
|----------|----------|----------|
| IAM Enumeration | GetUser, ListRoles, GetPolicy | MEDIUM |
| Privilege Escalation | AttachUserPolicy, CreateAccessKey | CRITICAL |
| S3 Exfiltration | GetObject, ListBuckets | HIGH |
| IMDS Abuse | 169.254.169.254 | CRITICAL |
| SSRF | Internal IP ranges | HIGH |

**MITRE ATT&CK Mapping:**

- T1087.004: Cloud Account Discovery
- T1552.005: Cloud Instance Metadata API
- T1098.003: Additional Cloud Roles
- T1530: Data from Cloud Storage

### 4. HeuristicEngine (`heuristics.py`)

Zero-day pattern detection through behavioral analysis:

| Heuristic | Category | Description |
|-----------|----------|-------------|
| `machine_timing` | Timing | Sub-100ms request intervals |
| `burst_requests` | Timing | >20 requests in 5s window |
| `privesc_sequence` | Sequence | Known IAM escalation chains |
| `unusual_service_combo` | Sequence | IAM + S3 + KMS combination |
| `encoded_payload` | Payload | Base64/URL-encoded content |
| `high_error_rate` | Behavior | >70% API error rate |
| `abnormal_data_volume` | Behavior | >100MB data requests |

### 5. CloudResponseGenerator (`responses.py`)

Generates realistic AWS-like responses:

**Success Responses:**

```json
{
  "ListBucketsResponse": {
    "Owner": {"ID": "abc123", "DisplayName": "honeypot-owner"},
    "Buckets": [
      {"Name": "prod-data-abc123", "CreationDate": "2024-01-15T10:00:00Z"}
    ]
  }
}
```

**Error Responses (version-specific):**

```json
{
  "Error": {
    "Code": "AccessDenied",
    "Message": "User: arn:aws:iam::123456789012:user/admin is not authorized to perform: iam:CreateUser on resource: arn:aws:iam::123456789012:user/backdoor",
    "Type": "Sender"
  }
}
```

**Bait Responses (credential capture):**

- `CreateAccessKey`: Returns fake but realistic-looking AWS credentials
- `GetSecretValue`: Returns fake database credentials
- `AssumeRole`: Returns temporary session credentials

## Data Models

### CloudSession

```python
class CloudSession(BaseModel):
    session_id: str
    source_ip: str
    current_state: SessionState  # DISCOVERY, AUTHENTICATED, etc.
    auth_attempts: int
    credentials_captured: List[CloudCredential]
    api_call_count: int
    services_accessed: Set[str]
    threat_score: float  # 0.0 - 100.0
    mitre_techniques: List[str]
```

### CloudAPICall

```python
class CloudAPICall(BaseModel):
    call_id: str
    service: str  # iam, s3, sts
    action: str  # GetUser, ListBuckets
    category: CloudAttackCategory
    severity: APICallSeverity
    tcp_fingerprint: Optional[TCPFingerprint]
    tls_fingerprint: Optional[TLSFingerprint]
    request_timing: RequestTiming
```

### HeuristicAlert

```python
class HeuristicAlert(BaseModel):
    heuristic_name: str
    severity: APICallSeverity
    trigger_reason: str
    evidence: Dict[str, Any]
    deviation_score: float  # 0.0 - 1.0
    is_zero_day_candidate: bool
```

## Integration

### With Existing Plugin System

The Cloud Management Honeypot integrates with the existing honeypot plugin:

```python
# In plugins/honeypot/swarm/handlers.py
from ..engine.cloud import CloudManagementHandler

class HandlerMixin:
    def _load_cloud_handler(self, definition):
        if definition.handler_type == "cloud":
            return CloudManagementHandler(
                self.config,
                definition=definition,
                provider=CloudProvider(definition.cloud_config.get("provider", "aws"))
            )
```

### EventBus Integration

Events are emitted through the standard EventBus:

```python
from core.events import get_event_bus

# Cloud-specific events
await bus.emit("honeypot.cloud_api_call", {
    "session_id": session.session_id,
    "service": "iam",
    "action": "CreateAccessKey",
    "severity": "critical",
    "mitre_technique": "T1098.001"
})

await bus.emit("honeypot.heuristic_alert", {
    "heuristic": "privesc_sequence",
    "is_zero_day_candidate": True,
    "deviation_score": 0.85
})
```

### HoneyDOC Captor Integration

```python
from ..captor import CaptorManager

captor = CaptorManager(config)

# Capture cloud API event
await captor.capture_network_event({
    "protocol": "http",
    "port": 8443,
    "source_ip": source_ip,
    "service": "cloud-api",
    "action": call.action,
    "fingerprints": {
        "tcp": tcp_fingerprint.options_signature,
        "tls": tls_fingerprint.ja4,
    }
})
```

## Configuration

### YAML Definition

```yaml
id: 'cloud-management-api'
protocol: 'http'
port: 8443
handler_type: 'cloud'

cloud_config:
  provider: 'aws'
  enabled_services: ['iam', 's3', 'sts', 'secretsmanager']
  imds_enabled: true

heuristics:
  enabled: true
  rules:
    - name: 'machine_timing'
      threshold_ms: 100
    - name: 'privesc_sequence'
      enabled: true

forensics:
  tcp_fingerprint: true
  tls_fingerprint: true
  capture_credentials: true
```

### Runtime Configuration

```python
# Enable specific heuristics
engine = get_heuristic_engine()
engine.add_rule(CustomHeuristicRule())

# Set callbacks
handler.set_high_severity_callback(async_alert_handler)
handler.set_session_end_callback(async_session_handler)
```

## Security Considerations

### Isolation

1. **No Outbound Connections**: The honeypot never initiates external connections
2. **Sandboxed Responses**: All responses are pre-generated or dynamically created from templates
3. **Input Sanitization**: All attacker input is sanitized via `sanitize_for_llm()` and `sanitize_for_log()`
4. **Resource Limits**: Rate limiting, max session duration, max body size

### Credential Handling

```python
# Credentials are always redacted in logs
credential.redacted()  # Returns sanitized version

# Example output:
{
    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
    "secret_access_key": "***REDACTED***",
    "session_token": "***REDACTED***"
}
```

### Attack Mitigation

- **Rate Limiting**: 10 connections/IP/minute
- **Session Timeout**: 30 minutes max
- **Auth Attempts**: 5 failures before blocking
- **Data Volume**: 100MB limit per session

## Deployment

### Standalone

```python
import asyncio
from plugins.honeypot.config import HoneypotConfig
from plugins.honeypot.engine.cloud import CloudManagementHandler

async def main():
    config = HoneypotConfig()
    handler = CloudManagementHandler(config)
    await handler.start(port=8443)

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await handler.stop()

asyncio.run(main())
```

### With Plugin System

The honeypot is automatically loaded when the YAML definition is present:

```bash
# Ensure YAML is in honeypots directory
ls plugins/honeypot/honeypots/cloud-management-api.yaml

# Start the honeypot system
python -m core.cli run
```

### Docker

```dockerfile
# Expose cloud API port
EXPOSE 8443

# Environment
ENV HONEYPOT_CLOUD_API_PORT=8443
ENV HONEYPOT_CLOUD_PROVIDER=aws
```

## Monitoring & Alerting

### Real-time Alerts

```python
# Subscribe to high-severity events
@bus.on("honeypot.attack_high_severity")
async def handle_critical(data):
    if data.get("category") == "privilege_escalation":
        await send_alert(
            channel="security-alerts",
            message=f"IAM privilege escalation from {data['source_ip']}"
        )
```

### Zero-Day Detection

```python
# Get potential zero-day indicators
candidates = handler.get_zero_day_candidates()
for alert in candidates:
    if alert.deviation_score > 0.9:
        await notify_security_team(alert)
```

### Statistics

```python
stats = handler.get_statistics()
# Returns CloudHoneypotStats with:
# - total_sessions, active_sessions
# - auth_attempts, credentials_captured
# - calls_by_service, attacks_by_category
# - heuristic_alerts, zero_day_candidates
```

## Testing

### Unit Tests

```bash
pytest plugins/honeypot/tests/unit/test_cloud_handler.py -v
```

### Integration Tests

```bash
pytest plugins/honeypot/tests/integration/test_cloud_integration.py -v
```

### Manual Testing

```bash
# Test IAM enumeration
curl -X POST http://localhost:8443/ \
  -H "Authorization: AWS4-HMAC-SHA256 Credential=AKIATEST/20240101/us-east-1/iam/aws4_request" \
  -d "Action=ListUsers"

# Test IMDS (SSRF detection)
curl http://localhost:8443/latest/meta-data/iam/security-credentials/

# Test S3 bucket listing
curl -X GET http://localhost:8443/s3/ \
  -H "Authorization: AWS4-HMAC-SHA256 Credential=AKIATEST/20240101/us-east-1/s3/aws4_request"
```

## Appendix

### Supported AWS Actions

| Service | Actions |
|---------|---------|
| IAM | GetUser, ListUsers, ListRoles, CreateAccessKey, AttachUserPolicy |
| S3 | ListBuckets, ListObjects, GetObject |
| STS | GetCallerIdentity, AssumeRole |
| Secrets Manager | ListSecrets, GetSecretValue |
| EC2 | DescribeInstances |
| IMDS | All /latest/meta-data paths |

### MITRE ATT&CK Coverage

- **Discovery**: T1087.004, T1580, T1619
- **Credential Access**: T1552.005, T1555
- **Privilege Escalation**: T1098.003, T1548.005
- **Lateral Movement**: T1021.007, T1648
- **Collection**: T1530
- **Exfiltration**: T1567.002
- **Defense Evasion**: T1562.008

### Performance Benchmarks

| Metric | Value |
|--------|-------|
| Requests/second | 1000+ |
| Memory per session | ~50KB |
| Pattern detection latency | <5ms |
| Heuristic evaluation | <10ms |
