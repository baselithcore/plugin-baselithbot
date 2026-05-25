"""React2Shell / React Flight Protocol Handler.

This handler implements a honeypot for detection of CVE-2025-55182 (React2Shell),
a Remote Code Execution vulnerability in React Server Components (RSC) via the
React Flight protocol.

The handler emulates a Next.js / React Server Components endpoint and detects:
1. Prototype pollution attempts via Flight protocol
2. Malicious chunk status manipulation ("resolved_model")
3. "Thenable" exploitation attempts
4. Blob reference manipulation
"""

import asyncio
from core.observability.logging import get_logger
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from aiohttp import web

from ..config import HoneypotConfig
from ..models import AttackCategory, AttackEvent, AttackSeverity, HoneypotProtocol
from ..engine.base import BaseHandler

logger = get_logger(__name__)


# Specific patterns for React2Shell/Flight Protocol exploits
RSC_EXPLOIT_PATTERNS = {
    "prototype_pollution": r"(?i)(\$1:__proto__|:constructor:constructor)",
    "chunk_manipulation": r"(?i)(\"\$@\d+\"|\"status\":\s*\"resolved_model\")",
    "thenable_exploit": r"(?i)(\"then\":\s*\"\$1:__proto__:then\")",
    "blob_exploit": r"(?i)(\"then\":\s*\"\$B\d+\"|_formData\.get)",
}


