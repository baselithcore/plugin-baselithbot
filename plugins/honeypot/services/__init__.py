"""Honeypot Services.

Service layer for honeypot plugin functionality.
"""

from .cve_service import CVEService, get_cve_service

__all__ = ["CVEService", "get_cve_service"]
