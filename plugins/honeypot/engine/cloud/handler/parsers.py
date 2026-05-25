"""Cloud Handler - Request Parsers.

Parsing logic for AWS API requests.
"""

import json
import re
from typing import Any, Dict, Optional, Tuple

from aiohttp import web


# AWS Signature Version 4 regex for credential extraction
AWS_AUTH_HEADER_PATTERN = re.compile(
    r"AWS4-HMAC-SHA256\s+Credential=([^/]+)/(\d{8})/([^/]+)/([^/]+)/aws4_request"
)

# Action extraction from AWS requests
AWS_ACTION_PATTERN = re.compile(r"Action=(\w+)")


def parse_aws_request(
    request: web.Request,
    headers: Dict[str, str],
    body: str,
) -> Tuple[str, str, Dict[str, Any]]:
    """Parse AWS-style API request to extract service, action, and parameters.

    Args:
        request: aiohttp Request object
        headers: Request headers
        body: Request body

    Returns:
        Tuple of (service, action, parameters)
    """
    service = "unknown"
    action = "unknown"
    parameters = {}

    # Try to get service from URL path
    path = request.path
    if path.startswith("/"):
        parts = path.strip("/").split("/")
        if parts and parts[0]:
            service = parts[0].lower()

    # Try to get service from Host header
    host = headers.get("Host", "")
    if ".amazonaws.com" in host:
        service_match = re.match(r"(\w+)\..*\.amazonaws\.com", host)
        if service_match:
            service = service_match.group(1).lower()

    # Try to get action from x-amz-target header
    target = headers.get("x-amz-target", "")
    if target and "." in target:
        action = target.split(".")[-1]

    # Try to get action from query string or body
    query = dict(request.query)
    if "Action" in query:
        action = query["Action"]
        parameters = {k: v for k, v in query.items() if k != "Action"}
    elif body:
        # Try URL-encoded body
        action_match = AWS_ACTION_PATTERN.search(body)
        if action_match:
            action = action_match.group(1)

        # Try JSON body
        try:
            json_body = json.loads(body)
            if isinstance(json_body, dict):
                parameters = json_body
        except json.JSONDecodeError:
            # Parse URL-encoded
            for param in body.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    if key != "Action":
                        parameters[key] = value

    return service, action, parameters


def parse_aws_auth_header(auth_header: str) -> Optional[str]:
    """Extract access key from AWS Authorization header.

    Args:
        auth_header: Authorization header value

    Returns:
        Access key ID or None
    """
    auth_match = AWS_AUTH_HEADER_PATTERN.search(auth_header)
    if auth_match:
        return auth_match.group(1)
    return None