class ReactFlightHandler(BaseHandler):
    """Custom handler for React Flight Protocol / Next.js RSC emulation."""

    def __init__(self, config: HoneypotConfig, definition=None):
        """Initialize handler."""
        super().__init__(config, definition)
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._sessions: Dict[str, dict] = {}
        # Default port for Next.js dev server or typical deployment
        self._default_port = 3000

    async def start(self, port: Optional[int] = None) -> None:
        """Start the RSC honeypot server."""
        if self._running:
            return

        listen_port = port or self.definition.port or self._default_port

        self._app = web.Application()
        self._setup_routes()

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(
            self._runner,
            "0.0.0.0",  # nosec B104
            listen_port,
        )

        try:
            await self._site.start()
            self._running = True
            logger.info(f"React Flight (RSC) honeypot started on port {listen_port}")
        except OSError as e:
            logger.error(f"Failed to start RSC honeypot: {e}")
            raise

    async def stop(self) -> None:
        """Stop the honeypot server."""
        if not self._running:
            return

        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()

        self._running = False
        logger.info("React Flight (RSC) honeypot stopped")

    def _setup_routes(self) -> None:
        """Setup routes to emulate Next.js / RSC endpoints."""
        # Common RSC endpoint
        self._app.router.add_route("*", "/_rsc", self._handle_rsc_request)
        # Often RSC payloads are sent to the page route with a header
        self._app.router.add_route("*", "/{path:.*}", self._handle_generic_request)

    async def _handle_rsc_request(self, request: web.Request) -> web.Response:
        """Handle specific /_rsc requests."""
        return await self._process_request(request, is_rsc_endpoint=True)

    async def _handle_generic_request(self, request: web.Request) -> web.Response:
        """Handle other requests (checking for RSC headers)."""
        return await self._process_request(request, is_rsc_endpoint=False)

    async def _process_request(
        self, request: web.Request, is_rsc_endpoint: bool
    ) -> web.Response:
        """Process potential RSC exploit requests."""
        path = request.path
        method = request.method
        source_ip = request.remote or "unknown"
        source_port = 0  # Not easily available in aiohttp

        # Get or create session
        session_id = self._get_or_create_session(source_ip)

        # HoneyDOC check
        if not self.check_flow_allowed(source_ip, session_id):
            return web.Response(status=403)

        # Apply stealth delay
        await self.apply_stealth_delay()

        # Capture payload
        headers = dict(request.headers)
        body = ""
        try:
            body = await request.text()
        except Exception:
            pass  # nosec B110

        # Check for RSC indicators
        is_rsc_traffic = (
            is_rsc_endpoint
            or headers.get("RSC") == "1"
            or "text/x-component" in headers.get("Accept", "")
        )

        # Build full payload for analysis
        full_payload = f"{method} {path}\nHeaders: {headers}\nBody: {body}"

        # Detect Patterns
        detected_patterns, category, severity = self._analyze_rsc_payload(
            body, full_payload
        )

        # If malicious patterns found OR it's an RSC request we want to log
        if detected_patterns or (is_rsc_traffic and body):
            event = AttackEvent(
                event_id=self._generate_event_id(),
                session_id=session_id,
                protocol=HoneypotProtocol.HTTP,
                timestamp=datetime.now(timezone.utc),
                source_ip=source_ip,
                source_port=source_port,
                event_type="rsc_exploit_attempt"
                if detected_patterns
                else "rsc_traffic",
                raw_data=full_payload[: self.config.max_payload_size_kb * 1024],
                http_method=method,
                http_path=path,
                http_headers=headers,
                http_body=body[:1024] if body else None,
                detected_patterns=detected_patterns,
                category=category,
                severity=severity,
                matched_cves=["CVE-2025-55182"] if detected_patterns else [],
            )
            print(f"DEBUG: Emitting event: {event}")
            asyncio.create_task(self.emit_event(event))

        # Generate realistic response
        return self._generate_rsc_response(is_rsc_traffic)

    def _analyze_rsc_payload(
        self, body: str, full_payload: str
    ) -> Tuple[list, AttackCategory, AttackSeverity]:
        """Analyze if the payload contains React2Shell exploits."""
        detected = []

        # 1. Specific RSC Exploit Checks
        for name, pattern in RSC_EXPLOIT_PATTERNS.items():
            if re.search(pattern, body):
                detected.append(name)

        if detected:
            # Strong indicator of CVE-2025-55182
            return detected, AttackCategory.EXPLOIT_ATTEMPT, AttackSeverity.CRITICAL

        # 2. General Fallback Checks (SQLi, XSS, etc from BaseHandler)
        base_detected, base_category = self.detect_patterns(full_payload)
        base_severity = self.calculate_severity(base_category, base_detected)

        return base_detected, base_category, base_severity

    def _generate_rsc_response(self, is_rsc_traffic: bool) -> web.Response:
        """Generate a realistic RSC response to keep attacker engaged."""
        headers = {
            "Content-Type": "text/x-component"
            if is_rsc_traffic
            else "text/html; charset=utf-8",
            "Vary": "RSC, Next-Router-State-Tree, Next-Router-Prefetch",
            "X-Powered-By": "Next.js",
        }

        # HoneyDOC Stealth: Mask explicit honeypot headers if needed
        headers = self.mask_response_headers(headers)

        if is_rsc_traffic:
            # Emulate a generic RSC flight response
            # Format: <id>:<json_data>\n
            response_text = (
                '1:I["./src/app/page.tsx",["","ROOT",""]]\n'
                '0:["$","main",null,{"children":["$","p",null,{"children":"Application Error: Client-side exception occurred."}]}]\n'
            )
            return web.Response(text=response_text, headers=headers)

        # Standard fallback page
        html_response = """<!DOCTYPE html>
<html>
<head>
    <title>Application Error</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, sans-serif; padding: 40px; text-align: center; }
        h1 { font-size: 24px; margin-bottom: 20px; }
        p { color: #666; }
    </style>
</head>
<body>
    <h1>Something went wrong</h1>
    <p>We're actively working on a fix.</p>
</body>
</html>"""
        return web.Response(text=html_response, headers=headers)

    def _get_or_create_session(self, source_ip: str) -> str:
        """Get or create session for IP."""
        if source_ip not in self._sessions:
            session_id = self._generate_session_id()
            self._sessions[source_ip] = {
                "session_id": session_id,
                "started_at": datetime.now(timezone.utc),
            }
        return self._sessions[source_ip]["session_id"]
