"""RDNS (Reverse DNS) Resolver package.

Provides async Reverse DNS resolution for IP addresses with caching,
timeout handling, and significance scoring for threat intelligence.
"""

from ._constants import IPCategory, SignificanceLevel
from ._models import (
    RDNSEnrichmentResponse,
    RDNSResult,
    sanitize_hostname,
    validate_ip_address,
)
from ._resolver import RDNSResolver, get_rdns_resolver

__all__ = [
    "RDNSResolver",
    "get_rdns_resolver",
    "RDNSResult",
    "RDNSEnrichmentResponse",
    "SignificanceLevel",
    "IPCategory",
    "validate_ip_address",
    "sanitize_hostname",
]
