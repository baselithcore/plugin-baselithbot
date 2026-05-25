"""Tactics identification for Botnet Profiler."""

from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

from ...models import AttackEvent


def identify_tactics(events: List[AttackEvent]) -> Dict[str, Any]:
    """Identify attack tactics used by the botnet.

    Args:
        events: List of events

    Returns:
        Dict describing tactics
    """
    tactics: Counter = Counter()
    evidence: Dict[str, List[str]] = defaultdict(list)

    for event in events:
        detected = detect_event_tactics(event)
        for tactic, ev in detected:
            tactics[tactic] += 1
            if len(evidence[tactic]) < 3:  # Keep max 3 examples
                evidence[tactic].append(ev)

    # Calculate primary tactic
    primary = tactics.most_common(1)[0][0] if tactics else "unknown"

    return {
        "primary_tactic": primary,
        "all_tactics": dict(tactics.most_common()),
        "tactic_count": len(tactics),
        "evidence_samples": dict(evidence),
        "threat_assessment": assess_threat(tactics),
    }


def detect_event_tactics(event: AttackEvent) -> List[Tuple[str, str]]:
    """Detect tactics from a single event."""
    tactics = []
    payload = ((event.raw_data or "") + " " + (event.command or "")).lower()

    # Brute force
    if event.username and event.password:
        tactics.append(("brute_force", f"{event.username}:{event.password}"))

    # Credential stuffing (many unique creds)
    if event.username and len(event.username) >= 5:
        tactics.append(("credential_stuffing", event.username))

    # DDoS indicators
    if any(kw in payload for kw in ["flood", "ddos", "attack", "target"]):
        tactics.append(("DDoS", payload[:50]))

    # Cryptomining
    if any(kw in payload for kw in ["miner", "xmrig", "pool", "stratum"]):
        tactics.append(("cryptomining", payload[:50]))

    # Malware delivery
    if any(kw in payload for kw in ["wget", "curl", "tftp", "download"]):
        tactics.append(("malware_delivery", payload[:50]))

    # Lateral movement
    if any(kw in payload for kw in ["net view", "net user", "whoami", "ipconfig"]):
        tactics.append(("lateral_movement", payload[:50]))

    # Reconnaissance
    if any(kw in payload for kw in ["scan", "nmap", "masscan", "portscan"]):
        tactics.append(("reconnaissance", payload[:50]))

    # SQL injection
    if event.category and "sql" in str(event.category).lower():
        tactics.append(("sql_injection", event.http_path or ""))

    # Command injection
    if any(kw in payload for kw in [";", "&&", "||", "`", "$("]):
        if len(payload) > 5:
            tactics.append(("command_injection", payload[:50]))

    # Default: reconnaissance if nothing else
    if not tactics and event.event_type in ["connection", "scan"]:
        tactics.append(("reconnaissance", event.source_ip))

    return tactics


def assess_threat(tactics: Counter) -> Dict[str, Any]:
    """Assess overall threat level based on tactics."""
    high_threat = ["DDoS", "cryptomining", "malware_delivery", "ransomware"]
    medium_threat = ["brute_force", "credential_stuffing", "sql_injection"]

    threat_score = 0
    for tactic, count in tactics.items():
        if tactic in high_threat:
            threat_score += count * 3
        elif tactic in medium_threat:
            threat_score += count * 2
        else:
            threat_score += count

    if threat_score >= 50:
        level = "critical"
    elif threat_score >= 20:
        level = "high"
    elif threat_score >= 10:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "score": threat_score,
        "high_risk_tactics": [t for t in tactics if t in high_threat],
    }
