"""Models for Feature Extractor."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass
class AttackFeatureVector:
    """Complete feature vector for an attacker IP."""

    ip: str

    # Temporal features
    event_count: int = 0
    events_per_hour: float = 0.0
    burst_score: float = 0.0
    time_spread_hours: float = 0.0
    peak_hour: int = 0

    # Payload features
    avg_payload_size: float = 0.0
    payload_entropy: float = 0.0
    payload_hash: str = ""
    unique_payloads: int = 0

    # Sequence features
    command_count: int = 0
    unique_commands: int = 0
    command_sequence_hash: str = ""
    avg_command_length: float = 0.0

    # Network fingerprint
    unique_ports: int = 0
    unique_protocols: int = 0
    unique_targets: int = 0
    unique_targets: int = 0
    protocol_fingerprint: str = ""
    ja4_fingerprints: Set[str] = field(default_factory=set)

    # Statistical features
    special_char_ratio: float = 0.0
    hex_pattern_count: int = 0
    url_count: int = 0
    ip_reference_count: int = 0

    # Credential features
    credential_attempts: int = 0
    unique_usernames: int = 0
    default_cred_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ip": self.ip,
            "temporal": {
                "event_count": self.event_count,
                "events_per_hour": round(self.events_per_hour, 2),
                "burst_score": round(self.burst_score, 2),
                "time_spread_hours": round(self.time_spread_hours, 2),
                "peak_hour": self.peak_hour,
            },
            "payload": {
                "avg_size": round(self.avg_payload_size, 2),
                "entropy": round(self.payload_entropy, 3),
                "hash": self.payload_hash[:16] if self.payload_hash else "",
                "unique_count": self.unique_payloads,
            },
            "sequence": {
                "command_count": self.command_count,
                "unique_commands": self.unique_commands,
                "sequence_hash": self.command_sequence_hash[:16],
                "avg_length": round(self.avg_command_length, 1),
            },
            "network": {
                "unique_ports": self.unique_ports,
                "unique_protocols": self.unique_protocols,
                "unique_targets": self.unique_targets,
                "fingerprint": self.protocol_fingerprint,
            },
            "statistical": {
                "special_char_ratio": round(self.special_char_ratio, 3),
                "hex_patterns": self.hex_pattern_count,
                "urls": self.url_count,
                "ip_references": self.ip_reference_count,
            },
            "credentials": {
                "attempts": self.credential_attempts,
                "unique_usernames": self.unique_usernames,
                "default_cred_ratio": round(self.default_cred_ratio, 2),
            },
        }

    def to_vector(self) -> List[float]:
        """Convert to numerical feature vector for ML."""
        return [
            float(self.event_count),
            self.events_per_hour,
            self.burst_score,
            self.time_spread_hours,
            float(self.peak_hour),
            self.avg_payload_size,
            self.payload_entropy,
            float(self.unique_payloads),
            float(self.command_count),
            float(self.unique_commands),
            self.avg_command_length,
            float(self.unique_ports),
            float(self.unique_protocols),
            float(self.unique_targets),
            self.special_char_ratio,
            float(self.hex_pattern_count),
            float(self.url_count),
            float(self.ip_reference_count),
            float(self.credential_attempts),
            float(self.unique_usernames),
            self.default_cred_ratio,
        ]

    def get_top_ja4(self) -> str:
        """Get the most frequent JA4 fingerprint for this IP."""
        # This is a placeholder as the vector currently stores aggregated stats.
        # In a real implementation, we would need to store the raw JA4s or a frequency map.
        # For now, we will rely on the FeatureExtractor to aggregate this at the summary level.
        return ""
