"""Cloud Handler Module.

Main HTTP handler for cloud API simulation.
"""

from .cloud_handler import CloudManagementHandler
from .helpers import (
    calculate_timing,
    create_attack_event,
    determine_trigger,
    extract_credentials,
)
from .parsers import parse_aws_auth_header, parse_aws_request
from .session_manager import CloudSessionManager

__all__ = [
    # Main handler
    "CloudManagementHandler",
    # Session management
    "CloudSessionManager",
    # Parsers
    "parse_aws_request",
    "parse_aws_auth_header",
    # Helpers
    "extract_credentials",
    "calculate_timing",
    "determine_trigger",
    "create_attack_event",
]
