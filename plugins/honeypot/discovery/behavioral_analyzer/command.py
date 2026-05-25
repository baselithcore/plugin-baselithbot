"""Command similarity logic for Behavioral Analyzer."""

import hashlib
import re
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set

from ...models import AttackEvent
from ..models import NetworkAnomaly


def detect_command_sequences(
    events: List[AttackEvent], min_correlation_group_size: int
) -> List[NetworkAnomaly]:
    """Detect identical command sequences across IPs.

    Identifies IPs executing the same command sequences,
    indicating automated scripts or botnet playbooks.

    Args:
        events: Attack events to analyze
        min_correlation_group_size: Minimum IPs to form a correlation group

    Returns:
        List of command sequence anomalies
    """
    anomalies: List[NetworkAnomaly] = []

    # Extract command sequences per IP
    ip_commands: Dict[str, List[str]] = defaultdict(list)

    for event in events:
        if event.command and len(event.command) > 1:
            # Normalize command (remove variable parts like IPs, timestamps)
            normalized = normalize_command(event.command)
            ip_commands[event.source_ip].append(normalized)

    # Build sequence fingerprints
    sequence_fingerprints: Dict[str, Set[str]] = defaultdict(set)

    for ip, commands in ip_commands.items():
        if len(commands) >= 2:
            # Create sequence hash from first N commands
            seq_key = "||".join(commands[:10])
            seq_hash = hashlib.md5(seq_key.encode(), usedforsecurity=False).hexdigest()[
                :12
            ]
            sequence_fingerprints[seq_hash].add(ip)

    # Report identical sequences
    for seq_hash, ips in sequence_fingerprints.items():
        if len(ips) >= min_correlation_group_size:
            # Get sample commands from first IP
            sample_ip = list(ips)[0]
            sample_cmds = ip_commands.get(sample_ip, [])[:3]

            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="command_sequence",
                involved_ips=list(ips),
                description=(
                    f"{len(ips)} IPs executed identical command sequence "
                    f"(likely automated script)"
                ),
                severity="high" if len(ips) >= 5 else "medium",
                confidence=min(1.0, 0.7 + len(ips) / 20),
                detected_at=datetime.now(),
                metadata={
                    "sequence_hash": seq_hash,
                    "sample_commands": sample_cmds,
                    "ip_count": len(ips),
                },
            )
            anomalies.append(anomaly)

    return anomalies


def normalize_command(command: str) -> str:
    """Normalize command by removing variable parts."""
    normalized = command.strip().lower()

    # Remove IP addresses
    normalized = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "<IP>", normalized)

    # Remove timestamps / dates
    normalized = re.sub(r"\d{4}-\d{2}-\d{2}", "<DATE>", normalized)
    normalized = re.sub(r"\d{2}:\d{2}:\d{2}", "<TIME>", normalized)

    # Remove random-looking strings (hex, base64)
    normalized = re.sub(r"[a-f0-9]{16,}", "<HEX>", normalized)

    return normalized
