"""Hashing utilities for CVE Hunter."""

from typing import Optional
from uuid import NAMESPACE_DNS, uuid5


def stable_finding_id(pattern: str, source: str, context: Optional[str]) -> str:
    """Generate a deterministic finding ID for discovery signals."""
    payload = f"{pattern}|{source}|{context or ''}"
    return str(uuid5(NAMESPACE_DNS, payload))
