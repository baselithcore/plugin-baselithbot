"""Cloud Handler - Helper Functions.

Helper functions for credential extraction, timing analysis, and event creation.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from aiohttp import web

from ....models import AttackCategory, AttackEvent, AttackSeverity, HoneypotProtocol
from plugins.honeypot.security import sanitize_for_log
from ..models import (
    APICallSeverity,
    CloudAPICall,
    CloudAttackCategory,
    CloudCredential,
    CloudSession,
    HeuristicAlert,
    RequestTiming,
)
from .parsers import parse_aws_auth_header


def extract_credentials(
    headers: Dict[str, str],
    body: str,
) -> Optional[CloudCredential]:
    """Extract credentials from request.

    Args:
        headers: Request headers
        body: Request body

    Returns:
        CloudCredential or None
    """
    credential = None

    # Check Authorization header for AWS Signature
    auth_header = headers.get("Authorization", "")
    access_key = parse_aws_auth_header(auth_header)
    if access_key:
        credential = CloudCredential(access_key_id=access_key)

    # Check for X-Amz-Security-Token
    if "x-amz-security-token" in headers:
        if credential is None:
            credential = CloudCredential()
        credential.session_token = sanitize_for_log(
            headers["x-amz-security-token"][:100]
        )

    # Check for Bearer token
    if auth_header.startswith("Bearer "):
        credential = CloudCredential(bearer_token=sanitize_for_log(auth_header[7:100]))

    # Check body for credentials
    if body:
        # Look for access keys in body
        key_match = re.search(r"(AKIA[0-9A-Z]{16})", body)
        if key_match:
            if credential is None:
                credential = CloudCredential()
            credential.access_key_id = key_match.group(1)

        # Look for username/password in body
        user_match = re.search(r"[Uu]sername[=:]\s*([^\s&\"]+)", body)
        pass_match = re.search(r"[Pp]assword[=:]\s*([^\s&\"]+)", body)
        if user_match or pass_match:
            if credential is None:
                credential = CloudCredential()
            if user_match:
                credential.username = sanitize_for_log(user_match.group(1)[:50])
            if pass_match:
                credential.password = sanitize_for_log(pass_match.group(1)[:50])

    return credential


def calculate_timing(
    source_ip: str,
    now: float,
    request_counts: Dict[str, List[float]],
) -> RequestTiming:
    """Calculate request timing metrics.

    Args:
        source_ip: Source IP address
        now: Current timestamp
        request_counts: Dictionary tracking request times per IP

    Returns:
        RequestTiming object with metrics
    """
    timing = RequestTiming(request_received_at=datetime.now(timezone.utc))

    # Track request history
    if source_ip not in request_counts:
        request_counts[source_ip] = []
    request_counts[source_ip].append(now)

    # Keep last 100 requests
    if len(request_counts[source_ip]) > 100:
        request_counts[source_ip] = request_counts[source_ip][-100:]

    times = request_counts[source_ip]

    if len(times) > 1:
        # Calculate inter-request delays
        delays = [(times[i] - times[i - 1]) * 1000 for i in range(1, len(times))]

        timing.time_since_last_request_ms = delays[-1] if delays else None
        timing.avg_inter_request_delay_ms = sum(delays) / len(delays)
        timing.min_inter_request_delay_ms = min(delays)
        timing.max_inter_request_delay_ms = max(delays)

        if len(delays) > 2:
            mean = timing.avg_inter_request_delay_ms
            timing.request_timing_variance = sum((d - mean) ** 2 for d in delays) / len(
                delays
            )

        # Check for machine-like timing
        if timing.min_inter_request_delay_ms < 100:
            timing.is_machine_timing = True
            if timing.request_timing_variance and timing.request_timing_variance < 50:
                timing.timing_pattern = "constant"
            else:
                timing.timing_pattern = "variable"
        else:
            timing.timing_pattern = "human"

    return timing


def determine_trigger(
    action: str,
    credentials: Optional[CloudCredential],
    detections: List[Dict],
) -> str:
    """Determine state machine trigger from action and context.

    Args:
        action: API action name
        credentials: Extracted credentials
        detections: List of detected patterns

    Returns:
        Trigger name for state machine
    """
    action_lower = action.lower()

    # Authentication triggers
    if credentials:
        return "auth_attempt"

    # IAM actions
    if any(
        kw in action_lower for kw in ["user", "role", "policy", "group", "accesskey"]
    ):
        return "iam_action"

    # List/describe actions
    if any(kw in action_lower for kw in ["list", "describe", "get"]):
        if any(kw in action_lower for kw in ["bucket", "object", "secret", "instance"]):
            return "list_resources"
        return "probe_endpoint"

    # Download actions
    if any(kw in action_lower for kw in ["getobject", "getsecretvalue"]):
        return "download_attempt"

    # Role assumption
    if "assumerole" in action_lower:
        return "role_assumed"

    # Cross-service patterns
    if len(detections) > 3:
        return "cross_service_access"

    return "probe_endpoint"


def create_attack_event(
    session: CloudSession,
    call: CloudAPICall,
    detections: List[Dict],
    heuristic_alerts: List[HeuristicAlert],
    request: web.Request,
    config,
    pattern_detector,
) -> AttackEvent:
    """Create AttackEvent for integration with existing honeypot system.

    Args:
        session: Cloud session
        call: API call
        detections: Pattern detections
        heuristic_alerts: Heuristic alerts
        request: HTTP request
        config: Honeypot config
        pattern_detector: Pattern detector instance

    Returns:
        AttackEvent for emission with enhanced metadata
    """
    # Map cloud severity to AttackSeverity
    severity_map = {
        APICallSeverity.CRITICAL: AttackSeverity.CRITICAL,
        APICallSeverity.HIGH: AttackSeverity.HIGH,
        APICallSeverity.MEDIUM: AttackSeverity.MEDIUM,
        APICallSeverity.LOW: AttackSeverity.LOW,
        APICallSeverity.INFO: AttackSeverity.INFO,
    }

    # Map cloud category to AttackCategory
    category_map = {
        CloudAttackCategory.CREDENTIAL_STUFFING: AttackCategory.BRUTE_FORCE,
        CloudAttackCategory.BRUTE_FORCE: AttackCategory.BRUTE_FORCE,
        CloudAttackCategory.IAM_ENUMERATION: AttackCategory.RECONNAISSANCE,
        CloudAttackCategory.SERVICE_DISCOVERY: AttackCategory.RECONNAISSANCE,
        CloudAttackCategory.BUCKET_ENUMERATION: AttackCategory.RECONNAISSANCE,
        CloudAttackCategory.SSRF: AttackCategory.EXPLOIT_ATTEMPT,
        CloudAttackCategory.PRIVILEGE_ESCALATION: AttackCategory.EXPLOIT_ATTEMPT,
        CloudAttackCategory.S3_EXFILTRATION: AttackCategory.CREDENTIAL_HARVESTING,
        CloudAttackCategory.SECRETS_EXTRACTION: AttackCategory.CREDENTIAL_HARVESTING,
        CloudAttackCategory.METADATA_SERVICE_ABUSE: AttackCategory.EXPLOIT_ATTEMPT,
    }

    severity = severity_map.get(call.severity, AttackSeverity.INFO)
    category = category_map.get(call.category, AttackCategory.UNKNOWN)

    # Get MITRE techniques with full details
    mitre_techniques = pattern_detector.get_mitre_techniques(call.detected_patterns)

    # Build enhanced heuristic alert metadata
    heuristic_metadata = []
    zero_day_candidate = False
    for alert in heuristic_alerts:
        heuristic_metadata.append(
            {
                "name": alert.heuristic_name,
                "severity": alert.severity.value,
                "confidence": alert.confidence_score,
                "description": alert.description,
                "indicators": alert.indicators,
            }
        )
        # Flag as zero-day candidate if high confidence + critical severity
        if alert.confidence_score >= 0.8 and alert.severity == APICallSeverity.CRITICAL:
            zero_day_candidate = True

    # Build MITRE ATT&CK metadata with techniques, tactics, and descriptions
    mitre_metadata = [
        {
            "technique_id": technique_id,
            "technique_name": technique_name,
            "tactic": tactic,
        }
        for technique_id, technique_name, tactic in mitre_techniques
    ]

    # Build detailed pattern detection metadata from raw detections
    pattern_details = [
        {
            "pattern_name": det.get("pattern_name"),
            "pattern_type": det.get("pattern_type"),
            "matched_text": sanitize_for_log(det.get("matched_text", "")[:100]),
            "mitre_technique": det.get("mitre_technique"),
        }
        for det in detections
        if det.get("pattern_name")
    ]

    # Build behavioral profile from session
    behavioral_profile = {
        "session_state": session.current_state.value,
        "state_transitions": len(session.state_history),
        "services_accessed": sorted(list(session.services_accessed)),
        "actions_performed": sorted(list(session.actions_performed)),
        "api_call_count": session.api_call_count,
        "success_rate": (
            session.success_count / session.api_call_count
            if session.api_call_count > 0
            else 0.0
        ),
        "error_rate": (
            session.error_count / session.api_call_count
            if session.api_call_count > 0
            else 0.0
        ),
        "is_automated": session.is_automated,
        "threat_score": session.threat_score,
    }

    # Add timing profile if available
    if call.request_timing:
        behavioral_profile["timing"] = {
            "is_machine_timing": call.request_timing.is_machine_timing,
            "timing_pattern": call.request_timing.timing_pattern,
            "avg_delay_ms": call.request_timing.avg_inter_request_delay_ms,
            "min_delay_ms": call.request_timing.min_inter_request_delay_ms,
        }

    # Build attack progression (state history)
    attack_progression = []
    for entry in session.state_history:
        if isinstance(entry, dict):
            # Already in dict format
            attack_progression.append(entry)
        else:
            # Legacy tuple format (state, timestamp)
            state, ts = entry
            attack_progression.append(
                {
                    "state": state.value if hasattr(state, "value") else str(state),
                    "timestamp": ts.isoformat()
                    if hasattr(ts, "isoformat")
                    else str(ts),
                }
            )

    # Cloud-specific CVE tags based on patterns and services
    cve_tags = []
    if call.category == CloudAttackCategory.METADATA_SERVICE_ABUSE:
        cve_tags.extend(["CVE-2019-5736", "CVE-2020-8555"])  # Container escape + SSRF
    if "ssrf" in [p.lower() for p in call.detected_patterns]:
        cve_tags.extend(
            ["CVE-2021-21972", "CVE-2022-22965"]
        )  # vCenter SSRF, Spring4Shell
    if call.category == CloudAttackCategory.PRIVILEGE_ESCALATION:
        cve_tags.extend(["CVE-2023-32315", "CVE-2023-46604"])  # AWS IAM, ActiveMQ RCE
    if "secrets" in call.service.lower():
        cve_tags.append("CVE-2024-21626")  # Secrets extraction

    return AttackEvent(
        event_id=f"evt-{hashlib.md5(f'{call.call_id}'.encode(), usedforsecurity=False).hexdigest()[:12]}",
        session_id=session.session_id,
        honeypot_id=config.cluster.node_id
        if hasattr(config, "cluster")
        else "cloud-mgmt",
        protocol=HoneypotProtocol.HTTP,
        timestamp=call.timestamp,
        source_ip=call.source_ip,
        source_port=call.source_port,
        event_type="cloud_api_call",
        raw_data=sanitize_for_log(
            json.dumps(
                {
                    "service": call.service,
                    "action": call.action,
                    "parameters": call.parameters,
                }
            )[:1000]
        ),
        http_method=request.method,
        http_path=request.path,
        http_headers={k: sanitize_for_log(v) for k, v in dict(request.headers).items()},
        detected_patterns=call.detected_patterns,
        category=category,
        severity=severity,
        metadata={
            # Basic cloud info
            "cloud_service": call.service,
            "cloud_action": call.action,
            "cloud_category": call.category.value,
            "cloud_provider": "aws",
            # Session and threat context
            "session_state": session.current_state.value,
            "threat_score": session.threat_score,
            "is_automated": session.is_automated,
            "credentials_captured": len(session.credentials_captured),
            # Enhanced heuristic analysis
            "heuristic_alerts": heuristic_metadata,
            "heuristic_count": len(heuristic_alerts),
            "zero_day_candidate": zero_day_candidate,
            # MITRE ATT&CK mapping
            "mitre_techniques": mitre_metadata,
            "mitre_technique_ids": [t[0] for t in mitre_techniques],
            "mitre_tactics": list(set(t[2] for t in mitre_techniques)),
            # Behavioral profile
            "behavioral_profile": behavioral_profile,
            # Attack progression
            "attack_progression": attack_progression,
            "state_transition_count": len(session.state_history),
            # CVE correlation
            "related_cves": cve_tags,
            # Detection metadata
            "detection_count": len(call.detected_patterns),
            "pattern_details": pattern_details,
            "services_accessed_count": len(session.services_accessed),
            "unique_actions_count": len(session.actions_performed),
        },
    )
