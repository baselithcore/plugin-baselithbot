"""Threat Intel Models."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class IOCBundle:
    """Collection of Indicators of Compromise."""

    id: str
    generated_at: datetime
    source: str = "honeypot"

    # Network IOCs
    malicious_ips: List[str] = field(default_factory=list)
    malicious_domains: List[str] = field(default_factory=list)
    malicious_urls: List[str] = field(default_factory=list)

    # File IOCs
    payload_hashes: List[Dict[str, str]] = field(default_factory=list)

    # Behavioral IOCs
    command_patterns: List[str] = field(default_factory=list)
    user_agents: List[str] = field(default_factory=list)

    # YARA rules
    yara_rules: List[str] = field(default_factory=list)

    # OSINT enrichment data (from external sources)
    osint_enrichment: Dict[str, Any] = field(default_factory=dict)

    # Context
    attack_types: List[str] = field(default_factory=list)
    confidence: float = 0.0
    severity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "id": self.id,
            "generated_at": self.generated_at.isoformat(),
            "source": self.source,
            "iocs": {
                "ips": self.malicious_ips,
                "domains": self.malicious_domains,
                "urls": self.malicious_urls,
                "hashes": self.payload_hashes,
                "commands": self.command_patterns[:20],
                "user_agents": self.user_agents[:10],
            },
            "yara_rules": self.yara_rules,
            "context": {
                "attack_types": self.attack_types,
                "confidence": round(self.confidence, 2),
                "severity": self.severity,
            },
        }
        # Include OSINT enrichment if available
        if self.osint_enrichment:
            result["osint_enrichment"] = self.osint_enrichment
        return result

    def to_stix(self) -> Dict[str, Any]:
        """Convert to STIX 2.1 format."""
        objects = []
        bundle_id = f"bundle--{self.id}"

        # Create indicator objects for IPs
        for ip in self.malicious_ips[:50]:
            objects.append(
                {
                    "type": "indicator",
                    "spec_version": "2.1",
                    "id": f"indicator--{uuid.uuid4()}",
                    "created": self.generated_at.isoformat(),
                    "modified": self.generated_at.isoformat(),
                    "name": f"Malicious IP: {ip}",
                    "pattern": f"[ipv4-addr:value = '{ip}']",
                    "pattern_type": "stix",
                    "valid_from": self.generated_at.isoformat(),
                    "labels": ["malicious-activity"],
                }
            )

        # Create indicator objects for domains
        for domain in self.malicious_domains[:50]:
            objects.append(
                {
                    "type": "indicator",
                    "spec_version": "2.1",
                    "id": f"indicator--{uuid.uuid4()}",
                    "created": self.generated_at.isoformat(),
                    "modified": self.generated_at.isoformat(),
                    "name": f"Malicious Domain: {domain}",
                    "pattern": f"[domain-name:value = '{domain}']",
                    "pattern_type": "stix",
                    "valid_from": self.generated_at.isoformat(),
                    "labels": ["malicious-activity"],
                }
            )

        # Create indicator objects for hashes
        for hash_info in self.payload_hashes[:50]:
            objects.append(
                {
                    "type": "indicator",
                    "spec_version": "2.1",
                    "id": f"indicator--{uuid.uuid4()}",
                    "created": self.generated_at.isoformat(),
                    "modified": self.generated_at.isoformat(),
                    "name": f"Malicious Payload: {hash_info.get('sha256', '')[:16]}...",
                    "pattern": f"[file:hashes.'SHA-256' = '{hash_info.get('sha256', '')}']",
                    "pattern_type": "stix",
                    "valid_from": self.generated_at.isoformat(),
                    "labels": self.attack_types[:3] or ["malicious-activity"],
                }
            )

        return {
            "type": "bundle",
            "id": bundle_id,
            "objects": objects,
        }
