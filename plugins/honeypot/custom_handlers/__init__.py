"""Custom honeypot handlers for CVE-specific detections."""

from .react_flight_handler import ReactFlightHandler
from .n8n_handler import N8nHandler
from .fortigate_handler import FortiGateHandler

__all__ = ["ReactFlightHandler", "N8nHandler", "FortiGateHandler"]
